# 第六章数据核对与图件复现

核对日期：2026-10-20。本文是写作说明，不进入论文正文。
本批只处理已有数据，没有重新执行测试、模型请求或 Docker。

## 原始材料

- [工程验证记录](../../../eval/evidence/repair-verification.json)：160 项测试、Ruff、构建与 CLI 验证。
- [实现与镜像指纹](../../../eval/evidence/repair-implementation.json)：未提交实现与 Git 基线分别记录。
- [任务清单](../../../eval/repair_tasks.json)：2 个开发任务、8 个保留任务。
- [任务有效性](../../../eval/evidence/repair-fixtures-validated.json)：原始源码通过、全部变异基线失败。
- [真实修复结果](../../../eval/evidence/repair-heldout-live.json)：正式评测 24 次运行。
- [评估器](../../../eval/run_repair_eval.py)：固定测试 9 个方法、额外测试 4 个方法及补丁重放检查。
- [真实 CLI 演示](../../../eval/evidence/repair-cli-demo.json)：开发任务，排除在正式评测分母外。

## 补充核对事实

1. 每组 `options` 除策略外完全相同。报告使用 3 次尝试、18 次模型调用、60,000 token 阈值、
   180 秒主体时限、60 秒命令时限；产品默认的 36 次调用与 900 秒不写入本章实验配置。
2. 24 次都只有 1 条尝试记录，不能声称真实评测验证了第二轮反馈的质量收益。
3. 预算失败为 `team` 3 次、`verified` 4 次，均在调用数不足 18 次时因 token 阈值终止。
4. 6 次失败只有轮次字段，没有补丁；事件中 Coordinator 完成、Worker 已开始但未完成。
   这些运行的 `independent=null`，不能把空结果解释为额外测试未通过。
5. `trailing-literal / verified` 的候选已通过固定验收，在 Verifier 阶段触发预算失败。
   其 `attempt-1.patch` 经评估器检查后通过额外测试，流程仍记失败。
6. 实际额外检查 18 次且均通过：单角色 8 次、评审反馈 5 次、验证反馈 5 次。
   流程成功共 17 次；没有固定通过、额外失败的样本供进一步比较。
7. 各组累计 token 总量为 248,957、516,328、481,337；均值为
   31,119.625、64,541、60,167.125，正文表四舍五入为整数。
8. 平均调用次数为 5.750、9.125、9.750；耗时沿用报告主体 duration，
   不包含评估器在运行后追加的额外检查，不用于严格性能结论。

## 案例定位

| 案例 | 运行标识 | 文件 |
| --- | --- | --- |
| `none-value / single` | `fcc748e586de4741a38212e5f4941de7` | [报告](../../../eval/evidence/repair-runs/fcc748e586de4741a38212e5f4941de7/report.json)、[候选](../../../eval/evidence/repair-runs/fcc748e586de4741a38212e5f4941de7/candidate.patch) |
| `trailing-literal / verified` | `20fdde7494a7448489aea5961fa7f50d` | [报告](../../../eval/evidence/repair-runs/20fdde7494a7448489aea5961fa7f50d/report.json)、[事件](../../../eval/evidence/repair-runs/20fdde7494a7448489aea5961fa7f50d/events.jsonl)、[尝试补丁](../../../eval/evidence/repair-runs/20fdde7494a7448489aea5961fa7f50d/attempt-1.patch) |

评估器把独立检查结果加入汇总文件中的运行报告；单个运行目录的 `report.json` 是修复核心写入的版本，
不应要求其自动包含评估器后加的 `independent` 字段。两者通过运行标识关联。

## 图件与统计复现

生成脚本只读取原始汇总和逐次记录，复算后核对归档 `summary`。
输出 [统计核对 JSON](ch06-statistics.json)及图6-2的 [SVG](../figures/06-repair-comparison.svg)、
[PDF](../figures/06-repair-comparison.pdf)和 [PNG](../figures/06-repair-comparison.png)。
图中每组均为 8 次，token 平均包括失败，纵轴从零开始，无重复运行误差条。

在仓库根目录运行：

```bash
uv run --no-project --with matplotlib==3.11.2 python docs/thesis/figures/plot_repair_results.py
```

脚本使用 Fontconfig 查找 Noto Sans CJK SC，并显式注册字体以避免 Matplotlib 缓存遗漏。
当前已生成并目视核对中文图件；PDF 仅为统计图，不是 LaTeX 论文或学校模板成稿。
绘图依赖在临时环境中使用，没有修改项目依赖清单或锁文件。
