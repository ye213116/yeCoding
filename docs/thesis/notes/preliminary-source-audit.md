# Preliminary Report: Primary-Source Audit

Checked: 26 October 2026. Scope: sources for an English preliminary proposal provisionally titled *Design and Implementation of a Multi-Agent Collaboration and Verification System for Code Repair*. This is a research note, not a claim that the proposed work has already been completed.

The existing thesis introduction and evaluation chapter were read for scope. The bibliography below contains ten research papers and two official documentation sources. Publication years refer to the cited formal versions; an earlier arXiv submission is not substituted for the publication year. All substantive literature claims below are linked to their primary sources. Formal pages, author-hosted papers and official project citations were used; secondary search results were not used as evidence.

## Verified Research Papers

### 1. ReAct (`yao2023react`)

Shunyu Yao, Jeffrey Zhao, Dian Yu, et al. 2023. *ReAct: Synergizing Reasoning and Acting in Language Models*. The Eleventh International Conference on Learning Representations (ICLR).

Primary sources: [formal entry](https://openreview.net/forum?id=WE_vluYUL-X); [author-submitted paper record](https://arxiv.org/abs/2210.03629).

The paper interleaves reasoning and external actions, using observations to update subsequent actions. This supports a tool-observation loop as an architectural starting point. Its evaluated settings include question answering, fact verification and interactive environments; they are not this project's repair tasks. It cannot establish repair quality or a benefit from multiple roles. The arXiv record identifies v3 as the ICLR camera-ready version; the initial preprint appeared in 2022, whereas the formal citation is 2023. [Paper abstract and version note](https://arxiv.org/abs/2210.03629).

### 2. SWE-agent (`yang2024sweagent`)

John Yang, Carlos E. Jimenez, Alexander Wettig, et al. 2024. *SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering*. Advances in Neural Information Processing Systems 37. DOI: [10.52202/079017-1601](https://doi.org/10.52202/079017-1601).

Repository navigation, editing and test execution are exposed through an agent-computer interface, and interface design is evaluated as a contributor to agent behavior. This supports treating tool interfaces as part of the system design. Its reported SWE-bench and HumanEvalFix results belong to its own experimental setup; they are not current leaderboard claims or results of yeCoding. [Official proceedings page](https://proceedings.neurips.cc/paper_files/paper/2024/hash/5a7c947568c1b1328ccc5230172e1e7c-Abstract-Conference.html).

### 3. AutoGen (`wu2024autogen`)

Qingyun Wu, Gagan Bansal, Jieyu Zhang, et al. 2024. *AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversations*. First Conference on Language Modeling (COLM).

Primary sources: [formal entry](https://openreview.net/forum?id=BAakY1hNKS); [formal PDF hosted by Microsoft Research](https://www.microsoft.com/en-us/research/wp-content/uploads/2023/08/LLM_agent.pdf).

The framework composes configurable agents through conversation patterns and tools, allowing combinations of model, human and execution behavior. This provides an implementation reference for role handoff and message flow. Pilot application results do not prove that additional roles improve this project's repair success under an equal budget. Use the plural **Conversations** from the formal PDF; some first-party publication pages and the earlier preprint use the singular. OpenReview's HTML entry required browser verification, but the Microsoft-hosted formal PDF was readable. [Formal paper, first page](https://www.microsoft.com/en-us/research/wp-content/uploads/2023/08/LLM_agent.pdf).

### 4. Reflexion (`shinn2023reflexion`)

Noah Shinn, Federico Cassano, Ashwin Gopinath, Karthik Narasimhan and Shunyu Yao. 2023. *Reflexion: Language Agents with Verbal Reinforcement Learning*. Advances in Neural Information Processing Systems 36. DOI: [10.52202/075280-0377](https://doi.org/10.52202/075280-0377).

The approach converts task feedback into reflective text retained in episodic memory for later attempts, without updating model weights. This motivates retaining useful failure evidence between repair attempts. Saving an execution log alone does not reproduce Reflexion, and its coding results cannot validate yeCoding's persistent memory or repository repair. Use the five authors listed in the formal proceedings, rather than mixing in a different arXiv author list. [Official proceedings page](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html).

### 5. RepoCoder (`zhang2023repocoder`)

Fengji Zhang, Bei Chen, Yue Zhang, et al. 2023. *RepoCoder: Repository-Level Code Completion Through Iterative Retrieval and Generation*. Proceedings of EMNLP 2023, pp. 2471-2484. DOI: [10.18653/v1/2023.emnlp-main.151](https://doi.org/10.18653/v1/2023.emnlp-main.151).

The method alternates retrieval of repository context with code generation. This supports selective context retrieval as an alternative to assuming all relevant source text can be inserted usefully at once. Its task is repository code completion, not issue repair; neither its gains nor its retrieval architecture should be attributed to yeCoding's AST/SQLite implementation. [Official ACL paper page and abstract](https://aclanthology.org/2023.emnlp-main.151/).

### 6. SWE-bench (`jimenez2024swebench`)

Carlos E. Jimenez, John Yang, Alexander Wettig, et al. 2024. *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* The Twelfth International Conference on Learning Representations (ICLR).

Primary sources: [formal entry](https://openreview.net/forum?id=VTF8yNQM66); [official citation](https://www.swebench.com/citations); [paper record and abstract](https://arxiv.org/abs/2310.06770).

The benchmark associates real repository issues with code changes and executable evaluation. The source describes 2,294 tasks across 12 Python repositories. It motivates repository-level tasks and test-based outcomes. A small task set constructed by injecting defects into fixed source code is not SWE-bench and cannot support direct comparisons with its published percentages. The first preprint was released in 2023; cite the formal ICLR 2024 version. [Original abstract](https://arxiv.org/abs/2310.06770) and [official formal bibliography](https://www.swebench.com/citations).

### 7. Lost in the Middle (`liu2024lostmiddle`)

Nelson F. Liu, Kevin Lin, John Hewitt, et al. 2024. *Lost in the Middle: How Language Models Use Long Contexts*. Transactions of the Association for Computational Linguistics 12, pp. 157-173. DOI: [10.1162/tacl_a_00638](https://doi.org/10.1162/tacl_a_00638).

On the tested question-answering and key-value retrieval settings, changing the position of relevant information affects performance, with important information in the middle often harder to use. This motivates investigating context selection and ordering; it does not establish the behavior of every later model or prove that compression resolves the issue for code repair. [Official ACL journal page](https://aclanthology.org/2024.tacl-1.9/).

### 8. Agentless (`xia2025agentless`)

Chunqiu Steven Xia, Yinlin Deng, Soren Dunn and Lingming Zhang. 2025. *Demystifying LLM-Based Software Engineering Agents*. Proceedings of the ACM on Software Engineering 2, FSE, Article FSE037, 24 pages. DOI: [10.1145/3715754](https://doi.org/10.1145/3715754).

The paper studies a structured localization, repair and validation pipeline with restricted autonomous action selection. It provides a useful counterpoint to assuming that increasingly elaborate agent orchestration is necessary. Its original findings justify including a simpler baseline and recording cost; they do not show that all agent workflows are inferior. Any numerical results would require the paper's particular benchmark, model and version qualifiers. The formal paper is dated July 2025; cite that version rather than silently adopting the preprint year or title. [Author-hosted formal paper, first page](https://lingming.cs.illinois.edu/publications/fse2025.pdf).

### 9. RepairAgent (`bouzenia2025repairagent`)

Islem Bouzenia, Premkumar Devanbu and Michael Pradel. 2025. *RepairAgent: An Autonomous, LLM-Based Agent for Program Repair*. 2025 IEEE/ACM 47th International Conference on Software Engineering (ICSE), pp. 2188-2200. DOI: [10.1109/ICSE55347.2025.00157](https://doi.org/10.1109/ICSE55347.2025.00157).

The system combines repair-specific tools, dynamically updated prompts and a finite-state controller. The agent can interleave information gathering, repair and test validation using previous feedback. This supports explicit states and tool results in a repair workflow. Evaluation on Defects4J does not establish success on this project's Python tasks or an advantage from multiple agents. Its preprint first appeared in 2024, but the cited formal version is ICSE 2025. The author-hosted formal PDF became readable after an initial fetch timeout. [Formal paper](https://www.software-lab.org/publications/icse2025_RepairAgent.pdf); [publisher metadata](https://ieeexplore.ieee.org/abstract/document/11029914).

### 10. Agent Trajectory Study (`bouzenia2025trajectories`)

Islem Bouzenia and Michael Pradel. 2025. *Understanding Software Engineering Agents: A Study of Thought-Action-Result Trajectories*. 2025 40th IEEE/ACM International Conference on Automated Software Engineering (ASE). DOI: [10.1109/ASE63991.2025.00234](https://doi.org/10.1109/ASE63991.2025.00234).

The study analyzes 120 trajectories and 2,822 model interactions from RepairAgent, AutoCodeRover and OpenHands, examining action sequences, token use, reasoning coherence and feedback integration. It supports recording trajectories and examining failure types alongside final success. This is an observational analysis, not evidence that yeCoding's logging causes better repairs. The author record states acceptance at ASE 2025; publisher indexing was added in January 2026. Retain the proceedings year 2025, and omit page numbers because they were not verified here. [Author-submitted paper record](https://arxiv.org/abs/2506.18824); [publisher DOI](https://doi.org/10.1109/ASE63991.2025.00234). Publisher HTML required JavaScript verification, so the substantive claims were checked against the authors' arXiv record.

## Official Execution-Environment Sources

### 11. Docker Engine Security (`dockerSecurity`)

Docker. *Docker Engine security*. Online documentation. Accessed 26 October 2026; no publication year inferred.

Namespaces and control groups contribute isolation and resource control, but daemon access, mounts and capability configuration affect security. The documentation describes incomplete isolation risks. This supports explicit execution constraints and careful configuration, not a claim of absolute sandbox safety. [Official documentation](https://docs.docker.com/engine/security/).

### 12. Docker Resource Constraints (`dockerResources`)

Docker. *Resource constraints*. Online documentation. Accessed 26 October 2026; no publication year inferred.

Containers have no default resource limits; CPU and memory restrictions must be configured. Hard and soft memory limits differ. This supports including explicit limits in the proposed evaluation environment; it does not prove that particular limits are present or effective in the current implementation. [Official documentation](https://docs.docker.com/engine/containers/resource_constraints/).

## Synthesis For The Proposal

The following are design inferences from the literature, not results reported by these sources:

- Combine a tool-observation loop with explicit repair states, drawing on ReAct, SWE-agent and RepairAgent. Separate patch generation, actual test execution and the interpretation of results.
- Use AutoGen as a reference for role interfaces, while Agentless motivates a simpler comparison condition. Treat a multi-role benefit as a question to test, including the possibility that coordination consumes a limited budget without improving outcomes.
- Use RepoCoder and Lost in the Middle to motivate selected repository context, and Reflexion to motivate feedback retention. Do not claim to reproduce these algorithms or to have proven a memory benefit.
- Use SWE-bench to motivate behavioral evaluation, and the trajectory study to motivate token, action and failure analysis. Fix source versions and acceptance tests before comparison; preserve infrastructure failures and budget exhaustion as distinct outcomes.
- Use Docker documentation to justify explicit execution settings and resource limits. A task copy protects the source worktree; container configuration controls a different boundary. Neither implies universal program correctness or complete security.

A defensible hypothesis is that separating repair generation from evidence-based verification may improve the reliability of completion reporting, while its effect on accepted repair rate and resource use must be measured. A coordinator, editor and verifier are a proposed design choice, not a novel algorithm established by these papers. A fair pilot can compare single-role execution feedback, multi-role review feedback and multi-role execution feedback with the same model, tasks and outer limits, report raw outcomes and costs, and avoid significance or generalization claims from a small convenience sample.

The preliminary report should use planned work and intended evaluation language. Existing thesis implementation and historical experiments may establish feasibility, but they must not be silently rewritten as future observations or used to invent expected success rates. Student identity, supervisor, academic year, institutional dates, approved scope and actual originality declaration remain matters for the student to confirm. No form has been signed or submitted by preparing this note.
