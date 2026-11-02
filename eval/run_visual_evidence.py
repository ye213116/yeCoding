"""Run a model-free budget sweep and refresh real Docker fixture checks.

This supplements, rather than overwrites, the archived real-model experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from prepare_external import prepare

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "evidence/visual-refresh-20261026")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    commands = []
    start = datetime.now(UTC).isoformat()

    def execute(arguments: list[str], name: str, timeout=180):
        command = [sys.executable, *arguments]
        print(f"Running {name}", flush=True)
        result = subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, timeout=timeout, check=False
        )
        (args.out / f"{name}.log").write_text(result.stdout + result.stderr)
        commands.append({"command": command, "returncode": result.returncode, "log": name})
        if result.returncode:
            raise RuntimeError(f"{name} failed; see preserved log")

    with tempfile.TemporaryDirectory(prefix="yecoding-visual-evidence-") as tmp:
        source = prepare(Path(tmp) / "upstream")
        for budget in [500, 1000, 2000, 4000, 8000]:
            execute(
                [
                    str(HERE / "run_eval.py"),
                    "--repo",
                    str(source),
                    "--tasks",
                    str(HERE / "tasks-python-dotenv.json"),
                    "--budget",
                    str(budget),
                    "--skip-llm",
                    "--ablation",
                    "--out",
                    str(args.out / f"retrieval-{budget}.json"),
                ],
                f"retrieval-{budget}",
            )
    execute(
        [
            str(HERE / "run_repair_eval.py"),
            "--split",
            "all",
            "--out",
            str(args.out / "fixture-validation.json"),
        ],
        "fixture-validation",
    )
    manifest = {
        "started_at_utc": start,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "scope": "Fresh deterministic retrieval and real Docker checks; no new model calls.",
        "retrieval_tasks": 12,
        "budgets": [500, 1000, 2000, 4000, 8000],
        "strategies": ["grep", "file", "symbol", "symbol_no_deps"],
        "retrieval_rows": 240,
        "docker_validation_commands": 12,
        "docker_image_id": subprocess.check_output(
            ["docker", "image", "inspect", "python:3.11-slim", "--format", "{{.Id}}"],
            text=True,
            timeout=10,
        ).strip(),
        "commands": commands,
        "implementation_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                Path(__file__),
                HERE / "run_eval.py",
                HERE / "run_repair_eval.py",
                ROOT / "src/yecoding/rag/context_builder.py",
                ROOT / "src/yecoding/rag/evaluation.py",
            ]
        },
        "outputs_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(args.out.glob("*.json"))
            if p.name != "manifest.json"
        },
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if not k.endswith("sha256")}, indent=2))


if __name__ == "__main__":
    main()
