"""Pinned SWE-bench experiment: prepare, run, grade, and summarize.

Use the isolated environment installed from context-requirements.lock.
No model calls are made by prepare. Existing attempts are never overwritten.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from dataclasses import asdict
from pathlib import Path

from eval.context_protocol import (
    BASELINE,
    DEFAULTS,
    MINI_SHA,
    configure,
    control_fingerprint,
    controls,
    digest,
    save,
    schedule,
    select_tasks,
    summarize,
)

ROOT = Path(__file__).resolve().parent.parent
DATASET = "princeton-nlp/SWE-bench_Lite"
DATASET_REVISION = "6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2"


def command(args, **kwargs):
    return subprocess.check_output(args, text=True, timeout=300, **kwargs).strip()


def image_name(instance):
    return (
        "docker.io/swebench/sweb.eval.x86_64."
        + instance.replace("__", "_1776_").lower()
        + ":latest"
    )


def implementation_manifest():
    paths = sorted((ROOT / "src/yecoding").rglob("*.py"))
    paths += sorted((ROOT / "eval").glob("context*.*"))
    paths += [ROOT / "uv.lock", ROOT / "pyproject.toml"]
    return {str(p.relative_to(ROOT)): digest(p) for p in paths if p.is_file()}


def freeze_code(out, manifest):
    for relative, expected in manifest.items():
        destination = out / ("improved" if relative.startswith("src/") else "harness") / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
        if digest(destination) != expected:
            raise ValueError("source changed during freeze: " + relative)
    (out / "harness/eval/__init__.py").write_text('"""Frozen experiment harness."""\n')


def prepare(out: Path):
    from datasets import load_dataset

    from yecoding.config import load_config
    from yecoding.context.trace import TraceRecorder
    from yecoding.llm import create_llm_client

    if out.exists():
        raise ValueError("prepare output exists; choose a new directory")
    # Verify actual server, executable containers and Linux bind mounts first.
    command(["docker", "version", "--format", "{{.Server.Version}}"])
    command(
        [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "--mount",
            f"type=bind,src={ROOT},dst=/check,readonly",
            "python:3.11-slim",
            "python",
            "-c",
            "from pathlib import Path; assert Path('/check/uv.lock').is_file()",
        ]
    )
    if importlib.metadata.version("mini-swe-agent") != "2.4.6":
        raise ValueError("mini-swe-agent must be 2.4.6")
    if importlib.metadata.version("swebench") != "4.1.0":
        raise ValueError("classic Lite tasks require pinned swebench 4.1.0")
    mini = ROOT / ".git/context-tools/mini-swe-agent"
    if command(["git", "-C", str(mini), "rev-parse", "HEAD"]) != MINI_SHA:
        raise ValueError("mini checkout does not match pinned upstream commit")
    if command(["git", "-C", str(mini), "status", "--porcelain"]):
        raise ValueError("mini checkout has local modifications")
    out.mkdir(parents=True)
    os.environ["MSWEA_GLOBAL_CONFIG_DIR"] = str(out / "mini-config")
    os.environ["MSWEA_SILENT_STARTUP"] = "1"
    import minisweagent

    mini_files = [
        "agents/default.py",
        "models/litellm_model.py",
        "environments/docker.py",
        "config/benchmarks/swebench.yaml",
    ]
    mini_hashes = {}
    for relative in mini_files:
        installed = Path(minisweagent.__file__).parent / relative
        if digest(installed) != digest(mini / "src/minisweagent" / relative):
            raise ValueError("installed mini does not match frozen checkout: " + relative)
        mini_hashes[relative] = digest(installed)
    baseline_archive = out / "baseline.tar.gz"
    subprocess.run(
        ["git", "archive", "--format=tar.gz", f"--output={baseline_archive}", BASELINE],
        cwd=ROOT,
        check=True,
    )
    frozen = out / "baseline"
    frozen.mkdir()
    with tarfile.open(baseline_archive) as archive:
        archive.extractall(frozen, filter="data")
    config = load_config(ROOT)
    configure(config, DEFAULTS)
    client = create_llm_client(config.llm)
    public_config = TraceRecorder(out / "unused", secrets=(config.llm.api_key,))._redact(
        controls(config)
    )
    protocol = {
        "kind": "three-line SWE-bench Lite context experiment",
        "prepared": False,
        "baseline_sha": BASELINE,
        "baseline_archive_sha256": digest(baseline_archive),
        "mini_version": "2.4.6",
        "mini_sha": MINI_SHA,
        "mini_source_hashes": mini_hashes,
        "dataset": DATASET,
        "dataset_revision": DATASET_REVISION,
        "swebench_version": importlib.metadata.version("swebench"),
        "packages": sorted(
            f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions()
        ),
        "limits": DEFAULTS,
        "config": public_config,
        "control_fingerprint": control_fingerprint(config),
        "price_snapshot": asdict(client.price_profile) if client.price_profile else None,
        "price_note": "Dated configured rates; estimates, not verified provider invoices",
        "implementation": implementation_manifest(),
        "tasks": {},
        "preflight": [],
        "protocol_notes": [
            "Original and evidence use identical evaluation adapters and prompts",
            "Mini retains upstream agent, model action parsing, prompts and observations",
            "Agent commands run in isolated, network-disabled task containers",
            "No gold patch or test_patch is sent to any agent",
            "Formal and development tasks are separate upstream splits",
        ],
        "dynamic_context": {"cwd": "/testbed", "time": "2026-10-30T00:00:00+00:00"},
    }
    freeze_code(out, protocol["implementation"])
    protocol["frozen_files"] = {
        str(path.relative_to(out)): digest(path)
        for folder in [out / "baseline/src", out / "improved/src", out / "harness"]
        for path in sorted(folder.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    save(out / "protocol.json", protocol)
    private = {}
    for split, count in [("dev", 5), ("test", 20)]:
        rows = list(load_dataset(DATASET, revision=DATASET_REVISION, split=split))
        selected = select_tasks(rows, count, DEFAULTS["seed"])
        protocol["tasks"][split] = []
        for row in selected:
            name = image_name(row["instance_id"])
            record = {"instance_id": row["instance_id"], "image_tag": name, "status": "checking"}
            protocol["preflight"].append(record)
            save(out / "protocol.json", protocol)
            print(f"PREFLIGHT {split} {row['instance_id']}", flush=True)
            try:
                subprocess.run(
                    ["docker", "pull", name], check=True, timeout=1200, stdout=subprocess.DEVNULL
                )
                inspect = json.loads(command(["docker", "image", "inspect", name]))[0]
                pinned_image = inspect["RepoDigests"][0]
                head = command(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "--network=none",
                        "--entrypoint",
                        "/bin/bash",
                        "-w",
                        "/testbed",
                        pinned_image,
                        "-c",
                        "source /opt/miniconda3/etc/profile.d/conda.sh && "
                        "conda activate testbed && python -c 'import sys' && git rev-parse HEAD",
                    ]
                )
                if head.splitlines()[-1] != row["base_commit"]:
                    raise ValueError("task image does not contain requested base commit")
                record.update(status="passed", image=pinned_image, image_id=inspect["Id"])
                safe = {
                    k: row[k] for k in ("instance_id", "repo", "base_commit", "problem_statement")
                }
                safe["image"] = pinned_image
                protocol["tasks"][split].append(safe)
                private[row["instance_id"]] = row
            except Exception as exc:
                record.update(status="environment_error", error=str(exc))
                save(out / "protocol.json", protocol)
                raise
            save(out / "protocol.json", protocol)
    # Evaluator-only dataset, never a worker argument or mounted agent file.
    private_path = out / "evaluator-dataset.json"
    save(private_path, list(private.values()))
    private_path.chmod(0o600)
    protocol["evaluator_dataset_sha256"] = digest(private_path)
    protocol["prepared"] = True
    save(out / "protocol.json", protocol)


def grade(out: Path, run: Path, job, protocol):
    expected = next(
        t
        for tasks in protocol["tasks"].values()
        for t in tasks
        if t["instance_id"] == job["instance_id"]
    )
    local_id = command(
        ["docker", "image", "inspect", image_name(job["instance_id"]), "--format", "{{.Id}}"]
    )
    if local_id != next(
        p["image_id"] for p in protocol["preflight"] if p["instance_id"] == expected["instance_id"]
    ):
        raise ValueError("evaluator image tag changed after protocol freeze")
    prediction = {
        "instance_id": job["instance_id"],
        "model_name_or_path": job["line"],
        "model_patch": (run / "final.patch").read_text(),
    }
    save(run / "predictions.json", [prediction])
    if not prediction["model_patch"].strip():
        return {"resolved": False, "grading_status": "empty_patch", "grading_run_id": None}
    run_id = "ctx-" + digest(run / "predictions.json")[:16] + "-" + str(time.time_ns())
    args = [
        sys.executable,
        "-m",
        "swebench.harness.run_evaluation",
        "--dataset_name",
        str(out / "evaluator-dataset.json"),
        "--predictions_path",
        str(run / "predictions.json"),
        "--instance_ids",
        job["instance_id"],
        "--max_workers",
        "1",
        "--run_id",
        run_id,
        "--namespace",
        "swebench",
    ]
    with (run / "grading.log").open("w") as log:
        proc = subprocess.run(args, cwd=out, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
    reports = list((out / "logs/evaluation" / run_id).rglob("report.json"))
    if not reports:
        return {
            "resolved": None,
            "grading_status": "environment_error",
            "grading_exit_code": proc.returncode,
            "grading_run_id": run_id,
        }
    report = json.loads(reports[0].read_text())
    resolved = report[job["instance_id"]]["resolved"]
    return {"resolved": bool(resolved), "grading_status": "graded", "grading_run_id": run_id}


def run(out: Path, split: str, *, ablations=False):
    from yecoding.config import load_config

    protocol = json.loads((out / "protocol.json").read_text())
    if not protocol["prepared"]:
        raise ValueError("environment preflight must complete before model runs")
    if protocol["implementation"] != implementation_manifest():
        raise ValueError("implementation changed since prepare; use a new experiment directory")
    if digest(out / "baseline.tar.gz") != protocol["baseline_archive_sha256"]:
        raise ValueError("baseline archive changed")
    if digest(out / "evaluator-dataset.json") != protocol["evaluator_dataset_sha256"]:
        raise ValueError("evaluator dataset changed")
    config = load_config(ROOT)
    configure(config, protocol["limits"])
    if not config.llm.api_key:
        raise ValueError("model key must be configured before running agents")
    if control_fingerprint(config) != protocol["control_fingerprint"]:
        raise ValueError("control configuration changed after prepare")
    tasks = {t["instance_id"]: t for t in protocol["tasks"][split]}
    jobs = schedule(list(tasks), repeats=1 if split == "dev" else 3, ablations=ablations)
    if split == "test":
        development = out / "dev/results.json"
        if not development.exists() or not json.loads(development.read_text()).get(
            "pipeline_passed"
        ):
            raise ValueError("three-line development pipeline must pass before formal evaluation")
    records = []
    for job in jobs:
        if any(
            digest(out / path) != expected for path, expected in protocol["frozen_files"].items()
        ):
            raise ValueError("frozen experiment source changed")
        directory = out / split / job["id"]
        if directory.exists():
            raise ValueError(f"attempt exists; never overwrite or silently resume: {directory}")
        directory.mkdir(parents=True)
        job_file = directory / "job.json"
        save(
            job_file,
            {
                **job,
                "task": tasks[job["instance_id"]],
                "limits": protocol["limits"],
                "experiment": str(out),
                "config_root": str(ROOT),
                "source_root": str(out / "improved"),
            },
        )
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(out / "harness")
        print(f"START {job['id']}", flush=True)
        worker_error = "worker exited without an accountable result"
        attempt_started = time.monotonic()
        try:
            with (directory / "worker.log").open("w") as log:
                subprocess.run(
                    [sys.executable, "-m", "eval.context_worker", str(job_file)],
                    cwd=out / "harness",
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=protocol["limits"]["seconds"] + 180,
                )
        except subprocess.TimeoutExpired:
            worker_error = "worker wall-clock timeout"
        finally:
            cleanup_job(job_file)
        result_file = directory / "result.json"
        if not result_file.exists():
            save(
                result_file,
                recover_attempt(
                    directory, job, worker_error, seconds=time.monotonic() - attempt_started
                ),
            )
        result = json.loads(result_file.read_text())
        try:
            if result["status"] == "environment_error":
                result.update(resolved=None, grading_status="environment_error")
            else:
                result.update(grade(out, directory, job, protocol))
        except Exception as exc:
            result.update(resolved=None, grading_status="environment_error", grading_error=str(exc))
        save(result_file, result)
        records.append(result)
        save(
            out / split / "results.json",
            {
                "records": records,
                "summary": summarize(records),
                "pipeline_passed": False,
            },
        )
        print(f"DONE {job['id']}: {result['status']} resolved={result['resolved']}", flush=True)
        if (
            result.get("provider_blocked")
            or result.get("usage_incomplete")
            or result.get("status") == "worker_error"
            or result["grading_status"]
            not in {
                "graded",
                "empty_patch",
            }
        ):
            raise RuntimeError("provider or evaluator unavailable; attempts and costs preserved")
    pipeline_passed = all(
        r["llm_calls"] > 0
        and r["grading_status"] in {"graded", "empty_patch"}
        and not r.get("provider_blocked")
        for r in records
    )
    pipeline_passed &= all(
        any(r["line"] == line and r["grading_status"] == "graded" for r in records)
        for line in {job["line"] for job in jobs}
    )
    save(
        out / split / "results.json",
        {
            "records": records,
            "summary": summarize(records),
            "pipeline_passed": pipeline_passed,
        },
    )


def cleanup_job(job_file):
    containers = command(
        ["docker", "ps", "-aq", "--filter", "label=yecoding.context.job=" + digest(job_file)]
    ).splitlines()
    if containers:
        subprocess.run(
            ["docker", "rm", "-f", *containers], check=True, stdout=subprocess.DEVNULL, timeout=60
        )


def recover_attempt(directory, job, error, *, seconds=0):
    """Keep received usage and mark missing accounting after a terminated worker."""
    from yecoding.types import Usage

    usage = Usage()
    calls = 0
    path = directory / "events.jsonl"
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            calls += row.get("type") == "request"
            if row.get("type") == "model.event" and row["event"].get("type") == "usage":
                usage += Usage.from_mapping(row["event"]["usage"])
            elif row.get("type") == "model.response":
                usage += Usage.from_mapping(row["response"].get("usage"))
    if not (directory / "final.patch").exists():
        (directory / "final.patch").write_text("")
    return {
        **job,
        "status": "worker_error",
        "completed": False,
        "error": error,
        "usage": usage.to_dict(),
        "llm_calls": calls,
        "seconds": seconds,
        "cost_usd": None if calls else 0,
        "usage_incomplete": bool(calls),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run", "report"])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--ablations", action="store_true")
    args = parser.parse_args()
    out = args.out.resolve()
    if args.action == "prepare":
        prepare(out)
    elif args.action == "run":
        run(out, args.split, ablations=args.ablations)
    else:
        path = out / args.split / "results.json"
        data = json.loads(path.read_text())
        data["summary"] = summarize(data["records"])
        save(path, data)
        print(json.dumps(data["summary"], indent=2))


if __name__ == "__main__":
    main()
