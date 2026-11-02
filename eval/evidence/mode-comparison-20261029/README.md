# 2026-10-29 普通模式与 Repair 对照

实验方法和结果解释见 [docs/mode-comparison.md](../../../docs/mode-comparison.md)。

```bash
uv run python -m eval.run_mode_comparison --split dev --limit 1 --output-tokens 2048 \
  --out eval/evidence/mode-comparison-20261029/pilot.json
uv run python -m eval.run_mode_comparison --split heldout --output-tokens 2048 \
  --out eval/evidence/mode-comparison-20261029/heldout.json
```

输出已存在时脚本拒绝覆盖；复现请使用新的输出路径。

- `pilot.json`：开发任务试跑，不计入正式结果。
- `heldout.json`：正式 32 次运行，逐次结果与统计，含固定验收/额外测试输出。
- `pilot-runs/`、`heldout-runs/`：模式事件、容器命令、补丁及原始报告。
- `environment.json`：非敏感配置开关与内置 Prompt/Skill 指纹；记录耗时实验的环境限制。

模型为报告中记录的供应商模型，所有组重新真实调用，不使用旧实验的分数填充本次结果。
普通模式使用真实 SDK 编排和统一的容器工具环境；本报告不代表普通 CLI 完整默认配置的成绩。

事件包含模型生成文本及工具调用。没有保存模型密钥、连接配置或原始用户数据库。
模型生成的“通过”等文字不参与评分；以评测器执行结果为准。

`heldout.json` 中 `completed` 对普通模式表示发出 done 且无观测到的错误/预算拒绝，
对 Repair 表示 verified。普通模式的 done 不是所有子任务成功的保证。
`independent.passed` 表示可取得的候选通过包含额外检查在内的 13 项测试。
两者分别统计，预算耗尽后已留下正确补丁的运行只计入代码通过。
