# Project Specifications and Preliminary Report

Filename: GUID_Surname_UESTCHN4006P_Preliminary_year

**UESTCHN4006P | Preliminary report | Research direction revised 30 October 2026**

| Field | Information |
| --- | --- |
| Student Name | [To be completed] |
| Placement Company (if appropriate) | [To be completed / Not applicable] |
| Student Matriculation Number / GUID | [To be completed] |
| Working Title of Project | Context Management for Coding Agents: Tool-Evidence Selection and Evaluation in yeCoding |
| UESTC Student Number | [To be completed] |
| Name of First Supervisor | [To be completed] |
| Degree Programme | [To be completed] |
| Academic Year | [To be completed] |

## Declaration of Originality and Submission Information

*I affirm that this submission is all my own work in accordance with the University of Glasgow and UESTC Regulations, and the James Watt School of Engineering requirements.*

Signed (Student): ____________________    Date: ____________________

Submission details, student information and calendar dates remain to be confirmed before submission. Weeks below are relative planning milestones, not a reconstruction of work already completed.

<!-- pagebreak -->

## Project Description and Background

Coding agents repeatedly inspect source files, search a repository, edit code and execute commands. During a multi-turn task, earlier tool results can remain in subsequent model requests even after they have been duplicated or made outdated by an edit. This raises a practical question: **can managing tool evidence reduce repeatedly supplied context while preserving task-solving ability?**

The project will investigate this question within yeCoding, an existing Python terminal coding agent. The complete CLI, model integration, tool execution and agent loop will remain the engineering platform. A selectable context policy will decide which evidence a model request receives and how it is organised. Code repair provides executable evaluation tasks; the research focus is context management within a single-agent tool loop.

Three experimental lines will establish the evaluation boundary:

| Experimental line | Role | Interpretation |
| --- | --- | --- |
| Original yeCoding | Frozen internal baseline with its existing context strategy. | Control condition for assessing the new method. |
| Improved yeCoding | The same system with tool-evidence selection. | Its difference from original yeCoding tests the context method. |
| mini-SWE-agent | Fixed official v2.4.6, with its native prompts and interaction protocol. | External system reference; overall differences cannot be attributed solely to context management. |

The intended contribution is a deterministic method for selecting and refreshing tool evidence, together with an evaluation of the relationship between solution rate and cost. Existing AST parsing, indexing and context packing are supporting infrastructure. Their prior existence will be acknowledged; using them does not by itself establish a new contribution.

**Scope.** Main development and the final demonstration remain in yeCoding. The project will not build a second full product around mini-SWE-agent, transfer the method to mini in this phase, resume Repair V2 development or optimise multi-agent collaboration. Cross-task memory, automatic skill injection and external MCP services will be disabled in the comparison to reduce interference.

## SMART Objectives

1. **Specify by Week 2:** freeze system and dataset versions, define evidence provenance and selection rules, and establish a common logging, budget and external evaluation protocol.
2. **Validate by Week 6:** demonstrate original and improved yeCoding through their public entry points; verify that the legacy policy reproduces frozen-baseline requests and that evidence selection preserves tool associations and raw history.
3. **Evaluate by Week 12:** complete a five-task development pilot, freeze twenty formal tasks and run three repetitions per condition: 180 main runs, plus 120 ablation runs, subject to pilot-confirmed feasibility and available resources.
4. **Report by Week 16:** analyse official solution outcomes, consumption and failure cases, and update the existing dissertation and demonstration materials with reproducible evidence and explicit limitations. Negative results remain valid outcomes.

<!-- pagebreak -->

## Literature Review

### Tool interaction and repository evidence

ReAct provides a reasoning–action–observation loop [1], while SWE-agent demonstrates the importance of the interfaces through which an agent navigates, edits and tests a repository [2]. These motivate retaining the existing agent loop while examining what prior observations are supplied at the next request. Tool execution alone does not establish that a task has been solved; acceptance requires a separate evaluation.

