# 论文首批原始文献核验笔记

核验日期：2026-10-20。用途：为摘要、绪论及后续相关技术章节提供引用依据；本文件是写作工作笔记，不直接并入论文正文。

选版原则：已有正式出版版本的论文采用正式年份及该版本书目信息。arXiv 用于核对原始摘要和版本历史，不将预印本年份、作者表或 DOI 混入正式版条目。引用键在 Markdown 和后续 LaTeX 中保持一致。本文的贡献范围是系统设计、实现、独立测试验收和证据记录，不是基础模型训练，也不预设多智能体普遍优于单智能体。

## 1. ReAct

- 引用键：`yao2023react`。
- 作者：Shunyu Yao, Jeffrey Zhao, Dian Yu, et al.
- 题名：ReAct: Synergizing Reasoning and Acting in Language Models。
- 正式出版：The Eleventh International Conference on Learning Representations（ICLR），2023。
- 正式原文：[ICLR 2023 PDF](https://openreview.net/pdf?id=WE_vluYUL-X)；正式入口：[OpenReview](https://openreview.net/forum?id=WE_vluYUL-X)。
- 版本辅助：[arXiv:2210.03629](https://arxiv.org/abs/2210.03629)，首发 2022 年，v3 注明是 ICLR camera-ready 版本。`10.48550/arXiv.2210.03629` 是预印本 DOI，不应写成 ICLR 出版 DOI。
- 可支持的观点：模型可以交替产生推理、执行动作并利用外部环境返回的信息，作为本系统工具调用循环的相关工作依据。[原始摘要与版本说明](https://arxiv.org/abs/2210.03629)
- 不能据此声称：ReAct 已证明本系统的代码修复成功率、实现安全性，或证明角色拆分一定有效。原论文主要任务与本项目评测不同。
- 核验状态：原论文搜索结果返回了含会议身份、标题、作者和摘要的第一页；直接打开 OpenReview 时遇到浏览器验证。arXiv 页面与作者项目页可直接读取，没有用二手博客补足出版信息。

## 2. SWE-agent

- 引用键：`yang2024sweagent`。
- 作者：John Yang, Carlos E. Jimenez, Alexander Wettig, et al.
- 题名：SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering。
- 正式出版：Advances in Neural Information Processing Systems，37（NeurIPS 2024）。
- 出版页面：[NeurIPS 官方论文页](https://proceedings.neurips.cc/paper_files/paper/2024/hash/5a7c947568c1b1328ccc5230172e1e7c-Abstract-Conference.html)。
- 官方页列出的 DOI：[10.52202/079017-1601](https://doi.org/10.52202/079017-1601)。
- 版本辅助：[arXiv:2405.15793](https://arxiv.org/abs/2405.15793)，首发 2024 年。
- 可支持的观点：面向 Agent 设计的交互接口涵盖仓库导航、代码编辑、测试执行；接口设计是软件工程 Agent 的重要组成部分。[正式论文摘要](https://proceedings.neurips.cc/paper_files/paper/2024/hash/5a7c947568c1b1328ccc5230172e1e7c-Abstract-Conference.html)
- 不能据此声称：本文复现了 SWE-agent 或达到其基准成绩；其测试结果也不能作为本系统多智能体、Skill 或 Memory 有效性的证据。原论文所报成绩属于当时设置，不是当前排行榜。
- 核验状态：正式出版页直接读取成功，题名、作者、会议卷号、年份及 DOI 均来自该页；未填写未经核验的页码。

## 3. SWE-bench

- 引用键：`jimenez2024swebench`。
- 作者：Carlos E. Jimenez, John Yang, Alexander Wettig, et al.
- 题名：SWE-bench: Can Language Models Resolve Real-World GitHub Issues?。
- 正式出版：The Twelfth International Conference on Learning Representations（ICLR），2024。
- 正式入口：[OpenReview](https://openreview.net/forum?id=VTF8yNQM66)。
- 出版身份与标准书目：[项目官方 Citations](https://www.swebench.com/citations)。
- 版本辅助：[arXiv:2310.06770](https://arxiv.org/abs/2310.06770)，首发 2023 年；预印本 DOI 为 `10.48550/arXiv.2310.06770`，与正式年份分开记录。
- 可支持的观点：仓库级问题解决需要根据问题描述修改代码，常涉及跨函数或跨文件理解；可将仓库、问题、补丁和可执行评测作为任务组织的相关工作背景。[原论文摘要](https://arxiv.org/abs/2310.06770)
- 不能据此声称：本项目的人工注入缺陷任务属于 SWE-bench、是其子集，或其成功率可与该基准直接比较。使用相似评测思路不等于实际运行该数据集。
- 核验状态：arXiv 原始信息与项目官方引用页已读取；OpenReview 直接访问触发浏览器验证。正式年份由项目官方书目确认，未填写正式出版 DOI 或页码。

## 4. AutoGen

- 引用键：`wu2024autogen`。
- 作者：Qingyun Wu, Gagan Bansal, Jieyu Zhang, et al.
- 正式题名：AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversations。
- 正式出版：First Conference on Language Modeling（COLM），2024。
- 正式原文：[COLM 2024 PDF](https://openreview.net/pdf?id=BAakY1hNKS)；正式入口：[OpenReview](https://openreview.net/forum?id=BAakY1hNKS)。
- 发表方辅助：[Microsoft Research 论文页](https://www.microsoft.com/en-us/research/publication/autogen-enabling-next-gen-llm-applications-via-multi-agent-conversation-framework/)。该页明确标注 COLM 2024，但题名写为单数 Conversation；本文跟随正式论文第一页使用复数 Conversations。
- 版本辅助：[arXiv:2308.08155](https://arxiv.org/abs/2308.08155)，首发 2023 年；它的题名为单数 Conversation，不直接复制为正式版题名。
- 可支持的观点：可通过可配置角色、对话规则和工具构建多智能体应用，作为本系统角色分工与交互编排的相关工作背景。[COLM 原文](https://openreview.net/pdf?id=BAakY1hNKS)
- 不能据此声称：多智能体在相同预算下普遍超过单智能体，或者 AutoGen 的案例结果能替代本项目的对比实验。
- 核验状态：原始 PDF 的搜索结果已返回标题、作者和 COLM 2024 身份；直接打开 OpenReview 会触发验证。官方研究机构论文页可读取。书目采用前三位作者加 et al.，避免混合不同版本作者表；不虚构 DOI 或页码。

## 5. Reflexion

- 引用键：`shinn2023reflexion`。
- 正式版作者：Noah Shinn, Federico Cassano, Ashwin Gopinath, Karthik Narasimhan, Shunyu Yao。
- 题名：Reflexion: Language Agents with Verbal Reinforcement Learning。
- 正式出版：Advances in Neural Information Processing Systems，36（NeurIPS 2023）。
- 出版页面：[NeurIPS 官方论文页](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html)。
- 官方页列出的 DOI：[10.52202/075280-0377](https://doi.org/10.52202/075280-0377)。
- 版本辅助：[arXiv:2303.11366](https://arxiv.org/abs/2303.11366)，2023 年。其 v4 作者表含 Edward Berman，不能与上述五位作者的正式书目混用。
- 可支持的观点：任务反馈可转换为文本反思并保存在情节记忆中，用于后续尝试；该机制不要求更新模型权重。[正式论文摘要](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html)
- 不能据此声称：本项目的 SQLite 经验存储实现就是 Reflexion，或单纯保存测试结果便等价于强化学习训练；其函数级编码实验不能直接证明仓库级修复效果。
- 核验状态：正式出版页读取成功，采用其五位作者版本；未填写未核验页码。

## 6. RepoCoder

- 引用键：`zhang2023repocoder`。
- 作者：Fengji Zhang, Bei Chen, Yue Zhang, et al.
- 题名：RepoCoder: Repository-Level Code Completion Through Iterative Retrieval and Generation。
- 正式出版：Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing，2023：2471–2484。出版者为 Association for Computational Linguistics。
- 正式页面：[ACL Anthology](https://aclanthology.org/2023.emnlp-main.151/)；DOI：[10.18653/v1/2023.emnlp-main.151](https://doi.org/10.18653/v1/2023.emnlp-main.151)。
- 版本辅助：[arXiv:2303.12570](https://arxiv.org/abs/2303.12570)，2023 年。
- 可支持的观点：仓库相关信息分散在不同文件中，可通过迭代检索与生成组织上下文；这是本系统代码检索能力的相关工作背景。[正式论文摘要](https://aclanthology.org/2023.emnlp-main.151/)
- 不能据此声称：代码补全与缺陷修复是相同任务；本文的 AST 搜索实现复现了 RepoCoder，或其检索策略已经提升本文修复成功率。
- 核验状态：ACL 正式书目、摘要、DOI 和页码直接读取成功。

## 7. Lost in the Middle

- 引用键：`liu2024lostmiddle`。
- 作者：Nelson F. Liu, Kevin Lin, John Hewitt, et al.
- 题名：Lost in the Middle: How Language Models Use Long Contexts。
- 正式出版：Transactions of the Association for Computational Linguistics，2024，12：157–173。出版者为 MIT Press。
- 正式页面：[ACL Anthology](https://aclanthology.org/2024.tacl-1.9/)；DOI：[10.1162/tacl_a_00638](https://doi.org/10.1162/tacl_a_00638)。
- 版本辅助：[arXiv:2307.03172](https://arxiv.org/abs/2307.03172)，首发 2023 年，正式版年份为 2024 年。
- 可支持的观点：在论文所测任务及模型上，相关信息的位置会影响长上下文利用效果；可作为进行上下文选择与预算控制的研究动机。[正式论文摘要](https://aclanthology.org/2024.tacl-1.9/)
- 不能据此声称：所有现有模型都存在相同程度的问题，或本文的上下文压缩、记忆召回已解决该问题。原论文的问答与键值检索实验也不直接等价于代码修复实验。
- 核验状态：正式期刊卷号、页码、作者、年份与 DOI 直接读取成功。

## 8. Docker 官方文档

以下两项是动态在线文档，使用团体作者 Docker，引用日期写为 2026-10-20；页面没有明确出版年份时不自行推定为 2026 年。后续 BibLaTeX 可使用 `urldate = {2026-10-20}`，具体文献类型与格式遵从学校模板。

### 8.1 Engine security

- 引用键：`dockerSecurity`。
- 作者：Docker。
- 题名：Docker Engine security。
- 来源：[Docker 官方文档](https://docs.docker.com/engine/security/)。
- 可支持的观点：容器使用 namespaces 提供隔离，cgroups 负责资源控制；Docker daemon、挂载与容器配置也构成安全边界的一部分。[官方安全文档](https://docs.docker.com/engine/security/)
- 不能据此声称：Docker 提供绝对安全，或仅使用容器就能防止所有逃逸和宿主机影响。本项目安全能力仍须由实际参数与挂载范围证明。
- 核验状态：页面直接读取成功。

### 8.2 Resource constraints

- 引用键：`dockerResources`。
- 作者：Docker。
- 题名：Resource constraints。
- 来源：[Docker 官方文档](https://docs.docker.com/engine/containers/resource_constraints/)。
- 可支持的观点：容器默认没有资源约束，需要显式设置 CPU、内存等运行参数；硬限制和软限制具有不同语义。[官方资源限制文档](https://docs.docker.com/engine/containers/resource_constraints/)
- 不能据此声称：系统当前已配置某个限制，或资源限制能够保证模型修复逻辑正确。是否生效需以本项目执行配置和验证记录为依据。
- 核验状态：页面直接读取成功。

## 首批正文使用约束

1. 正文可使用 `[@yao2023react]` 一类稳定引用键，参考文献表或转换脚本再统一编号。不要把浏览工具内部引用标识写入文件。
2. 外部论文只能证明相关技术及其原实验；本项目的功能、测试数量和成功率须引用仓库代码、原始报告及执行记录。
3. 摘要一般无需引文；学校模板有不同要求时再统一调整。
4. 不直接比较不同模型、任务集、预算与验收方式下的成功率，也不把历史论文中的“当时最好成绩”写成当前结论。
5. 绪论可保留上述六篇最直接相关工作；长上下文与 Docker 文档留给后续技术或实现章节，不为凑引用数量堆叠条目。

