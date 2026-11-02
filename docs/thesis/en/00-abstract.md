# Abstract

Coding agents can inspect repositories, edit source code and execute commands, but generating a plausible patch does not establish that a defect has been repaired. Repository-level repair also requires execution constraints, explicit acceptance criteria, failure feedback and resource control.

This dissertation presents a multi-agent collaboration and verification system built on an existing Python terminal coding agent. Coordinator, worker and verifier roles use separate contexts and sequential handoffs. Changes are made in disposable workspaces, commands execute in restricted Docker containers, and fixed acceptance tests run against a separate verification copy. Execution evidence supports bounded retries under shared budgets. The system exports patches and structured reports, with procedural skills and provenance-aware project memory integrated into the workflow.

Archived verification records report 160 passing automated tests, including existing regressions. Ten artificial defects were injected into pinned python-dotenv source: two development tasks and eight held-out tasks. Across 24 real model runs, single-role execution feedback, multi-role review feedback and multi-role verification feedback completed acceptance in eight, five and four cases respectively. No false acceptances were observed. Multi-role failures resulted from token-budget exhaustion; one additional candidate passed tests without completing its workflow.

Functional evidence supports the implemented isolation, acceptance, retry and reporting mechanisms. The small repair experiment does not demonstrate a success-rate advantage for multiple roles. Repair assessment must distinguish candidate behaviour from workflow completion and account for coordination costs.

**Keywords:** coding agent; multi-agent collaboration; code repair; execution evidence; resource budget.
