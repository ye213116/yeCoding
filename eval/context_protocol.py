"""Shared protocol and task-level statistics for the three-line experiment."""

from __future__ import annotations

import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

BASELINE = "7a1783bc723d358090a3c9f318d7bf795903138e"
MINI_SHA = "a83fcae82d2a08f0ee0c688f9d137b3566c097f8"
LINES = ("original", "evidence", "mini")
ABLATIONS = ("no_structure", "no_dedup")
DEFAULTS = {
    "seed": 20261030,
    "calls": 64,
    "tokens": 120_000,
    "seconds": 900,
    "output_tokens": 8192,
    "evidence_tokens": 16_000,
    "temperature": 0,
    "repeats": 3,
}


def configure(config, limits):
    config.llm.temperature = 0
    config.llm.max_tokens = limits["output_tokens"]
    config.llm.timeout = 120
    config.features.memory = config.features.skill = config.features.mcp = False
    config.features.context_compression = config.features.code_index = True
    config.features.audit_log = False
    config.prompt.custom_prompt_paths = []
    config.prompt.agent_mode = "react"
    config.policy.path_guard_enabled = config.policy.command_guard_enabled = True
    config.policy.hitl_mode = "never"


def controls(config):
    data = asdict(config)
    result = {key: data[key] for key in ("llm", "tools", "memory", "features", "policy", "prompt")}
    result["llm"].pop("api_key", None)
    result["policy"].pop("audit_log_path", None)
    return result


def control_fingerprint(config):
    return hashlib.sha256(json.dumps(controls(config), sort_keys=True).encode()).hexdigest()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def select_tasks(rows: list[dict], count: int, seed: int) -> list[dict]:
    """Round-robin over repositories; never inspect patches or model outcomes."""
    grouped = defaultdict(list)
    for row in sorted(rows, key=lambda x: x["instance_id"]):
        grouped[row["repo"]].append(row)
    rng = random.Random(seed)
    names = sorted(grouped)
    rng.shuffle(names)
    for name in names:
        rng.shuffle(grouped[name])
    chosen = []
    while len(chosen) < count:
        added = False
        for name in names:
            if grouped[name] and len(chosen) < count:
                chosen.append(grouped[name].pop())
                added = True
        if not added:
            raise ValueError(f"only {len(chosen)} eligible tasks; requested {count}")
    return chosen


def schedule(ids: list[str], *, repeats=3, ablations=False):
    lines = LINES + ABLATIONS if ablations else LINES
    jobs = []
    for repeat in range(repeats):
        for index, instance in enumerate(ids):
            offset = (index + repeat) % len(lines)
            for line in lines[offset:] + lines[:offset]:
                jobs.append(
                    {
                        "instance_id": instance,
                        "line": line,
                        "repeat": repeat + 1,
                        "id": f"r{repeat + 1}/{instance}/{line}",
                    }
                )
    return jobs


def summarize(records: list[dict], *, seed=20261030, bootstrap=2000):
    summary = {}
    for line in LINES + ABLATIONS:
        runs = [r for r in records if r["line"] == line]
        if not runs:
            continue
        summary[line] = {
            "runs": len(runs),
            "resolved": sum(r.get("resolved") is True for r in runs),
            "ungraded": sum(r.get("resolved") is None for r in runs),
            "normal_completion": sum(r.get("completed", False) for r in runs),
            "input_tokens": sum(r["usage"]["input_tokens"] for r in runs),
            "output_tokens": sum(r["usage"]["output_tokens"] for r in runs),
            "total_tokens": sum(r["usage"]["total_tokens"] for r in runs),
            "mean_seconds": statistics.mean(r["seconds"] for r in runs),
            "cost_estimate_usd": (
                sum(r["cost_usd"] for r in runs if r.get("cost_usd") is not None)
                if any(r.get("cost_usd") is not None for r in runs)
                else None
            ),
            "cost_unknown_runs": sum(r.get("cost_usd") is None for r in runs),
            "cache_hit_tokens": sum(r["usage"].get("cache_hit_tokens", 0) for r in runs),
            "cache_miss_tokens": sum(r["usage"].get("cache_miss_tokens", 0) for r in runs),
            "llm_calls": sum(r.get("llm_calls", 0) for r in runs),
            "statuses": dict(Counter(r.get("status", "unknown") for r in runs)),
        }
    reference = {(r["instance_id"], r["repeat"]): r for r in records if r["line"] == "original"}
    paired = {}
    for line in LINES[1:] + ABLATIONS:
        clusters = defaultdict(list)
        resolution_clusters = defaultdict(list)
        both_solved = []
        for run in records:
            base = reference.get((run["instance_id"], run["repeat"]))
            if run["line"] != line or base is None:
                continue
            clusters[run["instance_id"]].append(
                run["usage"]["input_tokens"] - base["usage"]["input_tokens"]
            )
            resolution_clusters[run["instance_id"]].append(
                int(run.get("resolved") is True) - int(base.get("resolved") is True)
            )
            if run.get("resolved") is True and base.get("resolved") is True:
                both_solved.append(
                    {
                        "instance_id": run["instance_id"],
                        "repeat": run["repeat"],
                        "input_delta": run["usage"]["input_tokens"] - base["usage"]["input_tokens"],
                        "cost_delta_usd": (
                            run["cost_usd"] - base["cost_usd"]
                            if run.get("cost_usd") is not None and base.get("cost_usd") is not None
                            else None
                        ),
                    }
                )
        means = [statistics.mean(v) for _, v in sorted(clusters.items())]
        if means:
            rng = random.Random(seed)
            draws = sorted(
                statistics.mean(rng.choices(means, k=len(means))) for _ in range(bootstrap)
            )
            resolution_means = [statistics.mean(v) for _, v in sorted(resolution_clusters.items())]
            resolution_draws = sorted(
                statistics.mean(rng.choices(resolution_means, k=len(resolution_means)))
                for _ in range(bootstrap)
            )
            paired[line] = {
                "tasks": len(means),
                "mean_input_delta": statistics.mean(means),
                "task_bootstrap_95pct": [
                    draws[int(0.025 * bootstrap)],
                    draws[min(bootstrap - 1, int(0.975 * bootstrap))],
                ],
                "both_solved_pairs": both_solved,
                "mean_resolution_delta": statistics.mean(resolution_means),
                "resolution_task_bootstrap_95pct": [
                    resolution_draws[int(0.025 * bootstrap)],
                    resolution_draws[min(bootstrap - 1, int(0.975 * bootstrap))],
                ],
            }
    return {"by_line": summary, "paired_vs_original": paired}
