"""
eval_generation/run_t2s_eval.py

Python-API equivalent of run_t2s_eval.sh, using t2smetrics.run_experiments
directly instead of shelling out to the CLI. Same config, same prioritized
metric subset -- pick whichever fits your workflow better.
"""

from __future__ import annotations

import os
print("cwd:", os.getcwd())

DATASET_NAME = "sparqllm"
INPUT_JSONL = "t2s_input.jsonl"

# See the note in run_t2s_eval.sh: confirm this is the real SPARQL query
# endpoint (GraphDB's own port is usually 7200/repositories/KG-SFT;
ENDPOINT_URL = "http://localhost:7200/repositories/KG-SFT"

METRICS = [
    "query_execution",
    "answerset_precision",
    "answerset_recall",
    "answerset_f1",
    "sp-f1",
    "query_exact_match",
]


def main():
    if not os.path.exists(INPUT_JSONL):
        raise FileNotFoundError(f"{INPUT_JSONL} not found -- run export_jsonl.py first.")

    from t2smetrics import run_experiments

    run_experiments.run(
        dataset=DATASET_NAME,
        jsonl_evals=[INPUT_JSONL],
        metrics_list=METRICS,
        execution_backend_endpoint_url=ENDPOINT_URL,
        per_query=True,
        verbose=True,
    )
    print(f"Done. Results under ./datasets/{DATASET_NAME}/results/ (default export path).")


if __name__ == "__main__":
    main()
