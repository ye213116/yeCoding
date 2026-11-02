# 写作事实与证据映射

本文件用于核对正文，不属于论文正文。核对日期：2026-10-20。

## 实现基线

实际仓库为 `/home/zyh/projects/yeCoding`。Git 基线为 `main` 分支的
`b90335dbe1e739b2092c846aec59983bfa15ce04`。新增实现尚未提交，完整对应关系以
[实现指纹](../../eval/evidence/repair-implementation.json)为准。
本批核对了该文件列出的所有 SHA256，与当前文件一致；没有把旧执行记录表述为本批重新运行的结果。

## 首批正文事实

| 正文主张 | 可核对证据 | 写作边界 |
| --- | --- | --- |
| 基于已有终端 Agent 扩展修复流程 | `src/yecoding/agent/query.py`、`query_engine.py`、`repair.py` | 不声称本轮从零实现全部 Agent 基础设施 |
| 三个独立上下文、顺序交接 | `agent/repair.py` 中 `_agent`、`run` | 不是并行 Worker 写入或补丁合并 |
| 固定验收命令和补丁交付 | `agent/repair.py`、`sandbox/workspace.py` | 测试通过不等于任意输入正确；补丁不自动应用 |
| 受限容器执行 | `sandbox/docker.py` | 不等于虚拟机隔离；当前实验使用普通宿主用户 UID |
| Skill 和 Memory 接入 | `agent/repair.py` 中 `_agent`、`_recall`、`_remember` | 有功能验证，没有单独质量提升结论 |
| 160 项自动化测试通过 | [验证记录](../../eval/evidence/repair-verification.json) | 包含 134 项既有基线，不称全部为新增测试 |
| 10 个任务、2 个开发、8 个评测 | [任务定义](../../eval/repair_tasks.json)、[有效性验证](../../eval/evidence/repair-fixtures-validated.json) | 同一上游仓库的人工缺陷，非历史 issue |
| 8 个任务、3 组、24 次真实运行 | [保留任务记录](../../eval/evidence/repair-heldout-live.json) | 不计开发任务；每个条件只执行一次 |
| 成功数 8、5、4 | 同上 `summary.*.verified` | 指流程验收成功，不与额外测试通过数混用 |
| 额外测试通过数 8、5、5 | 同上 `summary.*.independently_passed` | 有一个预算失败候选通过额外测试 |
| 三组错误验收均为 0 | 同上 `summary.*.false_acceptances` | 样本有限；三组均有固定验收，不能归因于增加验证角色 |
| 多角色失败全部为预算耗尽 | 同上各运行 `status` | team 3 次、verified 4 次，不泛化为其他任务的失败分布 |

## 写作时需要区分的两套实验

修复实验使用真实容器测试、真实模型调用和额外测试作为判据，正文第6章以此为主。
旧检索实验比较上下文长度、符号召回、源码覆盖和模型评分，分母、指标及评委均不同。
不能将旧检索实验的符号召回收益当作新增修复流程的成功率收益，也不能将模型评分当作真实测试结果。

## 第二章技术表述核对

| 技术表述 | 核对位置 | 限定范围 |
| --- | --- | --- |
| 工具调用重组、调用标识与结果关联 | `agent/query.py`、`tools/base.py` | 参数描述不等于完整 JSON Schema 校验或权限保证 |
| 相邻、声明并发安全的只读调用可并发 | `tools/executor.py` | 不等于任意工具、写入或修复角色都能并行 |
| 上下文估算与模型返回 usage 分别使用 | `context/manager.py`、`agent/query.py` | 不把字符启发式估算当作供应商精确计费 |
| AST 静态关系、词面检索与优先级组装 | `rag/parser.py`、`code_index.py`、`context_builder.py` | 无 embedding；关系为近似；符号命中不等于函数源码完整覆盖 |
| 通用技能按需加载，修复角色预先选择技能 | `skill/registry.py`、`agent/query.py`、`agent/repair.py` | 不能写成每个修复角色都开放任意技能写入工具 |
| 缓冲区消费后不重复追加，内容进入消息历史 | `skill/registry.py`、`agent/query.py` | 不能把一次注入表述为后续请求完全不再包含技能内容 |
| 项目作用域、TTL、词面相关性与元数据排序 | `memory/manager.py`、`agent/repair.py` | 非向量记忆；置信度属性不是校准概率；源码指纹不覆盖全部环境变化 |
| 容器约束、挂载与宿主文件工具边界分别管理 | `sandbox/docker.py`、`sandbox/workspace.py`、`agent/repair.py` | 容器约束属于 repair 路径；普通宿主用户 UID 运行不是任意部署均非 root 的保证 |

