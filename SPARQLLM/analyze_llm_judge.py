"""
eval_generation/analyze_llm_judge.py

Turns llm_judge_results.jsonl into something you can actually put in the
report: an overall summary, a per-CQ breakdown (to spot which questions the
system struggles with), and the worst-scoring examples with their rationale
(for the qualitative discussion section).

Input:  llm_judge_results.jsonl (from llm_judge.py)
Output: llm_judge_report.md     -- markdown tables + worst-case examples
        llm_judge_chart.png      -- bar chart of the three mean dimensions
                                     (requires matplotlib: pip install matplotlib)
"""

from __future__ import annotations

import json
from collections import defaultdict


DIMENSIONS = ("correctness", "efficiency", "readability")


def load_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def overall_summary(results: list[dict]) -> dict:
    return {dim: sum(r[dim] for r in results) / len(results) for dim in DIMENSIONS} | {"n": len(results)}


def per_cq_breakdown(results: list[dict]) -> dict[str, dict]:
    by_cq: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_cq[r.get("cq_ref", "?")].append(r)

    breakdown = {}
    for cq_ref, rows in sorted(by_cq.items(), key=lambda kv: kv[0]):
        breakdown[cq_ref] = {dim: sum(r[dim] for r in rows) / len(rows) for dim in DIMENSIONS}
        breakdown[cq_ref]["n"] = len(rows)
    return breakdown


def worst_examples(results: list[dict], n: int = 5) -> list[dict]:
    """Lowest correctness first -- that's the dimension most worth discussing
    qualitatively (efficiency/readability issues are less critical)."""
    return sorted(results, key=lambda r: r["correctness"])[:n]


def write_markdown_report(results: list[dict], out_path: str) -> None:
    summary = overall_summary(results)
    breakdown = per_cq_breakdown(results)
    worst = worst_examples(results)

    lines = ["# LLM-as-judge evaluation report", ""]

    lines.append("## Overall")
    lines.append(f"n = {summary['n']} instances judged\n")
    lines.append("| Dimension | Mean score |")
    lines.append("|---|---|")
    for dim in DIMENSIONS:
        lines.append(f"| {dim} | {summary[dim]:.3f} |")
    lines.append("")

    lines.append("## Breakdown by competency question")
    lines.append("| CQ | n | correctness | efficiency | readability |")
    lines.append("|---|---|---|---|---|")
    for cq_ref, scores in breakdown.items():
        lines.append(
            f"| {cq_ref} | {scores['n']} | {scores['correctness']:.3f} "
            f"| {scores['efficiency']:.3f} | {scores['readability']:.3f} |"
        )
    lines.append("")

    lines.append("## Lowest-scoring examples (by correctness)")
    lines.append("Useful for the qualitative discussion -- these are the cases")
    lines.append("worth explaining in the report, not just citing the aggregate number.\n")
    for r in worst:
        lines.append(f"**{r['id']}** ({r.get('cq_ref', '?')}) -- correctness {r['correctness']:.2f}")
        lines.append(f"> {r.get('rationale', '(no rationale recorded)')}")
        lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[analyze_llm_judge] wrote {out_path}")


def write_bar_chart(results: list[dict], out_path: str) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[analyze_llm_judge] matplotlib not installed, skipping chart "
              "(pip install matplotlib to enable it)")
        return

    summary = overall_summary(results)
    values = [summary[dim] for dim in DIMENSIONS]

    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(DIMENSIONS, values, color=["#4C72B0", "#DD8452", "#55A868"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Mean score (0-1)")
    ax.set_title(f"LLM-as-judge results (n={summary['n']})")
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.02, f"{val:.2f}", ha="center")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"[analyze_llm_judge] wrote {out_path}")


if __name__ == "__main__":
    results = load_jsonl("llm_judge_results.jsonl")
    write_markdown_report(results, "llm_judge_report.md")
    write_bar_chart(results, "llm_judge_chart.png")
