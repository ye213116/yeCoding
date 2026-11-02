# Chapter 2 Literature Review and Technical Background

## 2.1 Repair models and fault localisation

Automatic program repair separates a proposed change from the criterion used to accept it. Monperrus distinguishes repair objectives and oracles, while Gazzola et al. survey generate-and-validate and semantics-driven approaches. These taxonomies motivate an explicit task definition: passing available tests establishes a bounded observation, not universal correctness. [@monperrus2018repair; @gazzola2019survey]

GenProg searches program variants using genetic programming and existing tests. Nopol combines runtime observations and constraint solving for conditional bugs. Their generators and fault models differ, but both make the relationship between candidate search and executable constraints explicit. An LLM changes how candidates are proposed; it does not remove the need for an oracle. Neither study supplies a direct baseline for the present Python agent. [@legoues2012genprog; @xuan2017nopol]

Fault localisation is a separate difficulty. Wong et al. survey techniques for connecting observed failures to suspicious code. Here, lexical symbol retrieval helps navigation but is not spectrum-based localisation. Clear issue descriptions and local mutations reduce the localisation burden, limiting comparisons with unrestricted repository tasks. [@wong2016localization]

## 2.2 Learned generation and richer evidence

Tufano et al. learn transformations from historical buggy/fixed code pairs. SequenceR uses sequence-to-sequence learning, selected context and a copy mechanism for one-line repair. These studies illustrate the relevance of source representation and candidate-generation constraints. Their developer-patch matches and supplied-location assumptions differ from behavioural repository acceptance; the present system neither trains these models nor reproduces their benchmarks. [@tufano2019neuralrepair; @chen2021sequencer]

JAID uses state abstractions to extract information beyond ordinary tests for contract-based repair without supplied contracts. This provides a counterpoint to relying on test results alone, but a verifier reading logs does not implement JAID's semantic abstractions. Adding a review role cannot be described as equivalent semantic validation. [@chen2021contractrepair]

RepairLLaMA investigates repair-specific representations and parameter-efficient adaptation for Java bugs within one function. It offers a different route from orchestrating an unchanged model service: training and representation design, rather than role handoffs. The present system trains no adapters, and its Python workflow outcomes are not directly comparable to that evaluation. [@silva2025repairllama]

## 2.3 Patch overfitting and assessment

Yu et al. distinguish regression introduction from incomplete fixing and examine generated tests for Nopol. Their findings indicate that extra tests can help without solving the oracle problem. This motivates protecting acceptance tests and distinguishing test adequacy from broader correctness. [@yu2019overfitting]

Ye et al. assess patches at scale using generated tests and human repairs as reference oracles. Their QuixBugs study also examines plausible-patch correctness through manual and automatic assessment. These studies support checks beyond the suite that guided search, but their assessment techniques have assumptions and imperfections. The withheld tests here add evidence without reproducing those methods or proving correctness on untested inputs. [@ye2021assessment; @ye2021quixbugs]

## 2.4 Benchmarks and repository context

ManyBugs and IntroClass establish documented C repair benchmarks for reproducible comparisons. SWE-bench instead connects real repository issues to executable evaluation. They motivate pinned inputs and clearly reported task construction. The injected python-dotenv defects used here are neither historical issues nor instances of these benchmarks; cross-benchmark success rates are not directly comparable. [@legoues2015manybugs; @jimenez2024swebench]

RepoCoder combines repository retrieval with iterative completion. Lost in the Middle observes position-sensitive information use on its evaluated tasks. These results motivate selective context, without establishing a repair gain from this implementation's Python abstract syntax tree (AST) index. Its static relationships are approximate and its lexical retrieval does not use an embedding model. [@zhang2023repocoder; @liu2024lostmiddle]

## 2.5 Tool interaction and multiple roles

ReAct and SWE-agent motivate observable repository tools and interaction design, as introduced in Chapter1. AutoGen provides a reference for role organisation; Reflexion studies retaining textual feedback between attempts without updating model weights. Independent histories do not guarantee independent judgments when roles share a model and source. [@wu2024autogen; @shinn2023reflexion]

Hou et al.'s systematic review spans model, data and evaluation choices in software engineering, reinforcing the need to qualify results by setting. Its search period does not represent a complete October 2026 state of the art. In this project, coordination cost is measured alongside acceptance rather than assumed beneficial. [@hou2024llmse]

Table2-1 synthesises the design implications and limits.

Table2-1 Research strands informing the repair workflow and the limits on transferring their findings.

| Strand | Representative sources | Design implication | Limit |
| --- | --- | --- | --- |
| Repair/oracles | Surveys, GenProg, Nopol | Explicit acceptance and fault model | Tests are incomplete |
| Learned generation | Tufano, SequenceR | Selected source and bounded candidates | Different tasks/models |
| Assessment | Yu; Ye studies; JAID | Preserve independent evidence | Not a correctness proof |
| Benchmarks | ManyBugs; SWE-bench | Pin inputs and report provenance | Synthetic corpus is narrower |
| Context/agents | RepoCoder, ReAct, AutoGen | Tools, context and role contracts | Extra interaction costs resources |

## 2.6 Technical foundations

The existing query loop can be represented by instructions $I_t$, history $H_t$, available tools $\mathcal{T}_t$, model decision $\pi_\theta$ and executor $E$:

$$
a_t=\pi_\theta(I_t,H_t,\mathcal{T}_t),\qquad
o_t=E(a_t),\qquad
H_{t+1}=H_t\oplus(a_t,o_t).
$$

This describes interaction, not model training. The executor validates actions and associates results by call identifier. A text response can end a role call without satisfying task acceptance.

Instructions, history, tools, evidence and output allowances compete for a context window $W$:

$$
B_{\mathrm{prompt}}+B_{\mathrm{history}}+B_{\mathrm{tools}}
+B_{\mathrm{evidence}}+B_{\mathrm{output}}+B_{\mathrm{reserve}}\leq W.
$$

Estimated tokens support code selection and conversation compression; provider usage measures consumption. Retrieval selects repository evidence, while history compression reduces past interaction. Skills supply reusable procedures; project memory supplies attributable experience. Neither grants permissions or overrides current tests.

Disposable copies protect original files, while host path checks restrict file tools. Container isolation uses host-kernel mechanisms such as namespaces, control groups and capabilities; sharing the kernel limits the separation it provides. These are configured constraints, not a universal security guarantee. [@sultan2019containers] The present runner's central processing unit (CPU), memory and command limits are implementation choices described in Chapter5 and checked by its functional tests.
