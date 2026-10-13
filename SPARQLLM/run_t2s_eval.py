"""
eval_generation/run_t2s_eval.py
Run the T2S evaluation (SPARQL query execution + answer set comparison) on a JSONL file of generated SPARQL queries.
"""

from __future__ import annotations

import os
print("cwd:", os.getcwd())

DATASET_NAME = "sparqllm"
INPUT_JSONL = "t2s_input.jsonl"

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
