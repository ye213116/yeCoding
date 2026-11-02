# VerifiedRepair V2 与 ReAct：大预算对照

2026-10-29，使用当时未提交的 V2 实现重新运行。旧 V1 预算实验保持停止，未续填或覆盖。
2026-10-30 已放弃 V2 产品改动并恢复已提交基线；本报告及原始数据保留为历史记录，
不代表当前产品行为，也不是上下文管理方法的效果证据。后续直接在原论文与报告文件修改。

本轮两组均为 8/8 通过固定验收及额外测试，V2 默认 Single 的平均累计 token 比普通 ReAct
减少 56.5%。这说明本轮配置有资源效率收益，尚未显示成功率提升，也不是多角色协作的收益证明。

## 条件

- 模型：DeepSeek `deepseek-v4-flash`，temperature=0。
- 两组：公开 SDK 普通 ReAct 与 `repair(strategy="single")`。
- 任务：固定 python-dotenv v1.1.1 上的 8 个保留评测人工缺陷，每条件运行一次，共 16 次。
- 每任务累计预算 240,000 token，单次输出上限 8,192；最多 64 次请求、900 秒。
- V2 最多 3 轮候选，每轮 Worker 最多 8 次请求；普通 ReAct 保留默认最多 20 轮工具循环。
  这是现有公开模式整体配置的比较，没有强制两种循环使用完全相同的 Prompt 或轮次上限。
- 同样的受限文件工具、Docker 命令环境与测试保护；关闭 Memory、MCP、自定义 Prompt；
  保留已启用的 Skill、代码索引、上下文压缩。V2 仍按角色加载修复 Skill，没有做组件消融。
- 原始固定验收 9 项，模型运行结束后在独立副本加入 4 项额外检查。额外检查不向 Agent 提供。
- 运行前实际确认干净源码通过两套测试、每个注入缺陷产生失败。
- 固定随机种子 20261029 打乱排程，4 个隔离任务并发；各组共享相同模型及容器镜像指纹。

## 结果

| 指标 | 普通 ReAct | V2 Single + Workflow |
| --- | --- | --- |
| 固定验收通过 | 8/8 | 8/8 |
| 固定验收及额外测试通过 | 8/8 | 8/8 |
| 正常完成且通过额外测试 | 8/8 | 8/8 |
| 平均累计 token | 71,691 | 31,162 |
| 累计 token 中位数 | 64,544 | 27,003 |
| 平均模型请求数 | 7.75 | 5.50 |
| 平均任务耗时（共享主机并发） | 17.62 秒 | 15.18 秒 |

V2 平均累计 token 减少 56.5%，中位数减少 58.2%，平均模型请求数减少 29.0%。
7/8 个配对任务的 V2 token 更少；`override-environment` 略多。V2 的 8 个任务均在第一轮
候选通过，没有依赖重试，未调用 Coordinator/Reviewer。两组均未出现模型错误、输出截断、
预算耗尽或超时。全轮共 106 次模型请求、822,825 token。

| 任务 | ReAct token | V2 token | ReAct 请求数 | V2 请求数 |
| --- | --- | --- | --- | --- |
| none-value | 48,995 | 21,678 | 7 | 5 |
| trailing-literal | 59,996 | 58,250 | 7 | 7 |
| variable-cursor | 80,527 | 28,580 | 10 | 6 |
| unquoted-whitespace | 170,442 | 18,932 | 8 | 4 |
| escape-decoding | 69,092 | 25,129 | 9 | 5 |
| line-tracking | 71,233 | 34,774 | 8 | 6 |
| override-environment | 36,154 | 36,525 | 6 | 6 |
| disable-interpolation | 37,092 | 25,426 | 7 | 5 |

## 如何解释

当前 V2 在这批任务上保留了隔离验收、补丁和证据交付，同时达到与 ReAct 相同的通过数，
实际模型用量更低，支持继续保留默认 Single。24 万是每任务可用上限，实际消耗均低于上限；
本轮没有预算失败，因此没有把预算不足当成修复能力不足。

该结果不意味着任意项目都能节省 56.5%。只有一个项目、8 个局部人工缺陷、每条件一次，
普通 ReAct 本轮平均用量也高于旧 V1 实验中的 ReAct，因此不能将 V1/V2 的跨轮差异都归因于
架构调整。两组通过率均已达到本任务集上限，需要更难的真实问题和重复运行才能比较修复能力。
本轮没有评估规划和审查策略，也没有实测重试带来的增益。

token 是模型返回的累计输入与输出用量，包含重复上下文和缓存命中输入，不能直接解释为费用；
四个任务共享主机，耗时仅作描述，不作为独占性能结论。固定测试与额外检查仍然是有限覆盖，
通过不代表补丁普遍正确。这里的 ReAct 也仅使用统一受限工具环境，不能直接等同完整默认 CLI 体验。

## 复现和证据

```bash
uv run python -m eval.run_budget_grid \
  --budgets 240000 --repeats 1 --modes react repair --repair-strategy single \
  --output-tokens 8192 --calls 64 --timeout 900 --concurrency 4 \
  --out eval/evidence/repair-v2-high-budget-20261029

uv run python -m eval.report_budget_grid \
  eval/evidence/repair-v2-high-budget-20261029/grid.json
```

已有目录不会被覆盖，重新执行须选择新目录；保持实现与协议一致时可使用 `--resume`。
基线 HEAD 为 `7a1783bc723d358090a3c9f318d7bf795903138e`，V2 是未提交改动，不能只用
该 HEAD 复现；实际源码、Prompt、Skill、评测器和 fixture 已归档在同目录 `implementation.zip`。

- [原始总表、排程、条件及源码 SHA256](../eval/evidence/repair-v2-high-budget-20261029/grid.json)
- [自动生成的汇总](../eval/evidence/repair-v2-high-budget-20261029/report.md)
- [逐次结果 CSV](../eval/evidence/repair-v2-high-budget-20261029/results.csv)
- [证据一致性核验](../eval/evidence/repair-v2-high-budget-20261029/verification.json)

逐次模型事件、补丁及外部测试输出在 `runs/`，V2 自身的阶段用量、测试证据和 Trace 在
`repair-runs/`。本轮已经完整结束，无需继续派发模型调用。