RepoCoder combines repository retrieval and iterative generation for code completion [5]. Its relevance here is the selective use of repository information; code completion differs from issue repair, so its results cannot establish repair gains for yeCoding. Lost in the Middle reports position-sensitive use of long contexts in its evaluated settings [7]. This motivates checking evidence organisation instead of assuming that additional prompt content always helps. It does not establish an improvement for the model used in this project.

### Feedback, system complexity and evaluation

Reflexion and Self-Refine investigate feedback across iterative attempts [4,10]. For this project, execution failures are useful evidence to preserve, but the proposed first method will use deterministic selection rather than additional model-generated summaries. This makes the selection process inspectable and avoids introducing summary-model calls as another experimental variable.

AutoGen provides a reference for organising multiple conversational agents [3]. Agentless offers a more structured localisation, repair and validation approach [8], while RepairAgent combines tools with an autonomous repair process [9]. Together, these works motivate examining how information and execution are organised. They do not establish that more roles or more interaction improve outcomes under the same budget. This project therefore fixes a single-agent configuration and isolates context policy within yeCoding.

SWE-bench supports executable evaluation of repository-level issue resolution [6]. The planned study uses a fixed SWE-bench Lite subset and the official evaluator, rather than treating existing python-dotenv mutations as representative benchmark results. Container configuration and explicit resource settings support repeatable task execution [11,12]; they do not guarantee universal isolation or patch correctness.

| Research basis | Design implication | Question requiring this project's experiments |
| --- | --- | --- |
| ReAct; SWE-agent [1,2] | Preserve the tool loop and observe actual requests. | Does evidence selection change task completion? |
| RepoCoder; long-context study [5,7] | Select relevant code and manage repeated context. | Which information can be omitted without harming solutions? |
| Reflexion; Self-Refine [4,10] | Retain useful failure evidence across turns. | Can deterministic selection suffice without summarisation calls? |
| AutoGen; Agentless; RepairAgent [3,8,9] | Treat system organisation as a possible confound. | What can internal comparison establish beyond external comparison? |
| SWE-bench; Docker [6,11,12] | Use fixed tasks, environments and executable evaluation. | What solution–cost trade-off remains under common budgets? |

*Table 1. Literature-to-design mapping. These are project design inferences, not claims that prior work validates the proposed method.*

<!-- pagebreak -->

## Technical Background

### Research questions and proposed method

**RQ1:** Does selecting tool evidence reduce cumulative input tokens and monetary cost while maintaining official task solution rate, compared with original yeCoding?

**RQ2:** How much do structure information and exact deduplication contribute, and which omissions cause failures?

**Working hypothesis:** repeated reads and outdated source evidence create avoidable input overhead. Selective retention may reduce that overhead, but removing useful evidence may lower solution rate. The study will measure this trade-off rather than assume an improvement.

The architecture adds a context-policy boundary to the existing system:

```text
CLI / SDK / Runtime
        ↓
Existing Agent Loop
        ↓
Selectable Context Policy
   legacy / evidence
        ↓
Model Requests and Tool Execution
```

*Figure 1. Context-policy placement. Model adaptation and editing tools remain shared by the two yeCoding conditions.*

The legacy policy retains existing compression and history updates. The evidence policy keeps full raw history and creates a separate message view for each request. Tool results carry call identifiers, hashes and ordering; structured file reads additionally carry file versions and source ranges where available. Ordinary shell output remains command evidence without inferred file provenance.

The initial method will deduplicate identical content, identify outdated source evidence after edits, and select historical evidence under a soft target of 16,000 estimated tokens. Priority will consider recent failures, modified code and related structure, task-word matches and recency. The current user requirement and recent messages will be protected, with tool calls and results kept associated. Long textual results will use traceable excerpts, including failure information near log endings. Omissions and budget overruns will be recorded explicitly. No extra summarisation-model requests are planned.