本章使用的文献与 Docker 文档元数据沿用已完成的原始来源核验；没有为新增章节编造发表年份或页码。

## 第三章需求追溯

第三章已建立以下需求与实现的对应关系。表中测试均是已有代码与归档验证的来源，
本批写作只读核对，没有重新执行测试或模型实验。

| 第三章需求 | 对应位置 | 已有核对线索 |
| --- | --- | --- |
| FR-01、FR-02：工具与定位 | `tools/base.py`、`tools/executor.py`、`rag/`、`agent/query.py` | 工具顺序/并发及 AST/上下文测试 |
| FR-03：公开入口一致性 | `entrypoints/cli.py`、`entrypoints/repl.py`、`agent/query_engine.py`、`runtime/api.py` | CLI 预算配置、SDK 工作流、Runtime 失败事件测试 |
| FR-04：初始状态和基线 | `agent/repair.py`、`sandbox/workspace.py` | 无验收命令、基线已通过、镜像缺失测试 |
| FR-05、FR-06：角色与验收 | `agent/repair.py` 的 `_agent`、`_registry`、`_tests` | Reviewer 不能覆盖真实失败、固定文件篡改拒绝测试 |
| FR-07、FR-08：停止与交付 | `agent/repair.py`、`sandbox/docker.py`、`sandbox/workspace.py` | 有限重试、无进展、预算、补丁重放、超时/取消清理测试 |
| FR-09、FR-10：Skill 和 Memory | `skill/registry.py`、`memory/manager.py`、`agent/repair.py` | 角色技能记录、经验写入、过期源码指纹过滤及关闭记忆测试 |
| NFR-01—NFR-05：边界与集成 | 同上及 `runtime/tasks.py` | 路径/文件类型、只读挂载、宿主环境不透传、输出截断、取消后拒绝迟到完成测试 |
| NFR-06：评估口径 | `eval/run_repair_eval.py`、归档修复实验 | 开发/保留划分、独立测试、失败纳入平均消耗 |

第三章的当前范围不包含任意验收脚本保护、所有输入的秘密识别、瞬时取消或精确 token 硬上限。
验收场景是需求追溯结构，不替代后续第6章的实际测试与结果报告。

## 第四章设计追溯

第四章的分层是对现有 Python 模块的逻辑组织，不代表分别部署的服务。
本批读取代码核对设计，不新增业务功能，也不将概念执行阶段写成不存在的持久化枚举。

| 设计内容 | 核对位置 | 关键边界 |
| --- | --- | --- |
| 分层、共用查询循环和独立修复编排 | `agent/query.py`、`agent/query_engine.py`、`agent/repair.py` | CLI 直接构造 `VerifiedRepair`；其他修复入口经 `QueryEngine` |
| 角色工具和顺序交接 | `agent/repair.py` 中 `run`、`_agent`、`_registry` | 同一模型客户端；各调用历史独立；只有 Worker 写业务文件；非并行补丁合并 |
| 固定执行判据与策略差异 | `agent/repair.py` 中 `run`、`_tests` | 三组都有固定验收；Reviewer 文字不是最终布尔判据；测试通过后仍可能因后续调用预算失败而未交付 |
| 初始快照、双副本和候选生成 | `sandbox/workspace.py` | 初始文件映射在内存；`work` 可写、`verify` 从候选文件重建；并非 Git worktree 或逐轮应用补丁 |
| 单命令容器及宿主职责 | `sandbox/docker.py`、`agent/repair.py` 中 `_registry` | 每条命令新容器；文件工具和模型通信仍在宿主；无命令执行的宿主回退 |
| 数据对象、终止状态和证据文件 | `agent/repair.py`、`sandbox/docker.py` | 报告为字典；`invalid_patch` 是尝试分类；不承诺强制退出后的完整报告或模型消息重放 |
| Skill 与 Memory 生命周期 | `agent/repair.py` 中 `_agent`、`_recall`、`_remember` | 角色预选技能；原项目作用域、入口一次召回；成功才保存经验；关闭时跳过读写 |
| 接口与取消适配 | `entrypoints/cli.py`、`entrypoints/repl.py`、`agent/query_engine.py`、`runtime/api.py`、`runtime/tasks.py` | SDK 报告需检查状态；Runtime 非成功转错误；队列任务 ID 与修复运行 ID 不同；取消不保证瞬时中断模型 |

