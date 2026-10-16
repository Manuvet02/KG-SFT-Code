"""
eval_generation/question_gen.py

Feeds each grounded query + a few hand-written pairs from the real 17 CQs + a relevant schema fragment to an LLM
and asks it to produce the natural-language question a human wouldhave asked to get that query.
"""

from __future__ import annotations

import asyncio
import json
import re

import sys
import os
# Configura i path di importazione
eval_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(eval_dir)
backend_dir = os.path.dirname(app_dir)

for p in [eval_dir, app_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

FEW_SHOT_PAIRS = [
    {
        "question": "What is the capacity (number of seats) of each sports facility?",
        "sparql": """PREFIX sft: <http://www.semanticweb.org/KG-SFT#>
SELECT ?capacity WHERE {
   ?sport_facility a sft:sport_facility ; sft:has_capacity ?capacity .
}""",
    },
    {
        "question": "Which sports facilities are currently open, closed, or undergoing renovation?",
        "sparql": """PREFIX sft: <http://www.semanticweb.org/KG-SFT#>
SELECT ?status WHERE {
   ?sport_facility a sft:sport_facility ; sft:has_status ?status .
}""",
    },
    {
        "question": "Which sports facilities are accessible to people with disabilities?",
        "sparql": """PREFIX sft: <http://www.semanticweb.org/KG-SFT#>
SELECT ?sport_facility WHERE {
   ?sport_facility a sft:sport_facility ; sft:has_accessibility "yes" .
}""",
    },
    {
        "question": "Which public transport options are available to reach a specific sports facility?",
        "sparql": """PREFIX sft: <http://www.semanticweb.org/KG-SFT#>
SELECT ?code WHERE {
   ?sport_facility a sft:sport_facility ; sft:has_meanOfTransport ?mot .
   ?mot a sft:mean_of_transport ; sft:has_code ?code .
}""",
    },
    {
        "question": "What is the average travel time by public transport to a facility?",
        "sparql": """PREFIX sft: <http://www.semanticweb.org/KG-SFT#>
SELECT ?time WHERE {
   ?route a sft:route ; sft:has_time ?time .
}""",
    },
]


# Schema fragment -- confirmed classes/properties, keyed by the sft: tokens actually touched by a given golden query (see extract_touched_terms).

SCHEMA_FRAGMENTS: dict[str, str] = {
    "sport_facility": (
        "sft:sport_facility: has_name, has_address, has_city, has_capacity, "
        "has_accessibility (\"yes\"/\"no\"), has_status, has_timetable, "
        "has_sport, has_stop, has_service, has_meanOfTransport"
    ),
    "service": "sft:service: has_name (subtypes: app, reservation)",
    "mean_of_transport": "sft:mean_of_transport: has_code (subtypes: bike, bus, train)",
    "route": "sft:route: has_time, has_meanOfTransport, has_stop, has_path",
    "stop": "sft:stop: has_route, has_sportFacility (subtypes: bus_stop, train_station)",
    "path": "sft:path: has_type, has_description, has_route (subtypes: bike_line, bus_road)",
    "sport": "sft:sport: an activity type, linked from sport_facility/association via has_sport",
    "association": "sft:association: has_sport",
    "reservation": "sft:reservation: a service subtype",
}


def extract_touched_terms(sparql: str) -> list[str]:
    tokens = set(re.findall(r"sft:(\w+)", sparql))
    class_like = {t for t in tokens if t in SCHEMA_FRAGMENTS}
    return sorted(class_like)


def build_schema_fragment(sparql: str) -> str:
    terms = extract_touched_terms(sparql)
    if not terms:
        return "sft:sport_facility: has_name, has_address, has_city"  # safe fallback
    return "\n".join(SCHEMA_FRAGMENTS[t] for t in terms)


# Prompting

SYSTEM_PROMPT = """You write natural language questions that a person would ask \
to get the answer to a given SPARQL query, over a knowledge graph about sports \
facilities and public transport in Trentino (KG-SFT).

Rules:
- Output ONLY the question, nothing else. No preamble, no quotes, no explanation.
- One sentence, ending in a question mark.
- Do not mention SPARQL, classes, properties, or any technical vocabulary.
- Do not invent facts not present in the query.
- If the query has a FILTER with a specific value (a name, a status, a threshold, \
a comparator), the question must reflect that specific value, the way a person \
asking about one real thing would."""


def build_prompt(golden_sparql: str) -> str:
    """Returns the user-turn prompt; SYSTEM_PROMPT is passed separately to
    ask_llm's `system` argument."""
    few_shot_block = "\n\n".join(
        f"SPARQL:\n{pair['sparql']}\n\nQuestion: {pair['question']}"
        for pair in FEW_SHOT_PAIRS
    )
    schema_block = build_schema_fragment(golden_sparql)

    return f"""Relevant schema fragment:
{schema_block}

Examples:
{few_shot_block}

Now generate the question for this SPARQL query:
{golden_sparql}"""


def clean_question(raw: str) -> str:
    text = raw.strip().strip('"').strip()
    # drop a leading "Question:" if the model echoes the label
    text = re.sub(r"^question:\s*", "", text, flags=re.IGNORECASE)
    return text


def looks_valid(question: str) -> bool:
    return bool(question) and question.strip().endswith("?") and "\n" not in question.strip()


async def generate_one_question(
    ask_llm_fn,
    golden_sparql: str,
    max_retries: int = 2,
) -> str | None:
    prompt = build_prompt(golden_sparql)
    for _ in range(max_retries + 1):
        raw = await ask_llm_fn(prompt, system=SYSTEM_PROMPT)
        candidate = clean_question(raw)
        if looks_valid(candidate):
            return candidate
    return None


async def generate_questions(
    ask_llm_fn,
    groundings: list[dict],
    max_retries: int = 2,
    concurrency: int = 5,
) -> list[dict]:
    """Runs with a small concurrency cap (free-tier OpenRouter models are
    rate-limited) rather than firing all requests at once. """
    semaphore = asyncio.Semaphore(concurrency)
    results: list[dict] = []

    async def worker(inst: dict):
        async with semaphore:
            print(f"[question_gen] asking for {inst['id']} ...")
            question = await generate_one_question(ask_llm_fn, inst["golden_sparql"], max_retries)
        if question is None:
            print(f"[question_gen] gave up on {inst['id']}: model kept returning malformed output")
            return
        print(f"[question_gen] done  {inst['id']}: {question}")
        results.append({**inst, "generated_question": question})

    await asyncio.gather(*(worker(inst) for inst in groundings))
    return results


def load_groundings(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_questions_jsonl(records: list[dict], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


async def main():
    from mcp.openrouter_client import ask_llm, LOCAL_MODEL , MODEL  # your real, async, module-level function

    print(f"[question_gen] using model: {MODEL}")
    groundings = load_groundings("groundings.jsonl")
    print(f"[question_gen] {len(groundings)} groundings to process")
    records = await generate_questions(ask_llm, groundings)
    records.sort(key=lambda r: r["id"])  # restore input order after concurrent gather
    write_questions_jsonl(records, f"questions.jsonl")
    print(f"Generated {len(records)}/{len(groundings)} questions -> questions.jsonl")


if __name__ == "__main__":
    asyncio.run(main())