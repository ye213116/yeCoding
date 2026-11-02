"""Prepare the development repair example without modifying the application repository."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from run_repair_eval import COMMAND, prepare_task, tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, default=Path(tempfile.gettempdir()) / "yecoding-repair-demo"
    )
    args = parser.parse_args()
    task = next(task for task in tasks() if task["id"] == "default-value")
    root = prepare_task(args.out, task)
    print(f"Workspace: {root}")
    print(f"Task: {task['prompt']}")
    print(f"Acceptance: {COMMAND}")
    print(
        "Configure your model key in the environment, then run "
        "yecoding repair with --cwd and --test."
    )


if __name__ == "__main__":
    main()