第四章包含 4.1—4.8 节、3 张图和 5 张表。全部设计基于当前实现边界，
算法细节和测试数据分别留给第5章与第6章。实现指纹沿用本文件记录的未提交工作区基线。

## 第五章实现追溯

第五章依据当前代码展开算法与参数，不新增模型实验。伪代码省略事件展示及外层异常处理，
保持候选拒绝、测试、验证角色、成功判断和反馈更新的实际先后关系。

| 实现内容 | 核对位置 | 关键事实 |
| --- | --- | --- |
| 流式工具循环与顺序语义 | `agent/query.py`、`tools/base.py`、`tools/executor.py` | 按调用序号合并增量，按 ID 回填；连续安全读取并发，写入前等待；非完整 Schema 校验 |
| 受限注册表 | `agent/repair.py` 中 `_registry` | 选择已有工具；文件操作增加检查；命令处理器替换为 Docker；审批配置只作用于副本 |
| 索引与预算化代码上下文 | `agent/repair.py` 中 `_agent`、`rag/context_builder.py` | 每次角色前可重建；签名、直接关系、源码、摘要按优先级装配；默认 8 个符号、排名前 3 个至多各 40 行 |
| 算法5-1与来源指纹公式 | `sandbox/workspace.py` 中 `inventory`、`fingerprint`、`candidate` | 路径排序后以零字节分隔并拼接原始内容摘要；文件比较与补丁生成；候选映射重建验收副本 |
| 容器约束及生命周期 | `sandbox/docker.py` | 每条命令独立容器；双通道持续读取，各保留 20,000 字节；命名删除、屏蔽取消和输出任务回收 |
| 算法5-2与验收判据 | `agent/repair.py` 中 `run`、`_tests`、`_agent` | 固定命令顺序执行；先测试再验证角色，后判断交付；Worker 8 轮，其他角色 3 轮；不是投票通过 |
| 表5-3默认预算 | `config.py` 中 `RepairConfig`、`agent/repair.py` 中 `BudgetClient` | 3 次尝试、36 次调用、60,000 token 阈值、总 900 秒、命令 60 秒；实验配置另行说明 |
| Skill 与 Memory | `skill/registry.py`、`memory/manager.py`、`agent/repair.py` | 技能消费不代表从历史移除；仅修复类记忆额外验源码指纹；修复经验 30 天、置信度属性 0.7 |
| 公开入口与证据 | `entrypoints/cli.py`、`agent/query_engine.py`、`runtime/api.py`、`agent/repair.py` | 参数只显式覆盖；SDK 返回需检查状态；Runtime 失败转错误；报告非崩溃恢复或完整模型重放 |

本章包含 5.1—5.7 节、1 张图、4 张表、2 段算法及 2 处显示公式。
已与当前实现参数及指纹核对；验证范围为论文内容和实现事实，未重新执行自动化测试。

## 第六章测试与实验核对

本章使用已归档执行记录，统计脚本仅读取数据并生成论文图件，不执行模型或 Docker。
补充核对见 [第六章数据说明](notes/ch06-audit.md)，机器可读汇总见
[复算记录](notes/ch06-statistics.json)。

