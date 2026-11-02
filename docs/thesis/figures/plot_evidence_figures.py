"""Render manuscript figures from fresh retrieval and archived model evidence.

No model calls. Input hashes, role-level reconciliation and derived values are saved.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FRESH = ROOT / "eval/evidence/visual-refresh-20261026"
STRATEGIES = ("single", "team", "verified")
ROLES = ("coordinator", "worker", "verifier")
TEAL, BLUE, RUST, OLIVE = "#20756F", "#476C96", "#B14B40", "#777C35"
COLORS = {"single": TEAL, "team": BLUE, "verified": RUST}
ROLE_COLORS = dict(zip(ROLES, (BLUE, TEAL, "#C58E33"), strict=True))
INPUTS = {}


def load(path: Path):
    INPUTS[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text())


def save(fig, name):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    outside = []
    for element in fig.findobj():
        if (
            isinstance(element, matplotlib.text.Text)
            and element.get_visible()
            and element.get_text()
        ):
            extent = element.get_window_extent(renderer)
            if extent.width and extent.height and not fig.bbox.contains(extent.x0, extent.y0):
                outside.append(element.get_text())
            if extent.width and extent.height and not fig.bbox.contains(extent.x1, extent.y1):
                outside.append(element.get_text())
    if outside:
        raise ValueError(f"Text outside {name}: {outside}")
    for extension in ("pdf", "svg", "png"):
        fig.savefig(HERE / f"{name}.{extension}", dpi=220, facecolor="white")
    plt.close(fig)


def main():
    INPUTS[str(Path(__file__).relative_to(ROOT))] = hashlib.sha256(
        Path(__file__).read_bytes()
    ).hexdigest()
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10.5,
            "axes.labelsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#9AA3A8",
            "axes.linewidth": 0.7,
            "axes.labelcolor": "#30383D",
            "text.color": "#30383D",
            "xtick.color": "#505A60",
            "ytick.color": "#505A60",
            "legend.frameon": False,
            "svg.fonttype": "path",
            "pdf.fonttype": 42,
        }
    )
    live = load(ROOT / "eval/evidence/repair-heldout-live.json")
    manifest = load(FRESH / "manifest.json")
    archived_implementation = load(ROOT / "eval/evidence/repair-implementation.json")
    assert manifest["docker_image_id"] == archived_implementation["image_id"]
    for name, expected in manifest["outputs_sha256"].items():
        if hashlib.sha256((FRESH / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Fresh evidence changed: {name}")
    retrieval = [load(FRESH / f"retrieval-{b}.json") for b in manifest["budgets"]]
    fixture = load(FRESH / "fixture-validation.json")
    assert fixture["reference"]["passed"] and fixture["independent_reference"]["passed"]
    assert len(fixture["records"]) == 10
    assert all(r["baseline"]["category"] == "test_failure" for r in fixture["records"])
    for data in retrieval:
        assert data["model"] is None and data["task_count"] == 12 and len(data["rows"]) == 48

    budget_metrics = {}
    for data in retrieval:
        budget_metrics[str(data["budget_tokens"])] = {
            strategy: {
                field: statistics.mean(r[field] for r in data["rows"] if r["strategy"] == strategy)
                for field in ("overall_recall", "overall_line_coverage", "token_estimate")
            }
            for strategy in data["strategies"]
        }
    fig, axes = plt.subplots(1, 2, figsize=(6.55, 3.7))
    styles = [
        ("grep", "Grep excerpts", RUST, "s"),
        ("file", "Whole-file", BLUE, "D"),
        ("symbol", "AST + relations", TEAL, "o"),
        ("symbol_no_deps", "AST, no relations", OLIVE, "^"),
    ]
    for axis, field, title in zip(
        axes,
        ("overall_recall", "overall_line_coverage"),
        ("(a) Relevant-symbol recall", "(b) Symbol-body line coverage"),
        strict=True,
    ):
        for strategy, label, ink, marker in styles:
            values = [budget_metrics[str(b)][strategy][field] for b in manifest["budgets"]]
            axis.plot(
                manifest["budgets"],
                np.array(values) * 100,
                marker=marker,
                label=label,
                color=ink,
                lw=1.6,
                ms=4,
            )
        axis.set_xscale("log", base=2)
        axis.set_xticks(manifest["budgets"], ["0.5k", "1k", "2k", "4k", "8k"])
        axis.set_ylim(0, 102)
        axis.set_yticks([0, 25, 50, 75, 100])
        axis.set_xlabel("Context budget (estimated tokens)")
        axis.set_title(title, loc="left", pad=12)
        axis.grid(axis="y", color="#E6E9EA", lw=0.7)
        axis.set_axisbelow(True)
    axes[0].set_ylabel("Mean over 12 tasks (%)")
    fig.legend(
        *axes[0].get_legend_handles_labels(),
        ncol=2,
        loc="lower center",
        bbox_to_anchor=(0.53, 0.015),
        columnspacing=1.4,
        handlelength=2,
    )
    fig.subplots_adjust(left=0.09, right=0.98, top=0.88, bottom=0.31, wspace=0.29)
    save(fig, "05-context-budget-en")

    runs = {}
    trace = {}
    role_data = {}
    for row in live["records"]:
        for run in row["runs"]:
            key = (row["id"], run["strategy"])
            runs[key] = run
            path = ROOT / "eval/evidence/repair-runs" / run["id"] / "events.jsonl"
            INPUTS[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
            events = [json.loads(line) for line in path.read_text().splitlines()]
            trace[key] = events
            totals = defaultdict(Counter)
            for event in events:
                if event["type"] == "usage":
                    for metric in ("input_tokens", "output_tokens", "total_tokens"):
                        totals[event["role"]][metric] += event["data"]["usage"][metric]
            if sum(t["total_tokens"] for t in totals.values()) != run["usage"]["total_tokens"]:
                raise ValueError(f"Usage not reconciled: {key}")
            role_data[key] = totals
    task_ids = [row["id"] for row in live["records"]]

    # Each cell distinguishes a completed workflow, a checked but incomplete
    # candidate, and a run with no candidate available for post-run checks.
    values = np.zeros((8, 3))
    fig, ax = plt.subplots(figsize=(6.55, 4.4))
    for y, task in enumerate(task_ids):
        for x, strategy in enumerate(STRATEGIES):
            run = runs[task, strategy]
            state = 2 if run["status"] == "verified" else 1 if run["independent"] else 0
            values[y, x] = state
            label = (
                "Complete"
                if state == 2
                else "Patch passes; incomplete"
                if state == 1
                else "No candidate"
            )
            ax.text(
                x,
                y,
                f"{label}\n{run['usage']['total_tokens'] / 1000:.1f}k tokens",
                ha="center",
                va="center",
                fontsize=8.2,
                color="white" if state == 2 else "#343B3F",
            )
    ax.imshow(
        values,
        cmap=ListedColormap(["#F2DBD7", "#F2E3BC", TEAL]),
        vmin=0,
        vmax=2,
        aspect="auto",
        interpolation="nearest",
    )
    ax.set_xticks(range(3), STRATEGIES)
    ax.xaxis.tick_top()
    ax.tick_params(axis="both", length=0, pad=7)
    ax.set_yticks(range(8), task_ids, fontsize=8.5)
    ax.set_xticks(np.arange(-0.5, 3), minor=True)
    ax.set_yticks(np.arange(-0.5, 8), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.text(
        0.5,
        0.04,
        "All incomplete runs stopped on the shared token threshold; n = 8 per strategy.",
        ha="center",
        fontsize=8,
    )
    fig.subplots_adjust(left=0.28, right=0.99, top=0.9, bottom=0.1)
    save(fig, "06-task-outcomes-en")

    fig, ax = plt.subplots(figsize=(6.55, 3.85))
    for y, task in enumerate(task_ids):
        tokens = [runs[task, strategy]["usage"]["total_tokens"] / 1000 for strategy in STRATEGIES]
        ax.plot([min(tokens), max(tokens)], [y, y], color="#C6CDD0", lw=1.3, zorder=1)
        for strategy, marker, value in zip(STRATEGIES, ["o", "s", "^"], tokens, strict=True):
            ax.scatter(
                value,
                y,
                marker=marker,
                s=39,
                color=COLORS[strategy],
                edgecolor="white",
                linewidth=0.5,
                zorder=3,
            )
    ax.axvline(60, ls="--", color="#7D858A", lw=1)
    ax.text(60.8, -0.68, "60k request threshold", fontsize=8, color="#646D72")
    ax.set_yticks(range(8), task_ids, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 84)
    ax.set_xticks([0, 20, 40, 60, 80])
    ax.set_xlabel("Cumulative input + output tokens (thousands)")
    handles = [
        Line2D([], [], marker=m, color=COLORS[s], lw=0, label=s, markersize=6)
        for s, m in zip(STRATEGIES, ["o", "s", "^"], strict=True)
    ]
    ax.legend(handles=handles, ncol=3, loc="lower right", bbox_to_anchor=(1, 1.025))
    ax.grid(axis="x", color="#E6E9EA", lw=0.7)
    ax.set_axisbelow(True)
    fig.subplots_adjust(left=0.28, right=0.98, top=0.82, bottom=0.16)
    save(fig, "06-paired-token-cost-en")

    role_means = {
        strategy: {
            role: statistics.mean(role_data[t, strategy][role]["total_tokens"] for t in task_ids)
            for role in ROLES
        }
        for strategy in STRATEGIES
    }
    fig, axes = plt.subplots(1, 2, figsize=(6.55, 3.55), gridspec_kw={"width_ratios": [1.25, 1]})
    for x, strategy in enumerate(STRATEGIES):
        bottom = 0
        for role in ROLES:
            value = role_means[strategy][role] / 1000
            axes[0].bar(x, value, bottom=bottom, color=ROLE_COLORS[role], width=0.56)
            if value > 3:
                axes[0].text(
                    x,
                    bottom + value / 2,
                    f"{value:.1f}",
                    ha="center",
                    va="center",
                    color="white" if role != "verifier" else "#24292D",
                    fontsize=9,
                )
            bottom += value
        axes[0].text(x, bottom + 1.8, f"{bottom:.1f}k", ha="center", fontsize=9, weight="bold")
    axes[0].set_xticks(range(3), STRATEGIES)
    axes[0].set_ylabel("Mean tokens (thousands)")
    axes[0].set_ylim(0, 77)
    axes[0].set_title("(a) Allocation by active role", loc="left", pad=12)
    shares = [100 * (1 - role_means[s]["worker"] / sum(role_means[s].values())) for s in STRATEGIES]
    axes[1].barh(range(3), shares, color=["#D7DEE0", BLUE, RUST], height=0.55)
    for y, value in enumerate(shares):
        axes[1].text(value + 2.0, y, f"{value:.1f}%", va="center", fontsize=9)
    axes[1].set_yticks(range(3), STRATEGIES)
    axes[1].invert_yaxis()
    axes[1].set_xlim(0, 78)
    axes[1].set_xticks([0, 20, 40, 60])
    axes[1].set_xlabel("Coordinator + verifier share (%)")
    axes[1].set_title("(b) Non-worker share", loc="left", pad=12)
    handles = [Patch(facecolor=ROLE_COLORS[r], label=r.title()) for r in ROLES]
    fig.legend(handles=handles, ncol=3, loc="lower center", bbox_to_anchor=(0.48, 0.005))
    fig.subplots_adjust(left=0.10, right=0.98, top=0.86, bottom=0.29, wspace=0.55)
    save(fig, "06-role-token-allocation-en")

    fig, axes = plt.subplots(2, 1, figsize=(6.55, 4.55), sharex=True, sharey=True)
    cases = [
        ("none-value", "(a) Completed handoffs: none-value"),
        ("trailing-literal", "(b) Tests passed, review incomplete: trailing-literal"),
    ]
    case_audit = []
    for ax, (task, title) in zip(axes, cases, strict=True):
        run, events = runs[task, "verified"], trace[task, "verified"]
        usage = [
            (e["elapsed"], e["data"]["usage"]["total_tokens"])
            for e in events
            if e["type"] == "usage"
        ]
        times = [0] + [e[0] for e in usage] + [run["duration"]]
        cumulative = [0] + list(np.cumsum([e[1] for e in usage]) / 1000)
        cumulative += [cumulative[-1]]
        ax.step(times, cumulative, where="post", color="#343B3F", lw=1.4, zorder=3)
        intervals = []
        for role in ROLES:
            start = next(
                e["elapsed"] for e in events if e["type"] == "agent.started" and e["role"] == role
            )
            completed = next(
                (
                    e["elapsed"]
                    for e in events
                    if e["type"] == "agent.completed" and e["role"] == role
                ),
                None,
            )
            end = completed if completed is not None else run["duration"]
            ax.axvspan(start, end, color=ROLE_COLORS[role], alpha=0.13, lw=0)
            ax.text(
                (start + end) / 2,
                6,
                role.title(),
                ha="center",
                fontsize=7.5,
                color=ROLE_COLORS[role],
            )
            intervals.append(
                {"role": role, "start": start, "end": end, "completed": completed is not None}
            )
        assert run["attempts"][0]["passed"] is True
        test_time = next(
            e["elapsed"] for e in events if e["type"] == "agent.started" and e["role"] == "verifier"
        )
        test_tokens = sum(value for time, value in usage if time < test_time) / 1000
        ax.scatter(test_time, test_tokens, s=34, marker="D", color=TEAL, zorder=4)
        ax.annotate(
            "Fixed tests passed",
            (test_time, test_tokens),
            xytext=(-32, -23),
            textcoords="offset points",
            fontsize=7.5,
            arrowprops={"arrowstyle": "-", "color": "#7D858A", "lw": 0.6},
        )
        ax.axhline(60, ls="--", color="#7D858A", lw=0.8)
        ax.set_title(title, loc="left", pad=9, fontsize=10)
        ax.set_ylabel("Tokens (k)")
        ax.set_ylim(0, 77)
        ax.set_xlim(0, 23)
        ax.set_xticks([0, 5, 10, 15, 20])
        ax.set_yticks([0, 30, 60])
        ax.text(
            run["duration"] + 0.35,
            cumulative[-1],
            f"{cumulative[-1]:.1f}k\n"
            f"{'complete' if run['status'] == 'verified' else 'budget stop'}",
            va="center",
            fontsize=8,
            color=TEAL if run["status"] == "verified" else RUST,
        )
        case_audit.append(
            {
                "task": task,
                "run_id": run["id"],
                "intervals": intervals,
                "verifier_entry_after_test": test_time,
            }
        )
    axes[1].set_xlabel("Elapsed seconds within the archived run")
    fig.subplots_adjust(left=0.1, right=0.98, top=0.9, bottom=0.13, hspace=0.52)
    save(fig, "06-real-execution-traces-en")

    case = runs["none-value", "single"]
    patch = ROOT / "eval/evidence/repair-runs" / case["id"] / "candidate.patch"
    INPUTS[str(patch.relative_to(ROOT))] = hashlib.sha256(patch.read_bytes()).hexdigest()
    assert "+        if result is None:" in patch.read_text()
    fig = plt.figure(figsize=(6.55, 3.45))
    ax = fig.add_axes([0.04, 0.09, 0.92, 0.82])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0, 0.97, "Actual candidate: dotenv/variables.py", fontsize=11, weight="bold")
    code_lines = [
        "  result = env.get(self.name, default)",
        "+ if result is None:",
        '+     return ""',
        "  return str(result)",
    ]
    for i, line in enumerate(code_lines):
        y = 0.78 - i * 0.115
        if line.startswith("+"):
            ax.axhspan(y - 0.035, y + 0.067, xmin=0, xmax=0.91, color="#E4F1EB", lw=0)
        ax.text(
            0.02,
            y,
            line,
            fontfamily="DejaVu Sans Mono",
            fontsize=10,
            color=TEAL if line.startswith("+") else "#343B3F",
        )
    ax.plot([0.05, 0.95], [0.26, 0.26], color="#CCD3D6", lw=0.8)
    for x, label, value, ink in [
        (0.06, "Mutated baseline", "1 of 9 methods fails", RUST),
        (0.40, "Candidate acceptance", "9 of 9 pass", TEAL),
        (0.73, "Post-run extended suite", "13 of 13 pass", TEAL),
    ]:
        ax.scatter(x, 0.16, s=45, color=ink)
        ax.text(x + 0.025, 0.155, label, fontsize=8, va="center")
        ax.text(x, 0.035, value, fontsize=8, color=ink)
    save(fig, "06-concrete-patch-en")

    output = {
        "fresh_manifest": str((FRESH / "manifest.json").relative_to(ROOT)),
        "retrieval_budget_metrics": budget_metrics,
        "role_mean_tokens": role_means,
        "non_worker_share_percent": dict(zip(STRATEGIES, shares, strict=True)),
        "role_usage_reconciled_runs": len(runs),
        "timeline_cases": case_audit,
        "source_sha256": INPUTS,
        "matplotlib_version": matplotlib.__version__,
        "new_model_calls": 0,
        "generated_figures": [
            "05-context-budget-en",
            "06-task-outcomes-en",
            "06-paired-token-cost-en",
            "06-role-token-allocation-en",
            "06-real-execution-traces-en",
            "06-concrete-patch-en",
        ],
    }
    (HERE.parent / "notes/visual-evidence-statistics.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "figures": output["generated_figures"],
                "role_means": role_means,
                "non_worker_share_percent": output["non_worker_share_percent"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
