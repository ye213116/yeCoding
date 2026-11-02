# 实证图表修订：从框图叙述转向可核查证据

日期：2026-10-26（Asia/Shanghai）。分支 `main`，HEAD `b90335dbe1e739b2092c846aec59983bfa15ce04`。
实现和论文仍在未提交工作区；Git HEAD 不能单独标识本次分析输入，实际输入指纹另存于统计文件。

本次直接修改英文论文生成源、生成的 TeX、PDF 和源码包。不修改业务实现，不提交或推送 Git。
保留一张总体架构图，删去重复的顺序交接、工作区及评估流程框图，加入六张实证/案例图及其分析。

## 六张图各自回答的问题

| 位置 | 图与预览 | 回答的问题 | 证据与限制 |
| --- | --- | --- | --- |
| 图 5.1 | [预算敏感性双曲线](../figures/05-context-budget-en.png) | 增加上下文预算，定位和代码覆盖是否同步增加？ | 本次 240 条确定性检索；不是模型回答质量或修复成功率 |
| 图 5.2 | [真实补丁与测试证据](../figures/06-concrete-patch-en.png) | 系统实际改了什么、依据什么验收？ | 归档 single 路径 none-value；9 项固定测试包含在扩展的 13 项中 |
| 图 6.1 | [逐任务结果矩阵](../figures/06-task-outcomes-en.png) | 哪些任务完成、哪些没有候选、哪些有正确候选却没完成流程？ | 保留全部 24 次运行与逐格消耗，不把未检查标成测试失败 |
| 图 6.2 | [配对 Token 成本](../figures/06-paired-token-cost-en.png) | 同一任务采用不同策略时，消耗如何变化？ | 逐任务配对；不是重复测量或显著性分析 |
| 图 6.3 | [角色消耗分解](../figures/06-role-token-allocation-en.png) | 多角色的消耗实际分布在哪里？ | 从 usage 事件归属角色，逐份对齐 24 份报告总量；不是因果消融 |
| 图 6.4 | [真实运行轨迹](../figures/06-real-execution-traces-en.png) | 为什么测试已通过的候选，工作流仍然会失败？ | 两次 verified 策略归档事件；测试标记是测试之后的 Verifier 入口，不冒充精确测试完成时间 |

[六图总览](../figures/visual-evidence-overview.png)。图表均提供 SVG、PDF 和 PNG，论文导入矢量 PDF。
图 5.2 前移至实现章节，避免前半论文只有抽象框架；第 6、7 章补充结果解释与局限，不只插入图片。

## 本次真正补跑的内容

```bash
uv run python eval/run_visual_evidence.py
```

- 固定 python-dotenv v1.1.1 生产源码，12 个已标注理解任务。
- 四种策略：grep、whole-file、AST + relations、AST without relations。
- 五档估算 Token 预算：500、1,000、2,000、4,000、8,000，共 240 条上下文。
- Docker 校验 12 条命令：干净源码的固定/扩展测试均通过，10 个注入缺陷均产生 genuine test failure。
- 镜像 ID 与归档一致：`sha256:e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce`。
- 当前材料使用该次补充目录的最终生成记录；构建调试期间重跑同一确定性流程不扩大任务样本数。
- **没有新增模型调用。** 原 24 次真实模型记录和 160 项历史工程测试不冒充本次重新执行。

原始 JSON、日志、命令、时间、退出码和指纹：`eval/evidence/visual-refresh-20261026/`。
归档模型记录仍位于 `eval/evidence/repair-heldout-live.json` 和 `repair-runs/`。

## 新增的可支持结论

1. 在 4k 预算下，AST + relations 平均约 1,243 个估算 Token，定位召回 88.3%；whole-file 约 3,617 个，召回 85.4%。这是上下文长度差异，不是模型账单降低 65.6%。
2. AST 的符号体代码覆盖只有 56.0%，低于 whole-file 的 85.4%。超过 2k 的平台期提示选取上限限制覆盖；8k 时 whole-file 召回达到 93.8%，不能宣传 AST 在所有预算都领先。
3. 去除关系后，4k AST 召回降至 64.4%；关系有定位价值，但不能由此推断修复率增益。
4. 协调 + 审查占 team 与 verified 累计 Token 的 56.3% / 47.7%。输入包括重复提示词和工具历史，不能把这些数字当成唯一源码量或隔离出的因果开销。
5. trailing-literal 的修改角色在 14.50 秒结束，16.37 秒进入审查；候选已通过固定测试，但审查未完成而触发预算停止。真实轨迹把“候选行为正确”和“工作流完成”分开。

仍未提供新仓库真实 issue、多次重复模型运行、Skill/Memory 独立质量消融或多角色更优的证据；本次不作这些宣称。

## 构建与检查

```bash
uv run --no-project --with matplotlib==3.11.2 python docs/thesis/figures/plot_evidence_figures.py
uv run --no-project --with pypandoc_binary==1.17 --with pymupdf==2.0.0 python docs/thesis/latex/build.py
uv run --no-project --with pymupdf==2.0.0 python docs/thesis/latex/audit.py
```

派生数据、24 份角色 usage 对账、图表输入指纹：`visual-evidence-statistics.json`。
当前页数、字数、图表数、版式、引用与缺字检查以 `latex/build/pdf-audit.json` 为准。

最终测量：全文 46 个物理页；Introduction 至 References 前为 34 页，按目录后至参考文献前的保守口径为 **36 页**，满足 BEng 30–40 页要求。正文机器提取 8,480 词，含图表目录的保守区间 8,631 词，词数仅作信息项。

保留 7 图（1 架构 + 6 实证/案例）、16 表、2 算法、5 公式、22 篇学术引用。编译与自动核对通过：无缺字、越界、空白页、溢出盒、未定义引用或重复标签；17 个实现指纹、7 个实际导入图件和 24 份角色用量对账通过。四个涉及的 Python 脚本 Ruff 与格式检查通过，`git diff --check` 通过。

全部 46 页已渲染为两张总览检查，实证图及实现/案例整页已检查。检查图在 `latex/build/visual-review-final/`，图页索引列出实际物理页；图 5.1 / 5.2 位于物理页 23 / 24，图 6.1–6.4 位于 31–34。补丁图与时间轨迹的图注、字号和边界可读。保留第三方 `lineno.sty` 编码通知与导入 PDF accessibility tags 的编译器提示，不据此宣称无工具警告或 PDF 无障碍合规。

源码包 57 项，CRC 与逐项本地内容一致性检查通过；只打包实际使用的 Mermaid 源图，避免同名旧框图混入实证 SVG/PDF。

- PDF SHA256：`f237d0bb089fc07160c9c74652d6914ea6f93a646a16c10f9437e5fb95b607a9`。
- 源码包 SHA256：`32a66bd8d8b759d6a68caf7f1de43e6e798173b25f8c67ab78c1ef0ac5f12515`。
