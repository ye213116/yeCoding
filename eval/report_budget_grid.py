"""Export a completed budget grid as Markdown and CSV, without model calls."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def export(path: Path):
    data = json.loads(path.read_text())
    rows = data["results"]
    planned = data["schedule"]
    if not data.get("finished_at") or {r["id"] for r in rows} != {r["id"] for r in planned}:
        raise ValueError("grid is incomplete; final report export refused")
    if len(rows) != len({r["id"] for r in rows}):
        raise ValueError("duplicate results")
    if not all(r["usage_reconciled"] for r in rows):
        raise ValueError("model usage does not match event records")
    protocol = data["protocol"]
    lines = [
        "# 预算梯度与重复实验结果",
        "",
        f"模型：`{protocol['model']}`；单次输出：{protocol['output_tokens']:,} token；"
        f"累计预算：{', '.join(f'{n:,}' for n in protocol['budgets'])}。",
        f"修复策略：`{protocol.get('repair_strategy', 'verified (V1)')}`。",
        f"{len(protocol['task_ids'])} 个人工缺陷 × {len(protocol['modes'])} 种模式 × "
        f"{len(protocol['budgets'])} 档预算 × {protocol['repeats']} 次重复，"
        f"共 {len(rows)} 次实际运行。",
        "",
        f"时间（UTC）：{data['started_at']} — {data['finished_at']}。",
        f"实际累计 {sum(r['usage']['total_tokens'] for r in rows):,} token、"
        f"{sum(r['llm_calls'] for r in rows):,} 次模型请求。",
        "",
        "| 累计预算 | 模式 | 额外测试通过 | 正常返回且通过 | 平均 token | 平均请求数 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for tokens in protocol["budgets"]:
        for mode in protocol["modes"]:
            summary = data["summary"][f"{tokens}/{mode}"]
            n = summary["runs"]
            lines.append(
                f"| {tokens:,} | {mode} | {summary['independent_passed']}/{n} | "
                f"{summary['completed_and_passed']}/{n} | {summary['mean_tokens']:,.0f} | "
                f"{summary['mean_calls']:.2f} |"
            )
    lines += [
        "",
        "## 重复轮次与失败",
        "",
        "| 预算 | 模式 | 各轮额外通过数 | 各轮正常返回且通过数 | 终止状态 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for tokens in protocol["budgets"]:
        for mode in protocol["modes"]:
            summary = data["summary"][f"{tokens}/{mode}"]
            code = ", ".join(str(r["independent_passed"]) for r in summary["per_repeat"])
            completed = ", ".join(str(r["completed_and_passed"]) for r in summary["per_repeat"])
            states = "; ".join(f"{key}: {n}" for key, n in summary["statuses"].items())
            lines.append(f"| {tokens:,} | {mode} | {code} | {completed} | {states} |")
    lines += [
        "",
        "## 逐任务额外测试通过数",
        "",
        "| 预算 | 任务 | " + " | ".join(protocol["modes"]) + " |",
        "| --- | --- | " + " | ".join("---" for _ in protocol["modes"]) + " |",
    ]
    for tokens in protocol["budgets"]:
        for task in protocol["task_ids"]:
            cells = []
            for mode in protocol["modes"]:
                runs = [
                    r for r in rows if (r["tokens"], r["task"], r["mode"]) == (tokens, task, mode)
                ]
                cells.append(f"{sum(r['independent_passed'] for r in runs)}/{len(runs)}")
            lines.append(f"| {tokens:,} | {task} | " + " | ".join(cells) + " |")
    errors = Counter(r.get("error") for r in rows if r["status"] in {"error", "harness_error"})
    lines += [
        "",
        "## 诊断与解释边界",
        "",
        f"出现单次输出截断的运行：{sum(r['truncated_requests'] > 0 for r in rows)}。",
        f"无可评测候选的运行：{sum(not r['candidate_available'] for r in rows)}。",
        f"存在错误/评测器错误的运行：{sum(errors.values())}。",
        "",
        "额外测试通过使用原始 9 项验收加 4 项模型不可见检查。正常返回含义沿用评测协议：",
        "普通模式发出 done 且未观察到错误/预算拒绝，Repair 返回 verified；",
        "普通模式的 done 本身不保证内部每个子任务都成功。预算中断后的可用候选仍单独评分。",
        "",
        "平均消耗包含失败运行。所有条件使用相同的受限容器工具，保留各模式自己的编排。",
        f"本实验为同一项目 {len(protocol['task_ids'])} 个局部人工缺陷，"
        f"每条件重复 {protocol['repeats']} 次，不能据此推断跨项目的普遍效果。",
        "四个独立任务共享机器并发运行，耗时受资源竞争、缓存和供应商负载影响，",
        "不把耗时作为独占性能基准。温度为 0 也不保证模型输出完全一致。",
        "",
        "[原始总表](grid.json)；逐次完整结果见总表中的 result_file。",
        "",
    ]
    report = path.parent / "report.md"
    report.write_text("\n".join(lines))
    fields = [
        "id",
        "tokens",
        "repeat",
        "task",
        "mode",
        "status",
        "completed",
        "candidate_available",
        "acceptance_passed",
        "independent_passed",
        "completed_and_passed",
        "total_tokens",
        "llm_calls",
        "duration",
        "truncated_requests",
        "model_errors",
        "result_file",
    ]
    with (path.parent / "results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            values = {**row, "total_tokens": row["usage"]["total_tokens"]}
            writer.writerow({key: values[key] for key in fields})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(export(args.path))


if __name__ == "__main__":
    main()
