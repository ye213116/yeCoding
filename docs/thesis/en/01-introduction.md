# Chapter 1 Introduction

## 1.1 Background and motivation

Repository repair requires a failure to be reproduced, relevant implementation to be located, a change to be made and regressions to be checked. A generated patch can look plausible while remaining incorrect. Likewise, a successful file write or a model's statement that a defect is fixed does not establish that the required behaviour has been restored.

Large language models (LLMs) can interact with repositories through tools. ReAct alternates reasoning, actions and observations; SWE-agent studies navigation, editing and execution through an agent-computer interface. These studies motivate an interactive coding workflow, but their results do not validate this implementation. [@yao2023react; @yang2024sweagent]

Separate roles offer a way to divide planning, editing and inspection. AutoGen provides a reference for configurable conversational agents. Role separation also repeats information and consumes requests, so its value must be measured rather than assumed. [@wu2024autogen]

This dissertation extends the existing yeCoding Python terminal agent with a dedicated repair workflow. A coordinator organises the task, a worker edits a disposable copy and a verifier examines the candidate. Fixed tests, rather than review text, determine acceptance. Restricted execution and shared budgets constrain the process, while patches and structured records make successful and incomplete outcomes inspectable.

## 1.2 Task definition and research questions

A task comprises an issue description, current source state, prepared execution image, fixed acceptance commands and resource budgets. The output is a candidate patch with execution evidence and a termination state. The system does not automatically apply changes to the original repository.

Candidate behaviour and workflow completion are distinct. A candidate may pass tests while a subsequent required handoff exhausts the budget. Conversely, an already passing input does not establish that a repair occurred. These distinctions lead to three questions:

1. **RQ1:** How can general coding capabilities be retained while bounding file changes and command execution, preserving original source and cleaning up after timeout or cancellation?
2. **RQ2:** How can role handoffs associate actual candidates with tests and reviews, supporting bounded retries without treating model assertions as acceptance?
3. **RQ3:** Under matched outer budgets, how do single-role execution feedback, multi-role review feedback and multi-role verification feedback differ in completion, consumption and failure categories?

RQ3 permits adverse results for collaboration. The system targets Python tasks with runnable tests and caller-prepared environments. Model training, arbitrary-language semantics, concurrent patch merging and virtual-machine-level isolation are outside scope.

## 1.3 Contributions and starting position

The work builds on an existing agent rather than implementing all infrastructure from scratch. It contributes:

- A dedicated repair orchestrator with separate coordinator, worker and verifier histories, restricted tools and sequential handoffs.
- Disposable editing and verification copies, candidate checks, restricted container commands and source-associated patch export.
- Fixed acceptance, evidence-based feedback and shared attempt, request, token and time limits, with explicit unsuccessful states.
- Integration of procedural skills and provenance-aware project memory.
- Functional verification and a controlled comparison retaining failures and reporting candidate checks separately from completed workflows.

The command-line interface (CLI), interactive terminal, software development kit (SDK) and Runtime adapters reuse the same core. General ReAct, Plan and Team modes remain separate: repair-specific container and acceptance controls must not be attributed to every agent entry point. Skills and memory are functionally integrated, without an experimentally established independent quality benefit.

The dissertation proceeds from literature and specification to design, implementation, results, discussion and conclusions. Supporting details are in Appendix A; the central method and findings remain in the main text.
