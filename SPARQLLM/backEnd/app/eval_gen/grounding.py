"""
eval_generation/grounding.py

For each template, walk its placeholders one at a time, this avoids the combinatorial blow-up of grounding every
placeholder independently and lets an earlier binding constrain a later one.

No LLM is used anywhere in this module.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

import yaml

import sys
import os
# Configura i path di importazione
eval_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(eval_dir)
backend_dir = os.path.dirname(app_dir)

for p in [eval_dir, app_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)


# GraphDB backend adapter
class GraphDBBackend:
    def __init__(self, client):
        self._client = client

    def execute(self, query: str):
        raw = self._client.execute_query(query)
        return _normalize_sparql_json(raw)


def _normalize_sparql_json(raw):
    if isinstance(raw, dict):
        if "boolean" in raw:
            return raw["boolean"]
        bindings = raw.get("results", {}).get("bindings")
        if bindings is not None:
            return [
                {var: cell.get("value") for var, cell in binding.items()}
                for binding in bindings
            ]
    return raw


# Data model

@dataclass
class GroundedInstance:
    id: str
    cq_ref: str
    template_id: str
    question_seed: str          # cq_text with placeholders substituted
    golden_sparql: str          # fully grounded, executable SPARQL
    bindings: dict = field(default_factory=dict)   # placeholder -> value used


class GroundingExhausted(Exception):
    """Raised when a template can't be grounded to a non-empty query
    within the retry budget."""


# Template loading
def load_templates(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["templates"]


def _topo_order(placeholders: dict) -> list[str]:
    """Order placeholder names so any `depends_on` is resolved before the
    placeholder that depends on it. Simple Kahn's-algorithm pass; the
    template bank only has single-level dependencies (e.g. sport_label
    depends_on sport_id), but this handles chains too."""
    order: list[str] = []
    remaining = dict(placeholders)
    while remaining:
        ready = [
            name for name, spec in remaining.items()
            if not spec.get("depends_on") or spec["depends_on"] not in remaining
        ]
        if not ready:
            raise ValueError(f"Circular depends_on in placeholders: {remaining}")
        order.extend(ready)
        for name in ready:
            del remaining[name]
    return order


# Per-placeholder grounding

def _is_ask(sparql: str) -> bool:
    # crude but sufficient: ASK queries don't have a SELECT clause
    return re.search(r"\bASK\s*{", sparql, re.IGNORECASE) is not None


def _local_name(value: str) -> str:
    """URIs get their trailing path segment (e.g. .../Sport/sci -> sci);
    plain literals pass through unchanged."""
    if value.startswith("http://") or value.startswith("https://"):
        return value.rstrip(">").rsplit("/", 1)[-1]
    return value


def _build_scoped_query(spec: dict) -> str:
    domain_class = spec["domain_class"]
    via_property = spec.get("via_property")
    if via_property:
        return f"""PREFIX sft: <http://www.semanticweb.org/KG-SFT#>
SELECT DISTINCT ?value WHERE {{
    ?x a {domain_class} ;
        sft:{via_property} ?value .
    FILTER(isLiteral(?value))
}}"""
    return f"""PREFIX sft: <http://www.semanticweb.org/KG-SFT#>
