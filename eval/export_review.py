"""Export shuffled answers for review, hiding strategy and model score."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path


def export_review(report_path: Path, tasks_path: Path, out: Path, seed: int = 42) -> int:
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    task_bytes = tasks_path.read_bytes()
    if report.get("tasks_sha256") != hashlib.sha256(task_bytes).hexdigest():
        raise ValueError("task file does not match the report")
    tasks = {task["id"]: task for task in json.loads(task_bytes)["tasks"]}
    rows = [row for row in report["rows"] if row.get("answer_text")]
    random.Random(seed).shuffle(rows)
    out.mkdir(parents=True, exist_ok=True)
    review_path = out / "review.csv"
    mapping_path = out / "review-key.json"
    if review_path.exists() or mapping_path.exists():
        raise FileExistsError("review export already exists; choose a new directory")
    mapping = {}
    with review_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "review_id",
                "task_id",
                "question",
                "reference_facts",
                "answer",
                "correctness_1_5",
                "completeness_1_5",
                "grounding_1_5",
                "usefulness_1_5",
                "comments",
            ]
        )
        for number, row in enumerate(rows, start=1):
            identifier = f"R{number:03d}"
            task = tasks[row["task_id"]]
            facts = task.get("reference_facts", [])
            writer.writerow(
                [
                    identifier,
                    task["id"],
                    task["query"],
                    "\n".join(facts),
                    row["answer_text"],
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
            mapping[identifier] = {"task_id": row["task_id"], "strategy": row["strategy"]}
    mapping_path.write_text(
        json.dumps(
            {
                "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
                "seed": seed,
                "rows": mapping,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    count = export_review(args.report, args.tasks, args.out, args.seed)
    print(f"exported {count} answers to {args.out}")


if __name__ == "__main__":
    main()
