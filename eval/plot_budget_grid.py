"""Plot a completed grid with: uv run --with matplotlib python -m eval.plot_budget_grid."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def plot(path: Path):
    data = json.loads(path.read_text())
    if not data.get("finished_at") or len(data["results"]) != len(data["schedule"]):
        raise ValueError("refusing to plot an incomplete grid as final results")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    protocol = data["protocol"]
    budgets = protocol["budgets"]
    modes = protocol["modes"]
    colors = {"react": "#2463a6", "plan": "#df8b20", "team": "#7f56a4", "repair": "#22846b"}
    labels = {"react": "ReAct", "plan": "Plan", "team": "Team", "repair": "Repair"}
    positions = list(range(len(budgets)))
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3), layout="constrained")
    for mode in modes:
        summaries = [data["summary"][f"{budget}/{mode}"] for budget in budgets]
        code = [100 * s["independent_passed"] / s["runs"] for s in summaries]
        complete = [100 * s["completed_and_passed"] / s["runs"] for s in summaries]
        tokens = [s["mean_tokens"] / 1000 for s in summaries]
        for axis, values in zip(axes, [code, complete, tokens], strict=True):
            axis.plot(positions, values, marker="o", color=colors[mode], label=labels[mode])
        for x, summary in enumerate(summaries):
            repeats = summary["per_repeat"]
            for index, repeat in enumerate(repeats):
                jitter = (index - (len(repeats) - 1) / 2) * 0.035
                for axis, field in zip(
                    axes[:2], ["independent_passed", "completed_and_passed"], strict=True
                ):
                    axis.scatter(
                        x + jitter,
                        100 * repeat[field] / repeat["runs"],
                        color=colors[mode],
                        s=17,
                        alpha=0.35,
                        zorder=2,
                    )
    titles = [
        "Additional tests passed",
        "Normal return and tests passed",
        "Mean actual model usage",
    ]
    for axis, title in zip(axes, titles, strict=True):
        axis.set_title(title, fontsize=11)
        axis.set_xticks(positions, [f"{budget // 1000}k" for budget in budgets])
        axis.set_xlabel("Cumulative token budget")
        axis.grid(axis="y", alpha=0.2)
        axis.spines[["top", "right"]].set_visible(False)
    for axis in axes[:2]:
        axis.set_ylim(-4, 106)
        axis.set_ylabel("Runs (%)")
    axes[2].set_ylabel("Tokens (thousands), including failed runs")
    axes[2].set_ylim(bottom=0)
    fig.suptitle(
        f"{protocol['model']} | output cap {protocol['output_tokens']:,} | "
        f"{len(protocol['task_ids'])} artificial defects x {protocol['repeats']} repeats",
        fontsize=12,
    )
    axes[2].legend(fontsize=9, loc="best")
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(path.parent / f"budget-comparison.{suffix}", dpi=180)
    plt.close(fig)
    return path.parent / "budget-comparison.png"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(plot(args.path))


if __name__ == "__main__":
    main()