SELECT DISTINCT ?value WHERE {{
    ?value a {domain_class} .
    FILTER(isIRI(?value))
}}"""


def ground_placeholder(
    backend: GraphDBBackend,
    name: str,
    spec: dict,
    bound: dict[str, str],
    rng: random.Random,
) -> str | None:
    """Sample one concrete value for a single placeholder. Returns None if
    the scoped query has no results (caller decides whether that discards
    the whole template attempt)."""
    if spec.get("depends_on"):
        base_key = spec["depends_on"]
        if base_key not in bound:
            raise ValueError(f"{name} depends_on {base_key}, which isn't bound yet")
        return _local_name(bound[base_key])

    if spec.get("candidates"):
        # Fixed enum, not sampled from the DB (e.g. comparator: < <= > >=).
        return rng.choice(spec["candidates"])

    query = _build_scoped_query(spec)
    rows = backend.execute(query)
    values = _extract_values(rows, var="value")
    if not values:
        return None
    return rng.choice(values)


def _extract_values(rows, var: str) -> list[str]:
    """Normalize whatever shape backend.execute() returns into a flat list
    of string values. Handles:
      - list[str]                      (client already extracts the value)
      - list[dict[str, str]]           (flat {var: value} rows)
      - list[dict[str, dict]]          (raw SPARQL-JSON bindings: {var: {"value": ...}})
    """
    if not rows:
        return []
    values = []
    for row in rows:
        if isinstance(row, str):
            values.append(row)
        elif isinstance(row, dict):
            cell = row.get(var)
            if isinstance(cell, dict):
                cell = cell.get("value")
            if cell:
                values.append(cell)
    return values


# Per-template grounding

def ground_template(
    backend: GraphDBBackend,
    template: dict,
    rng: random.Random,
    max_attempts: int = 5,
    keep_empty: bool = False,
    keep_false: bool = True,
) -> GroundedInstance:
    """ Walk placeholders in dependency order, binding one at a time. After
        all placeholders are bound, substitute into the template's own sparql
        and execute the FULL grounded query."""
    
    placeholders = template.get("placeholders") or {}
    order = _topo_order(placeholders)

    last_bindings: dict[str, str] = {}
    for attempt in range(1, max_attempts + 1):
        bound: dict[str, str] = {}
        dead_end = False

        for name in order:
            spec = placeholders[name]
            value = ground_placeholder(backend, name, spec, bound, rng)
            if value is None:
                dead_end = True  # this placeholder has no values at all; no point retrying
                break
            elif '"' in value:
                value = value.replace('"', '\\"')
            bound[name] = value

        if dead_end:
            raise GroundingExhausted(
                f"{template['id']}: placeholder '{name}' has no groundable values "
                f"(empty scoped query) -- check domain_class/via_property."
            )

        golden_sparql = _substitute(template["sparql"], bound)
        question_seed = _substitute(template["cq_text"], bound)
        is_ask = _is_ask(golden_sparql)

        if is_ask and keep_false:
            return _make_instance(template, bound, question_seed, golden_sparql, attempt)
        if not is_ask and keep_empty:
            return _make_instance(template, bound, question_seed, golden_sparql, attempt)

        result = backend.execute(golden_sparql)
        last_bindings = bound

        if is_ask:
            if result is True:  # accept "yes" answers by default
                return _make_instance(template, bound, question_seed, golden_sparql, attempt)
            # False -> discard and resample, same as an empty SELECT
        else:
            if result:  # non-empty -> accept
                return _make_instance(template, bound, question_seed, golden_sparql, attempt)
            # empty -> discard and resample on next loop iteration

    raise GroundingExhausted(
        f"{template['id']}: {max_attempts} groundings all produced empty results "
        f"(last tried: {last_bindings})."
    )


def _substitute(text: str, bound: dict[str, str]) -> str:
    def repl(match: re.Match) -> str:
        key = match.group(1)
        return _local_name(bound[key]) if key in bound else match.group(0)
    return re.sub(r"\{\{(\w+)\}\}", repl, text)


def _make_instance(template, bound, question_seed, golden_sparql, attempt) -> GroundedInstance:
    inst_id = f"{template['id']}-{attempt:02d}-{abs(hash(frozenset(bound.items()))) % 10000:04d}"
    return GroundedInstance(
        id=inst_id,
        cq_ref=template["cq_ref"],
        template_id=template["id"],
        question_seed=question_seed,
        golden_sparql=golden_sparql,
        bindings=bound,
    )

def generate_groundings(
    backend: GraphDBBackend,
    templates: list[dict],
    n_per_template: int = 3,
    seed: int = 42,
    skip_ids: set[str] | None = None,
) -> list[GroundedInstance]:
    """ Ground every template n_per_template times with different random samples. 
        The skip_ids lets you exclude templates that aren't ready yet """
    rng = random.Random(seed)
    skip_ids = skip_ids or set()
    instances: list[GroundedInstance] = []

    for template in templates:
        if template["id"] in skip_ids:
            continue

        seen_golden: set[str] = set()
        attempts_for_this_template = n_per_template if template.get("placeholders") else 1

        for _ in range(attempts_for_this_template):
            try:
                print(f"[grounding] {template['id']} attempt {_ + 1}/{attempts_for_this_template}")
                inst = ground_template(backend, template, rng)
            except GroundingExhausted as exc:
                print(f"[grounding] skipped: {exc}")
                break
            if inst.golden_sparql in seen_golden:
                continue  # no new variety left for this template; move on
            seen_golden.add(inst.golden_sparql)
            instances.append(inst)

    return instances


def write_groundings_jsonl(instances: list[GroundedInstance], out_path: str) -> None:
    import json
    with open(out_path, "w", encoding="utf-8") as f:
        for inst in instances:
            f.write(json.dumps({
                "id": inst.id,
                "cq_ref": inst.cq_ref,
                "template_id": inst.template_id,
                "question_seed": inst.question_seed,
                "golden_sparql": inst.golden_sparql,
                "bindings": inst.bindings,
            }, ensure_ascii=False) + "\n")



if __name__ == "__main__":
    from app.client import GraphDBClient  # your existing MCP client

    raw_client = GraphDBClient()  # adjust constructor args as needed
    backend = GraphDBBackend(raw_client)

    templates = load_templates("backEnd/app/eval_gen/templates/cq_templates.yaml")

    instances = generate_groundings(backend, templates, n_per_template=3)
    write_groundings_jsonl(instances, "groundings.jsonl")
    print(f"Wrote {len(instances)} grounded instances -> groundings.jsonl")