"""
eval_generation/run_agent.py

Run the SparqLLMAgent on a set of generated questions and save the results.
"""


from __future__ import annotations

import json
import os
import sys
import time

_this_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(_this_dir)       # backend/app
backend_dir = os.path.dirname(app_dir)     # backend
for _p in (app_dir, backend_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agent.agent import SparqLLMAgent  # noqa: E402  (import must follow path setup)


# JSONL helpers

def load_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(record: dict, path: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_jsonl(records: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# Agent round-trip- retry-with-backoff on failures, incremental writes, resumable on crash.

def run_one(agent: SparqLLMAgent, question: str, max_retries: int = 2) -> dict | None:
    """Returns {"query": ..., "summary": ...} or None after exhausting retries."""
    for attempt in range(max_retries + 1):
        try:
            res = agent.ask(question)
        except Exception as exc:
            wait = 3 * (attempt + 1)
            print(f"[run_agent] agent.ask failed ({exc!r}), retrying in {wait}s "
                  f"(attempt {attempt + 1}/{max_retries + 1})")
            time.sleep(wait)
            continue

        if res and res.get("query"):
            return res
        print(f"[run_agent] empty/malformed response (attempt {attempt + 1}/{max_retries + 1})")

    return None


def run_all(
    questions_path: str = "questions.jsonl",
    runs_path: str = "agent_runs.jsonl",
    t2s_path: str = "t2s_input.jsonl",
    max_retries: int = 2,
    limit: int | None = None,
) -> None:
    groundings = load_jsonl(questions_path)
    if limit:
        groundings = groundings[:limit]

    already_done: set[str] = set()
    if os.path.exists(runs_path):
        already_done = {r["id"] for r in load_jsonl(runs_path)}
        if already_done:
            print(f"[run_agent] resuming: {len(already_done)} already done in {runs_path}")

    print("[run_agent] initializing SparqLLMAgent ...")
    try:
        agent = SparqLLMAgent()
        print("[run_agent] agent ready")
    except Exception as e:
        print(f"Errore nell'inizializzazione dell'agente: {e}")
        return

    todo = [inst for inst in groundings if inst["id"] not in already_done]
    print(f"[run_agent] {len(todo)}/{len(groundings)} to process")

    for i, inst in enumerate(todo, 1):
        question = inst["generated_question"]
        print(f"[run_agent] ({i}/{len(todo)}) asking {inst['id']}: {question}")
        res = run_one(agent, question, max_retries)
        if res is None:
            print(f"[run_agent] gave up on {inst['id']} after {max_retries + 1} attempts")
            continue

        record = {
            **inst,
            "generated_sparql": res["query"],
            "agent_summary": res.get("summary", ""),
        }
        append_jsonl(record, runs_path)
        print(f"[run_agent] done  {inst['id']}")

    export_t2s_input(runs_path, t2s_path)


def export_t2s_input(runs_path: str, t2s_path: str) -> None:
    """Converts the completed agent_runs.jsonl into the minimal schema that t2s-metrics expects. """
    if not os.path.exists(runs_path):
        print(f"[run_agent] {runs_path} not found, nothing to export yet.")
        return

    records = load_jsonl(runs_path)
    t2s_records = [
        {
            "id": r["id"],
            "golden": r["golden_sparql"].strip(),
            "generated": r["generated_sparql"].strip(),
            # Default false, same convention as export_jsonl.py. Flip to
            # true by hand in t2s_input.jsonl for questions where row order
            # genuinely matters (e.g. "closest", "first", "shortest").
            "order_matters": False,
        }
        for r in records
        if r.get("generated_sparql")
    ]
    write_jsonl(t2s_records, t2s_path)
    print(f"[run_agent] exported {len(t2s_records)}/{len(records)} -> {t2s_path}")


if __name__ == "__main__":
    run_all()