The final demonstration will follow one task: what the original policy carried, what the evidence policy retained or omitted, whether the exported patch passed evaluation, and how consumption changed. This connects the research method to observable system behaviour.

### Controlled evaluation

Original yeCoding is frozen at `7a1783bc723d358090a3c9f318d7bf795903138e`. The external reference is mini-SWE-agent v2.4.6, pinned to full commit `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`. Dependencies, task data, evaluation tooling and configurations will be recorded with the experimental artefacts.

After environment-only checks, tasks will be grouped by repository, shuffled with seed `20261030` and sampled by round-robin selection. Five development tasks will be separate from twenty formal tasks. Selection will not use model performance or reference-patch contents. Existing artificial defects remain historical or debugging material.

The two yeCoding conditions will share model settings, tool definitions, system prompts, dynamic-field rules, permissions and budgets. mini will retain its native prompts, tools and completion mechanism while sharing the model settings, task environments, external budgets and evaluator. Its structural differences will be included in interpretation.

The planned model is `deepseek-v4-flash`, temperature 0, maximum output 8,192 tokens per request, 120,000 cumulative tokens checked before requests, 64 requests and 900 seconds per task. Complete settings and prices will be frozen before formal execution. Each run will use a fresh container and work copy. Run order will rotate within task/repetition blocks, with serial execution by default. Temperature 0 will not be treated as a determinism guarantee.

| Study | Conditions | Planned formal runs |
| --- | --- | --- |
| Main comparison | Original yeCoding, improved yeCoding, mini-SWE-agent | 20 tasks × 3 conditions × 3 repetitions = 180 |
| Ablations | Evidence selection without structure; without deduplication | 20 tasks × 2 conditions × 3 repetitions = 120 |
| Total | Development runs counted separately | 300 |

*Table 2. Proposed formal evaluation. Ablations retain the same evidence-selection quota.*

Patches will be graded by the official SWE-bench evaluator. Reference and evaluation patches will remain outside agent-visible inputs. Official solution status and normal agent completion will be reported separately. Provider errors, timeouts, empty patches and exhausted budgets will remain in the denominator; infrastructure errors will be labelled separately with attempts and incurred costs retained. The final response may exceed the request-time token threshold, and actual usage will still be counted.

### Evidence, analysis and current feasibility

Records will include actual request messages, system prompts, tool definitions and fingerprints; raw tool results and provenance; selection decisions; model usage and cache information; elapsed time; termination reasons; and final patches. Estimated context size will be distinguished from provider-reported tokens, and credentials will be excluded.

Primary outcomes are official solution rate, normal completion rate, input/output tokens, cache use, cost, requests and elapsed time. Analysis will include consumption across all runs and paired consumption where both yeCoding conditions solve a task, so early failure is not presented as a saving. Repetitions will be aggregated by task, with paired differences and task-resampling intervals; repeated runs will not be treated as independent tasks.

**Current position.** The selectable policy, observation layer and three-line evaluation framework are implemented. Engineering checks and real CLI probes provide feasibility evidence, not solution-rate evidence. The first SWE-bench task-image pull timed out, so the three-line development loop, official task grading and formal experiments remain pending. The immediate milestone is to complete that development loop before freezing the formal study. No context-management benefit is claimed from the current implementation or historical repair results.

Key risks are image availability, model API costs, information loss and limited task diversity. Environment checks and the development pilot will establish feasibility before formal execution. Any change to the planned sample or budget will be documented before the affected formal runs.

<!-- pagebreak -->

## References

[1] S. Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models," ICLR, 2023. [Original paper](https://openreview.net/forum?id=WE_vluYUL-X).

