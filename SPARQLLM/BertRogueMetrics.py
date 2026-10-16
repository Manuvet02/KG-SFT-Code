"""
BertRogueMetrics.py

ROUGE-1/2/L and BERTScore between golden_sparql and generated_sparql

"""

from __future__ import annotations

import json


def load_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def compute_rouge(golden: str, generated: str, scorer) -> dict:
    scores = scorer.score(golden, generated)
    return {
        "rouge1": scores["rouge1"].fmeasure,
        "rouge2": scores["rouge2"].fmeasure,
        "rougeL": scores["rougeL"].fmeasure,
    }


def compute_all(records: list[dict]) -> list[dict]:
    from rouge_score import rouge_scorer
    from bert_score import score as bertscore_fn

    rouge = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)

    print(f"[text_overlap] computing ROUGE for {len(records)} instances ...")
    rouge_scores = [compute_rouge(r["golden"], r["generated"], rouge) for r in records]

    # BERTScore batches internally and downloads a model on first run
    # (default: roberta-large, ~1.4GB) -- can take a while the first time.
    print(f"[text_overlap] computing BERTScore for {len(records)} instances "
          f"(downloads a model on first run, may take a while) ...")
    goldens = [r["golden"] for r in records]
    generateds = [r["generated"] for r in records]
    P, R, F1 = bertscore_fn(generateds, goldens, lang="en", verbose=False)

    results = []
    for i, r in enumerate(records):
        results.append({
            "id": r["id"],
            "rouge1": rouge_scores[i]["rouge1"],
            "rouge2": rouge_scores[i]["rouge2"],
            "rougeL": rouge_scores[i]["rougeL"],
            "bertscore_precision": P[i].item(),
            "bertscore_recall": R[i].item(),
            "bertscore_f1": F1[i].item(),
        })
    return results


def summarize(results: list[dict]) -> dict:
    if not results:
        return {}
    dims = ("rouge1", "rouge2", "rougeL", "bertscore_precision", "bertscore_recall", "bertscore_f1")
    summary = {dim: sum(r[dim] for r in results) / len(results) for dim in dims}
    summary["n"] = len(results)
    return summary


def write_jsonl(records: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def write_bar_chart(summary: dict, path: str) -> None:
    import matplotlib.pyplot as plt

    dims = ["rouge1", "rouge2", "rougeL", "bertscore_precision", "bertscore_recall", "bertscore_f1"]
    scores = [summary[dim] for dim in dims]

    plt.figure(figsize=(10, 6))
    plt.bar(dims, scores, color='skyblue')
    plt.ylim(0, 1)
    plt.ylabel("Score")
    plt.title("BERTScore and ROUGE Scores Summary")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

if __name__ == "__main__":
    records = load_jsonl("t2s_input.jsonl")
    results = compute_all(records)
    write_jsonl(results, "BertRogueResults.jsonl")

    summary = summarize(results)
    with open("BertRogueSummary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[text_overlap] {len(results)}/{len(records)} scored -> BertRogueResults.jsonl")
    write_bar_chart(summary, "BertRogueSummary.png")
