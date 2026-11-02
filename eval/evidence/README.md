# 论文实验原始证据

本目录可纳入版本管理，与被忽略的 `eval/results/` 临时输出区分。

| 文件 | 来源与用途 |
| --- | --- |
| `self-legacy-4000.json`、`self-legacy-tasks.json` | 本次推进前已有的 10 任务真实模型记录和对应任务原文；旧报告缺少完整上下文及源码快照哈希，作为历史结果留存 |
| `self-2000-retrieval.json`、`self-4000-retrieval.json` | 修正 T06 相关文件标签后的 10 任务、四策略检索复跑；没有新模型评分 |
| `dotenv-2000-retrieval.json`、`dotenv-4000-retrieval.json` | 固定上游源码上的 12 个独立任务、四策略、两档预算；没有模型评分 |
| `dotenv-4000-live.json` | 12 任务 × 四策略的 48 条真实模型回答及原始评委输出 |
| `python-dotenv-LICENSE` | 上游源码摘录及 fixture 的许可证 |
| `review-dotenv-4000/review.csv` | 隐藏策略与模型评分、打乱顺序的学生/导师复核表；空评分不是已完成人工评测 |
| `review-dotenv-4000/review-key.json` | 策略映射和原报告哈希；复核时不要查看 |
| `demo-cli.txt` | 真实 `yecoding -p` 调用 `get_context` 的终端演示输出 |
| `source-checks.json` | 对评分争议案例的实际源码行为验证，非人工评分 |

新版 JSON 记录完整检索上下文、上下文哈希、源码文件哈希、实现文件哈希、任务哈希、
预算、策略、模型配置、原始回答、评委文本及逐任务指标。运行源码包含未提交修改，Git
revision 不能单独代表该次输入；应同时查看 manifest。上游版本与 fixture 校验信息见
`../fixtures/python-dotenv-v1.1.1.json`，使用原样生产源码，未安装或执行上游 CLI。

旧版任务 T06 的 `relevant_files` 漏掉已标注依赖 `CodeIndex.ranked_symbols` 所在文件。
新版补齐该文件，因此新旧文件召回率不可直接横比；任务和实现版本也不同，不混合统计。

报告生成时间以其 UTC 字段为准。复核表对应导出时的报告哈希；若重新跑模型评测，
应另建输出目录和复核表，保留这一轮原始记录。后续正式论文另存学校要求的材料备份。

本轮独立模型运行时解压路径为 `eval/repos/python-dotenv-v1.1.1/src`，该运行完成后
已将源码移至系统临时目录，以避免它参与自建任务索引。原始报告中的运行路径保留，
源码内容和哈希未变；后续按 `eval/prepare_external.py` 的默认目录复现。
# 修复主线新增证据（2026-10-20）

- `repair-implementation.json`：Git 基线、未提交实现指纹、容器镜像 ID。
- `repair-verification.json`：本次验证命令和结果。
- `repair-fixtures-validated.json`：10 个固定外部源码人工缺陷的真实容器有效性验证。
- `repair-dev-live.json`：开发任务真实模型修复记录；不混入保留任务成绩。
- `repair-heldout-live.json`：8 个保留任务×3 策略，含额外测试、成本与失败记录。
- `repair-cli-demo.json`：真实 CLI 调用的退出码和修复报告。
- `repair-runs/`：开发/保留实验各轮补丁、事件与原始报告。

缺陷是本项目人工注入，不是历史 issue；评测使用独立上下文与相同预算，关闭跨任务 Memory。
三组都运行固定验收，不得把错误验收为零单独归因于多 Agent。完整口径见
[修复流程](../../docs/repair-workflow.md)和[实验工作稿](../../docs/thesis-experiments.md)。

---

## 实证图表补充（2026-10-26）

`visual-refresh-20261026/` 单独保存新增非模型实验，不覆盖原 24 次真实模型记录：

- `retrieval-{500,1000,2000,4000,8000}.json`：12 个固定源码理解任务 × 4 种策略 × 5 档预算，共 240 条上下文；不产生模型回答或评分。
- `fixture-validation.json`：干净源码的固定/扩展测试通过，10 个人工缺陷均产生真实测试失败，共 12 条 Docker 命令。
- `manifest.json`：命令、退出码、时间、实现/输出指纹、Docker 镜像 ID。
- 对应 `.log` 保存本次运行日志。

运行入口：`uv run python eval/run_visual_evidence.py`。每次重新运行会刷新本补充目录；历史模型归档保持不变。
角色 Token、逐任务结果及时间轨迹另从原 24 次事件重建，和每份报告总量逐一对账。
派生数据与所有图源指纹见 `docs/thesis/notes/visual-evidence-statistics.json`；不把上下文长度当成模型计费量，
不把额外角色的消耗占比解释为已隔离的因果开销，也不由本补充推断修复质量提升。

