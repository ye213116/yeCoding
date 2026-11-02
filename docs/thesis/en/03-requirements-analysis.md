# Chapter 3 Requirements and Specification

## 3.1 Tasks and scope

The system serves terminal users, programmatic callers and evaluators. Each supplies an issue, current source directory, prepared container image, at least one fixed acceptance command and positive resource limits. Evidence is delivered outside the source workspace. Current file bytes establish the input: Git HEAD alone cannot identify uncommitted changes.

Dependencies must already exist in the image. Missing tests or an unavailable environment must produce explicit errors without host-shell fallback. Supported repair edits business source in disposable copies. Concurrent writers, automatic merges, binary patches, links, special files and tasks requiring protected-test changes are excluded.

## 3.2 Functional specification

Table3-2 defines the shared contracts. Different interfaces may organise parameters differently, but may not silently change acceptance semantics.

Table3-2 Functional requirements for the repair workflow.

| ID | Requirement | Observable condition |
| --- | --- | --- |
| FR-01 | Repository tools | Read, search, edit and command results reflect execution; invalid inputs are rejected. |
| FR-02 | Code context | Retrieval retains source locations and identifies truncation. |
| FR-03 | Shared entry points | Core acceptance is consistent; unsuccessful outcomes are explicit. |
| FR-04 | Baseline | Source is recorded and a genuine failure established before repair. |
| FR-05 | Role handoffs | Separate histories and permitted tools refer to the same candidate. |
| FR-06 | Fixed acceptance | Real test results govern acceptance; protected checks cannot be weakened. |
| FR-07 | Bounded retry | Candidate-specific feedback and shared budgets control continuation. |
| FR-08 | Evidence delivery | Success exports a patch/report; failure retains available evidence. |
| FR-09 | Procedural skills | Actual role content, version and provenance are recorded. |
| FR-10 | Project memory | Scope, expiry and source applicability are checked. |

A passing baseline does not count as a new repair. Worker summaries do not replace file differences; favourable reviews do not override failing tests. Empty changes or consecutive identical candidates end as no progress. A passing candidate is not a completed workflow if required handoffs remain unfinished.

Skills guide operations without granting permissions. Memory supplies untrusted historical leads, not current acceptance. Automatic successful experience is saved only after workflow success, with source and report provenance. Disabling memory skips recall and saving; recoverable storage problems produce warnings rather than overwrite established test facts.

## 3.3 Non-functional specification

Table3-3 separates execution constraints from quality claims. No minimum repair rate or universal collaboration benefit is specified.

Table3-3 Non-functional requirements and their inspection conditions.

| ID | Requirement | Inspection condition |
| --- | --- | --- |
| NFR-01 | Source/path boundaries | Copies contain edits; out-of-scope files and unsupported types are rejected. |
| NFR-02 | Resource limits | Commands/tasks have limits and cleanup on timeout or cancellation. |
| NFR-03 | Credential boundary | Model credentials are not forwarded; standard private-file patterns are excluded. |
| NFR-04 | Traceability | Candidate-linked evidence distinguishes success from incomplete execution. |
| NFR-05 | Integration consistency | Explicit options override configuration; cancelled tasks reject late completion. |
| NFR-06 | Evaluation clarity | Completion, additional checks and consumption use explicit all-run denominators. |

Protection applies to supported file conventions, not arbitrary acceptance scripts or every possible secret. Containers restrict commands while host file tools require separate checks. Token usage is checked before a request, so a final response can cross the threshold. Cleanup may delay return beyond the nominal deadline; cancellation does not guarantee immediate interruption of a remote model request.

## 3.4 Acceptance and evaluation

Completion requires a genuine failing baseline, a non-empty legal candidate, passing fixed commands and delivery after all strategy-required stages. Functional scenarios cover missing commands, passing baselines, failed-then-passing retries, misleading positive reviews, boundary violations, no progress, exhausted budgets, unavailable images, timeout, cancellation and knowledge/interface integration. The detailed traceability matrix is in TableA-2; the essential completion conditions remain specified here.

Comparative evaluation fixes source, model settings, environment, commands and outer limits. Development cases are excluded from the held-out denominator, and artificial defects are identified as such. Post-run checks assess exported patches without changing original termination states. Functional operation, repair quality and reproducibility are separate claims: records support inspection but cannot guarantee identical remote-model output.