[2] J. Yang et al., "SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering," Advances in Neural Information Processing Systems, vol. 37, 2024. [Publisher](https://proceedings.neurips.cc/paper_files/paper/2024/hash/5a7c947568c1b1328ccc5230172e1e7c-Abstract-Conference.html).

[3] Q. Wu et al., "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversations," First Conference on Language Modeling, 2024. [Original paper](https://openreview.net/forum?id=BAakY1hNKS).

[4] N. Shinn, F. Cassano, A. Gopinath, K. Narasimhan and S. Yao, "Reflexion: Language Agents with Verbal Reinforcement Learning," Advances in Neural Information Processing Systems, vol. 36, 2023. [Publisher](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html).

[5] F. Zhang et al., "RepoCoder: Repository-Level Code Completion Through Iterative Retrieval and Generation," EMNLP, pp. 2471-2484, 2023. [doi:10.18653/v1/2023.emnlp-main.151](https://doi.org/10.18653/v1/2023.emnlp-main.151).

[6] C. E. Jimenez et al., "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?," ICLR, 2024. [Original paper](https://openreview.net/forum?id=VTF8yNQM66).

[7] N. F. Liu et al., "Lost in the Middle: How Language Models Use Long Contexts," Transactions of the Association for Computational Linguistics, vol. 12, pp. 157-173, 2024. [doi:10.1162/tacl_a_00638](https://doi.org/10.1162/tacl_a_00638).

[8] C. S. Xia et al., "Agentless: Demystifying LLM-based Software Engineering Agents," FSE, 2025. [Formal paper](https://lingming.cs.illinois.edu/publications/fse2025.pdf).

[9] I. Bouzenia, P. Devanbu and M. Pradel, "RepairAgent: An Autonomous, LLM-Based Agent for Program Repair," ICSE, pp. 2188–2200, 2025. [Formal paper](https://www.software-lab.org/publications/icse2025_RepairAgent.pdf).

[10] A. Madaan et al., "Self-Refine: Iterative Refinement with Self-Feedback," Advances in Neural Information Processing Systems, vol. 36, 2023. [Original paper](https://arxiv.org/abs/2303.17651).

[11] Docker, "Docker Engine security," official documentation, accessed 26 October 2026. [Documentation](https://docs.docker.com/engine/security/).

[12] Docker, "Resource constraints," official documentation, accessed 26 October 2026. [Documentation](https://docs.docker.com/engine/containers/resource_constraints/).

<!-- pagebreak -->

## Measurable Outcomes & Work Plan

**Project category:** software development and experimental evaluation. The schedule organises remaining validation, experiments and writing around the existing implementation.

| Deliverable | Measurable acceptance criterion | Due |
| --- | --- | --- |
| Frozen protocol and feasible environment | Version/configuration manifest; usable task images; pilot-based cost estimate. | W2 |
| Three-line development loop | Real model requests, patch export and official evaluation on the development set; failures recorded. | W4 |
| Validated context method | Legacy request equivalence; duplicate, stale-source, long-log, tool-pairing and budget checks; inspected development traces. | W6 |
| Formal evidence and analysis | 180 main and 120 ablation runs, or a prospectively documented revision; task-level solution–cost analysis. | W12 |
| Dissertation and demonstration | Existing report/manuscript updated in place; reproducible artefacts, limitations and a same-task comparison. | W16 |

| Workstream | W1–2 | W3–4 | W5–6 | W7–8 | W9–10 | W11–12 | W13–14 | W15–16 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Environment and protocol | ● | | | | | | | |
| Development runs and method validation | ● | ● | ● | | | | | |
| Freeze and main experiments | | | | ● | ● | | | |
| Ablations and analysis | | | | | ● | ● | | |
| Existing dissertation and demonstration | | | | | | ● | ● | ● |

*Figure 2. Relative work schedule. Calendar dates and submission details require supervisor confirmation.*

Required resources are a Docker-capable computer, Python, image/evidence storage and sufficient model API credit. No model training or additional specialised hardware is proposed. Student details, the originality declaration, risk and ethics forms, logbook and institutional submission arrangements must be completed separately with the supervisor; this draft does not constitute approval or submission.