| 正文内容 | 核对来源 | 本批确认 |
| --- | --- | --- |
| 工程验证 | `eval/evidence/repair-verification.json`、`tests/test_repair.py` | 归档 160 passed；既有 134、修复新增 25、快照回归新增 1；模型夹具与真实 Docker 区分 |
| 正式任务与环境 | `eval/repair_tasks.json`、`eval/evidence/repair-implementation.json`、逐次 `options` | 2 个开发、8 个保留；3 策略各一次；18 次调用、180 秒为实验配置，非产品默认 |
| 基线有效性 | `eval/evidence/repair-fixtures-validated.json` | 未变异源码通过，10 个变异任务均为真实测试失败 |
| 固定与额外测试 | `eval/run_repair_eval.py` 的 `ACCEPTANCE`、`INDEPENDENT` 及评估流程 | 固定 9 个方法，额外 4 个；额外文件在模型结束后加入独立目录 |
| 汇总与消耗 | `eval/evidence/repair-heldout-live.json` 的 24 次记录 | 成功 8、5、4；额外通过 8、5、5；均值包含失败；次数均值为 5.750、9.125、9.750 |
| 额外检查分母 | 同上 `independent`、补丁文件 | 实际执行 18 次且全通过；其余 6 次无补丁未检查，不能称为额外测试失败 |
| 首轮与失败阶段 | 各运行 `attempts` 及 `events.jsonl` | 24 次都只建立 1 轮；6 次 Worker 交接前预算终止，1 次测试通过后 Verifier 阶段预算终止 |
| 成功及失败案例 | `fcc748e586de4741a38212e5f4941de7`、`20fdde7494a7448489aea5961fa7f50d` 的报告、事件与补丁 | `none-value` 局部修复；`trailing-literal` 候选通过但流程预算失败；状态保持原值 |
| 图6-2 | `figures/plot_repair_results.py` 与 `notes/ch06-statistics.json` | 原始记录复算并比对归档 summary；中文图件已预览，SVG/PDF 可用于排版 |

本章不把单次小样本结果写成多智能体普遍无效，也不将各组零错误验收归因于验证角色。
Skill 全开、Memory 全关且没有独立消融；早期检索实验不混入修复实验指标。

## 第七章与全稿结论核对

第七章以绪论 1.3.2 的三个研究问题组织结论：通用能力与执行边界、
执行证据与角色交接、统一预算下的策略表现。工程总结对应第4—5章，
经验结论对应第6章，不新增未经实验验证的准确率或安全结论。

- 三组成功数保持 8、5、4；额外通过保持 8、5、5；7 次失败为 token 预算触发。
- 24 次只建立一轮尝试；重试可运行来自功能测试，不表述为真实模型多轮增益。
- 同步修订中英文摘要结尾，分别注明功能测试与修复实验的结论来源。
- Skill 与 Memory 仅有功能验证；动态角色、并行候选及预算分配等均写为后续研究。
- 中英文摘要与七章正文均已起草；一致性记录见 [全稿核对](notes/manuscript-audit.md)。

## 全稿整合时持续复核

- 第6章已明确三组策略都包含固定验收；后续摘要和图表说明继续保持 `team` 的反馈消融含义。
- token 阈值在下一次请求前检查，最终 usage 可以超过 60,000，不能称为严格的最终总量上限。
- 耗时记录期间存在同机回归负载，不用于严格性能结论。
- 自动保存经验只说明候选通过指定验收，不说明原仓库已经应用补丁。
- 学校模板、篇幅、图表格式和参考文献样式未提供，LaTeX 阶段再适配，不推测具体校规。

## LaTeX 成稿与原始正文对应

2026-10-23：以本目录 9 个摘要及章节 Markdown 文件生成 `latex/chapters/`，
在 `latex/build/build-report.json` 保存正文 SHA256、工具版本、图表计数与 PDF SHA256。
`latex/build/pdf-audit.json` 保存交叉引用、文献、页面边界、实现指纹和实验来源摘要核对结果。
排版仅调整图的方向、标签、字号与图件字体格式，原始结果和论文结论不变。
正文继续从 Markdown 修改后生成，禁止只改生成章节而造成两份稿件内容不同。
本次没有重跑归档 160 项测试、真实模型或 Docker；详细范围见 [编译核对](notes/latex-build-audit.md)。
