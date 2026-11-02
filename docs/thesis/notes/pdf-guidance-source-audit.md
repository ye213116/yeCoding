# Sources for the Final-Report Guidance Revision

Research checked on 26 October 2026. Scope: primary academic sources for the
English dissertation's repair, verification, context and evaluation arguments.
This note supplies thirteen journal additions to the existing seven research
papers and two Docker documents. If all are substantively cited, the resulting
22-item bibliography contains fourteen journal articles, six conference papers
and two technical documentation sources. Surveys are journal research articles;
they should support synthesis rather than replace citations to original methods.

## Verification Method and Limits

Research claims below come from publisher abstracts/full text, author manuscripts
or author-maintained artefacts. Metadata was checked against the same sources
and publisher-deposited Crossref records at `https://api.crossref.org/works/DOI`.
Several ACM and IEEE pages blocked automated access; accessible author copies
and registered metadata were used instead. No paywall was bypassed. Publication
years refer to journal issues where verified, rather than preprint dates.

Two metadata qualifications should remain explicit:

- Monperrus's author version is titled *Automatic Software Repair: A Bibliography*,
  whereas ACM's Crossref record shortens it to *Automatic Software Repair*.
  The author title and the publisher DOI identify the same article.
- SequenceR's author copy and Microsoft record retain 2019 early-access metadata,
  and Crossref returns a 2021 year with placeholder pages `1-1`. Final issue
  pagination was not available from an accessible primary source in this audit.
  Consequently its BibTeX deliberately omits volume, issue and page numbers.
  Do not copy the placeholder `1-1` into the dissertation.

## Claim-to-Source Audit

### `monperrus2018repair`

Martin Monperrus, *Automatic Software Repair: A Bibliography*, ACM Computing
Surveys 51(1), 2018, article 17, 24 pages.
[Author manuscript](https://arxiv.org/abs/1807.00515),
[publisher DOI](https://doi.org/10.1145/3105906).

- Distinguishes behavioural repair from runtime/state repair and surveys the
  oracles and operators used to define repair tasks.
- Supports defining precisely what the project's tests establish about a patch.
- Limit: a pre-LLM survey cannot establish the performance of current coding agents.

### `gazzola2019survey`

Luca Gazzola, Daniela Micucci and Leonardo Mariani, *Automatic Software Repair:
A Survey*, IEEE Transactions on Software Engineering 45(1), 34-67, 2019.
[Author institution's publisher-version record](https://boa.unimib.it/handle/10281/184798),
[DOI](https://doi.org/10.1109/TSE.2017.2755013).

- Synthesises 108 papers and compares repair approaches, empirical evidence and
  open challenges, including generate-and-validate and semantics-driven repair.
- Provides a historical framework for discussing candidate generation and validation
  as separate responsibilities.
- Limit: this is a taxonomy and synthesis, not an experimental result for yeCoding.

### `legoues2012genprog`

Claire Le Goues, ThanhVu Nguyen, Stephanie Forrest and Westley Weimer,
*GenProg: A Generic Method for Automatic Software Repair*, IEEE Transactions on
Software Engineering 38(1), 54-72, 2012.
[IEEE abstract](https://ieeexplore.ieee.org/abstract/document/6035728),
[author PDF](https://web.eecs.umich.edu/~weimerw/p/weimer-tse2012-genprog.pdf),
[DOI](https://doi.org/10.1109/TSE.2011.104).

- Uses existing tests to encode the observed defect and required functionality
  while genetic programming searches for candidate program variants.
- Supports the continuity between classical generate-and-validate repair and an
  LLM generator controlled by executable acceptance.
- Limit: its C-program search algorithm and evaluation do not provide an LLM or
  Python-agent baseline; passing the input suite is not a general proof.

### `legoues2015manybugs`

Claire Le Goues, Neal Holtschulte, Edward K. Smith, Yuriy Brun, Premkumar Devanbu,
Stephanie Forrest and Westley Weimer, *The ManyBugs and IntroClass Benchmarks
for Automated Repair of C Programs*, IEEE Transactions on Software Engineering
41(12), 1236-1256, 2015.
[Author benchmark site and citation](https://people.cs.umass.edu/~brun/repairbenchmarks/),
[author manuscript](https://www.cs.umd.edu/~tedks/papers/2015-manybugs-and-introclass.pdf),
[DOI](https://doi.org/10.1109/TSE.2015.2454513).

- Establishes reproducible and comparative repair benchmarks with defective
  programs, test suites and documented benchmark-quality requirements.
- Supports pinned source states, reproducible baselines and consistent comparison
  conditions in the present evaluation.
- Limit: neither benchmark is the injected Python corpus used in this dissertation.

### `chen2021sequencer`

Zimin Chen, Steve Kommrusch, Michele Tufano, Louis-Noel Pouchet, Denys Poshyvanyk
and Martin Monperrus, *SequenceR: Sequence-to-Sequence Learning for End-to-End
Program Repair*, IEEE Transactions on Software Engineering, 2021 issue year
(2019 early access).
[Author manuscript](https://arxiv.org/abs/1901.01808),
[author artefact](https://github.com/ASSERT-KTH/sequencer),
[DOI](https://doi.org/10.1109/TSE.2019.2940179).

- Learns one-line repairs using sequence-to-sequence learning, a copy mechanism
  and selected source context.
- Its artefact separates compilable, test-passing and human-patch-equivalent
  candidates, supporting distinct outcome categories.
- Limit: requires a supplied buggy line and targets one-line Java replacement;
  it does not establish unrestricted repository repair or a multi-agent advantage.

### `tufano2019neuralrepair`

Michele Tufano, Cody Watson, Gabriele Bavota, Massimiliano Di Penta, Martin White
and Denys Poshyvanyk, *An Empirical Study on Learning Bug-Fixing Patches in the
Wild via Neural Machine Translation*, ACM Transactions on Software Engineering
and Methodology 28(4), 1-29, 2019.
[Author manuscript](https://arxiv.org/abs/1812.08693),
[author manuscript deposited with NSF](https://par.nsf.gov/servlets/purl/10179624),
[publisher DOI](https://doi.org/10.1145/3340544).

- Mines historical fixes and learns transformations from abstracted buggy/fixed
  code pairs using an encoder-decoder model.
- Shows why learned patch proposals and source representation are relevant to
  repair, while the candidate-generation budget affects exact-match results.
- Limit: matching a developer patch is not equivalent to proving behavioural
  correctness; this study does not evaluate repository-level tool-using agents.

### `yu2019overfitting`

Zhongxing Yu, Matias Martinez, Benjamin Danglot, Thomas Durieux and Martin
Monperrus, *Alleviating Patch Overfitting with Automatic Test Generation: A Study
of Feasibility and Effectiveness for the Nopol Repair System*, Empirical Software
Engineering 24(1), 33-67, 2019 (online 2018).
[Publisher abstract and issue citation](https://link.springer.com/article/10.1007/s10664-018-9619-4).

- Distinguishes introducing regressions from incompletely fixing the original
  defect, and studies adding generated tests to synthesis constraints.
- Finds generated tests useful against regression introduction but limited against
  incomplete fixing because of the oracle problem.
- Limit: stronger testing does not make the oracle complete; findings concern
  Nopol and Defects4J rather than the present Python workflow.

### `ye2021assessment`

He Ye, Matias Martinez and Martin Monperrus, *Automated Patch Assessment for
Program Repair at Scale*, Empirical Software Engineering 26(2), article 20, 2021.
[Publisher full text](https://link.springer.com/article/10.1007/s10664-020-09920-w).

- Assesses patches with randomly generated tests using human-written repairs as
  ground-truth oracles, on 638 patches from fourteen repair systems.
- Supports independent assessment beyond the suite that guided candidate search.
- Limit: assumes a trusted reference patch and imperfect test generation; the
  project's withheld tests do not reproduce the full RGT method or its accuracy.

### `ye2021quixbugs`

He Ye, Matias Martinez, Thomas Durieux and Martin Monperrus, *A Comprehensive
Study of Automatic Program Repair on the QuixBugs Benchmark*, Journal of Systems
and Software 171, article 110825, 2021.
[Publisher article](https://www.sciencedirect.com/science/article/pii/S0164121220302193),
[updated author manuscript](https://arxiv.org/abs/1805.03454),
[DOI](https://doi.org/10.1016/j.jss.2020.110825).

- Compares ten repair tools and investigates plausible-patch correctness using
  manual assessment and three automatic assessment techniques.
- Shows why a test-adequate outcome needs to be separated from broader correctness;
  reports false-positive issues in invariant-based assessment.
- Limit: the evaluated repair tasks are Java algorithm programs. A Python version
  of the benchmark does not make these results Python-agent measurements.

### `xuan2017nopol`

Jifeng Xuan, Matias Martinez, Favio DeMarco, Maxime Clement, Sebastian Lamelas
Marcote, Thomas Durieux, Daniel Le Berre and Martin Monperrus, *Nopol: Automatic
Repair of Conditional Statement Bugs in Java Programs*, IEEE Transactions on
Software Engineering 43(1), 34-55, 2017.
[Author manuscript](https://arxiv.org/abs/1811.04211),
[publisher DOI](https://doi.org/10.1109/TSE.2016.2560811).

- Combines angelic fix localisation, runtime state collection and SMT-based
  synthesis to repair conditional expressions and missing preconditions.
- Demonstrates how a precisely bounded fault model permits more explicit repair
  constraints than an unrestricted generation task.
- Limit: its passing/failing test input contract and Java conditional fault model
  do not establish formal correctness or general repository repair.

### `wong2016localization`

W. Eric Wong, Ruizhi Gao, Yihao Li, Rui Abreu and Franz Wotawa, *A Survey on
Software Fault Localization*, IEEE Transactions on Software Engineering 42(8),
707-740, 2016.
[IEEE publisher abstract and metadata](https://doi.org/10.1109/TSE.2016.2521368).

- Surveys the diverse techniques and evaluation concerns involved in locating
  faults from observed program failures.
- Supports treating localisation as a distinct difficulty before patch synthesis,
  and explaining limitations when task descriptions reveal defect locations.
- Limit: the repository's symbol index is navigation support, not an implemented
  spectrum-based localisation algorithm from this survey.

### `hou2024llmse`

Xinyi Hou, Yanjie Zhao, Yue Liu, Zhou Yang, Kailong Wang, Li Li, Xiapu Luo, David
Lo, John Grundy and Haoyu Wang, *Large Language Models for Software Engineering:
A Systematic Literature Review*, ACM Transactions on Software Engineering and
Methodology 33(8), article 220, 79 pages, 2024.
[Publisher text and metadata](https://doi.org/10.1145/3695988),
[author manuscript](https://nzjohng.github.io/publications/papers/tosem2024_5.pdf).

- Synthesises 395 studies spanning model choices, dataset preparation, optimisation,
  evaluation and software engineering tasks, including repair.
- Supports discussing the dependence of conclusions on task, data and evaluation
  choices, rather than a universal metric for software-agent quality.
- Limit: the search window ends in January 2024, so the survey is historical context
  and cannot establish a complete October 2026 state of the art.

### `chen2021contractrepair`

Liushan Chen, Yu Pei and Carlo A. Furia, *Contract-Based Program Repair Without
The Contracts: An Extended Study*, IEEE Transactions on Software Engineering
47(12), 2841-2857, 2021.
[Author institution record and abstract](https://research.chalmers.se/en/publication/521217),
[publisher DOI](https://doi.org/10.1109/TSE.2020.2970009).

- JAID constructs detailed state abstractions from ordinary Java source to add
  information beyond tests; the extended evaluation covers three benchmark suites.
- Supports discussing richer evidence and explicit trade-offs in test-driven repair.
- Limit: this dissertation does not implement JAID's abstractions or contracts;
  a verifier reading logs cannot be equated to semantic validation.

## Suggested Critical Synthesis

The literature can be integrated into four connected arguments without adding
thirteen isolated paper summaries:

1. Classical APR makes the oracle and fault model explicit (Monperrus, Gazzola,
   GenProg, Nopol). An LLM changes candidate generation, while executable
   acceptance remains an engineering responsibility.
2. Learned generation uses historical fixes and selected code context (Tufano,
   SequenceR), while the broader LLM literature highlights evaluation and data
   dependence (Hou). These results motivate the system but are not directly
   comparable success-rate baselines.
3. Verification must distinguish passing available tests from broader correctness
   (Yu, Ye assessment, Ye QuixBugs, Chen contract repair). Independent checks add
   evidence, but incomplete oracles and domain-specific methods limit what can be
   concluded. Model approval should be described as review, not proof.
4. Reproducible benchmarks and localisation assumptions shape validity (ManyBugs,
   Wong). The injected Python task corpus answers a narrower question than
   historical issues or large multilingual benchmarks.

Do not turn these design motivations into empirical claims that more agents,
more context, or more tests necessarily improve the present implementation.

## Ready-to-Use BibTeX

The entries below deliberately omit article numbers unless needed to identify
an article without a normal page range. DOI fields are verified. The two
qualified title/date cases above remain documented.

```bibtex
@article{monperrus2018repair,
  author = {Monperrus, Martin},
  title = {Automatic Software Repair: A Bibliography},
  journal = {ACM Computing Surveys},
  year = {2018},
  volume = {51},
  number = {1},
  pages = {17:1--17:24},
  doi = {10.1145/3105906},
  url = {https://arxiv.org/abs/1807.00515}
}
@article{gazzola2019survey,
  author = {Gazzola, Luca and Micucci, Daniela and Mariani, Leonardo},
  title = {Automatic Software Repair: A Survey},
  journal = {IEEE Transactions on Software Engineering},
  year = {2019},
  volume = {45},
  number = {1},
  pages = {34--67},
  doi = {10.1109/TSE.2017.2755013},
  url = {https://boa.unimib.it/handle/10281/184798}
}
@article{legoues2012genprog,
  author = {Le Goues, Claire and Nguyen, ThanhVu and Forrest, Stephanie and Weimer, Westley},
  title = {{GenProg}: A Generic Method for Automatic Software Repair},
  journal = {IEEE Transactions on Software Engineering},
  year = {2012},
  volume = {38},
  number = {1},
  pages = {54--72},
  doi = {10.1109/TSE.2011.104}
}
@article{legoues2015manybugs,
  author = {Le Goues, Claire and Holtschulte, Neal and Smith, Edward K. and Brun, Yuriy and Devanbu, Premkumar and Forrest, Stephanie and Weimer, Westley},
  title = {The {ManyBugs} and {IntroClass} Benchmarks for Automated Repair of {C} Programs},
  journal = {IEEE Transactions on Software Engineering},
  year = {2015},
  volume = {41},
  number = {12},
  pages = {1236--1256},
  doi = {10.1109/TSE.2015.2454513},
  url = {https://people.cs.umass.edu/~brun/repairbenchmarks/}
}
@article{chen2021sequencer,
  author = {Chen, Zimin and Kommrusch, Steve and Tufano, Michele and Pouchet, Louis-No{\"e}l and Poshyvanyk, Denys and Monperrus, Martin},
  title = {{SequenceR}: Sequence-to-Sequence Learning for End-to-End Program Repair},
  journal = {IEEE Transactions on Software Engineering},
  year = {2021},
  doi = {10.1109/TSE.2019.2940179},
  url = {https://arxiv.org/abs/1901.01808}
}
@article{tufano2019neuralrepair,
  author = {Tufano, Michele and Watson, Cody and Bavota, Gabriele and Di Penta, Massimiliano and White, Martin and Poshyvanyk, Denys},
  title = {An Empirical Study on Learning Bug-Fixing Patches in the Wild via Neural Machine Translation},
  journal = {ACM Transactions on Software Engineering and Methodology},
  year = {2019},
  volume = {28},
  number = {4},
  pages = {1--29},
  doi = {10.1145/3340544},
  url = {https://arxiv.org/abs/1812.08693}
}
@article{yu2019overfitting,
  author = {Yu, Zhongxing and Martinez, Matias and Danglot, Benjamin and Durieux, Thomas and Monperrus, Martin},
  title = {Alleviating Patch Overfitting with Automatic Test Generation: A Study of Feasibility and Effectiveness for the {Nopol} Repair System},
  journal = {Empirical Software Engineering},
  year = {2019},
  volume = {24},
  number = {1},
  pages = {33--67},
  doi = {10.1007/s10664-018-9619-4}
}
@article{ye2021assessment,
  author = {Ye, He and Martinez, Matias and Monperrus, Martin},
  title = {Automated Patch Assessment for Program Repair at Scale},
  journal = {Empirical Software Engineering},
  year = {2021},
  volume = {26},
  number = {2},
  pages = {20},
  doi = {10.1007/s10664-020-09920-w},
  note = {Article 20}
}
@article{ye2021quixbugs,
  author = {Ye, He and Martinez, Matias and Durieux, Thomas and Monperrus, Martin},
  title = {A Comprehensive Study of Automatic Program Repair on the {QuixBugs} Benchmark},
  journal = {Journal of Systems and Software},
  year = {2021},
  volume = {171},
  pages = {110825},
  doi = {10.1016/j.jss.2020.110825}
}
@article{xuan2017nopol,
  author = {Xuan, Jifeng and Martinez, Matias and DeMarco, Favio and Cl{\'e}ment, Maxime and Lamelas Marcote, Sebastian and Durieux, Thomas and Le Berre, Daniel and Monperrus, Martin},
  title = {{Nopol}: Automatic Repair of Conditional Statement Bugs in {Java} Programs},
  journal = {IEEE Transactions on Software Engineering},
  year = {2017},
  volume = {43},
  number = {1},
  pages = {34--55},
  doi = {10.1109/TSE.2016.2560811},
  url = {https://arxiv.org/abs/1811.04211}
}
@article{wong2016localization,
  author = {Wong, W. Eric and Gao, Ruizhi and Li, Yihao and Abreu, Rui and Wotawa, Franz},
  title = {A Survey on Software Fault Localization},
  journal = {IEEE Transactions on Software Engineering},
  year = {2016},
  volume = {42},
  number = {8},
  pages = {707--740},
  doi = {10.1109/TSE.2016.2521368}
}
@article{hou2024llmse,
  author = {Hou, Xinyi and Zhao, Yanjie and Liu, Yue and Yang, Zhou and Wang, Kailong and Li, Li and Luo, Xiapu and Lo, David and Grundy, John and Wang, Haoyu},
  title = {Large Language Models for Software Engineering: A Systematic Literature Review},
  journal = {ACM Transactions on Software Engineering and Methodology},
  year = {2024},
  volume = {33},
  number = {8},
  pages = {220:1--220:79},
  doi = {10.1145/3695988}
}
@article{chen2021contractrepair,
  author = {Chen, Liushan and Pei, Yu and Furia, Carlo A.},
  title = {Contract-Based Program Repair Without the Contracts: An Extended Study},
  journal = {IEEE Transactions on Software Engineering},
  year = {2021},
  volume = {47},
  number = {12},
  pages = {2841--2857},
  doi = {10.1109/TSE.2020.2970009},
  url = {https://research.chalmers.se/en/publication/521217}
}
```

## Sources Not Counted as Journal Additions

- *A Systematic Literature Review on Large Language Models for Automated Program
  Repair*, Zhang et al., arXiv:2405.01466: the author preprint is authentic, but a
  journal version was not established by this audit. Do not label it TOSEM solely
  from a third-party search snippet.
- *The Patch Overfitting Problem in Automated Program Repair: Practical Magnitude
  and a Baseline for Realistic Benchmarking*, Petke et al., 2024: the
  [author institutional record](https://discovery.ucl.ac.uk/id/eprint/10192372/)
  explicitly identifies FSE Companion proceedings, not a journal. Useful as a
  counterpoint on assessment overhead if more conference citations are wanted.
- *Toward Effective LLM-Based Automated Program Repair*, JSS volume 243: although
  indexed online, the displayed issue date is January 2027. It is unnecessary for
  the present 26 October 2026 report revision and was not used.

## Follow-Up: Complete Journal Pagination

Checked again on 26 October 2026 in response to the final report's requirement
for journal volume and page fields. This section supersedes the earlier
SequenceR pagination qualification and the unprefixed Tufano page range.

### SequenceR Resolved Through Its First Author's Thesis

The [KTH thesis PDF's List of Papers](https://www.diva-portal.org/smash/get/diva2%3A1812919/FULLTEXT01.pdf)
lists SequenceR among the papers included in the thesis, with first author
Zimin Chen highlighted, and explicitly supplies:

> IEEE Transactions on Software Engineering, vol. 47, no. 9, pp. 1943-1959,
> 1 Sept. 2021, doi: 10.1109/TSE.2019.2940179.

This is an author-owned primary bibliographic statement, rather than a third-party
index. Its search-indexed text was readable; direct PDF retrieval timed out
during this audit. The separately accessible author article and artefact remain
the sources for the research claims. These final issue fields may now be added:

```bibtex
  year = {2021},
  volume = {47},
  number = {9},
  pages = {1943--1959},
```

The author-maintained early-access
[BibTeX record](https://www.monperrus.net/martin/bibtexbrowser.php?bib=monperrus.bib&key=1901.01808)
continues to omit pagination and use 2019. This explains the discrepancy with
the final issue citation; it is not a second paper.

### Tufano Article Number Resolved Through a Coauthor's Page

[Coauthor Martin White's William & Mary publication list](https://www.cs.wm.edu/~mgwhite/)
explicitly gives the journal article's pages as `19:1-19:29`. This author-owned
record supports replacing `pages = {1--29}` with:

```bibtex
  pages = {19:1--19:29},
```

The verified publisher-deposited volume/issue/year remain 28(4), 2019.

### Optional Modern Journal Alternative

Replacement is no longer necessary to obtain complete SequenceR pagination.
If the literature discussion needs a newer example of learned repair rather
than another historical method, the following additional source has complete
metadata verified on the
[IEEE publisher page](https://ieeexplore.ieee.org/document/11039501/)
and the publisher-deposited Crossref record. It is not included in the original
22-source count.

Silva, Fang and Monperrus's RepairLLaMA studies repair-specific code
representations and parameter-efficient model adaptation. It evaluates Java
bugs requiring changes inside a single function, including multiple locations.
It supports discussing input representation as a consequential design choice
and fine-tuning as a different research route from orchestration. Its reported
outcomes are not directly comparable to the dissertation's Python tasks, and
the dissertation does not train adapters or reproduce this method.
[Author manuscript](https://arxiv.org/pdf/2312.15698),
[author replication artefact](https://github.com/ASSERT-KTH/repairllama).

```bibtex
@article{silva2025repairllama,
  author = {Silva, Andr{\'e} and Fang, Sen and Monperrus, Martin},
  title = {{RepairLLaMA}: Efficient Representations and Fine-Tuned Adapters for Program Repair},
  journal = {IEEE Transactions on Software Engineering},
  year = {2025},
  volume = {51},
  number = {8},
  pages = {2366--2380},
  doi = {10.1109/TSE.2025.3581062},
  url = {https://arxiv.org/abs/2312.15698}
}
```

## Follow-Up: Journal Source for Container Isolation

The report guidance's preference against internet sources can be met by citing
the following journal survey for the architectural argument, while describing
the actual Docker flags and resource values as details of this project's
implementation and verifying those details in its code and tests.

Sari Sultan, Imtiaz Ahmad and Tassos Dimitriou, *Container Security: Issues,
Challenges, and the Road Ahead*, IEEE Access 7, 52976-52996, 2019.
DOI: [10.1109/ACCESS.2019.2911732](https://doi.org/10.1109/ACCESS.2019.2911732).

Primary metadata and abstract are available in the
[authors' Kuwait University research record](https://pure.ku.edu.kw/en/publications/container-security-issues-challenges-and-the-road-ahead/).
The publisher-deposited Crossref record independently confirms all three authors,
title, volume 7, pages 52976-52996 and year 2019. IEEE Access uses a continuous
volume here; no issue number is needed. The institutional record's `8693491` is
the IEEE document identifier; retain normal page numbers in the citation.

The article's abstract categorises host/container threat boundaries and identifies
namespaces, control groups, capabilities, seccomp and Linux security modules as
important software protection mechanisms. Its introduction explains that Linux
containers share the operating-system kernel, and its control-group discussion
covers accounting and constraining resource consumption. These mechanisms should
be described as partial, configured controls: the paper does not support calling
the repair environment a complete security boundary or claiming immunity to
container escape. Its accepted article text was readable in the
[author manuscript rendering](https://www.researchgate.net/publication/332482728_Container_Security_Issues_Challenges_and_the_Road_Ahead);
the public IEEE endpoint presented a JavaScript verification page during this
audit. Research claims come from the article itself and the institutional
abstract, not comments or summaries around that manuscript.

Suggested paraphrase for the dissertation:

Linux container isolation depends on several host-kernel mechanisms, including
namespaces, control groups and capability restrictions. Because containers
share the kernel, these mechanisms provide configured constraints rather than
the separation of an independent guest kernel. The repair runner therefore
combines restricted execution with explicit resource budgets and records the
limits of that arrangement.

Suggested citation placement: cite `sultan2019containers` after the first two
sentences. Describe exact CLI flags, configured values and observed cleanup
behaviour separately as this project's implementation and test evidence. Do not
attribute current Docker flag syntax, defaults or the security of yeCoding to
this 2019 survey.

```bibtex
@article{sultan2019containers,
  author = {Sultan, Sari and Ahmad, Imtiaz and Dimitriou, Tassos},
  title = {Container Security: Issues, Challenges, and the Road Ahead},
  journal = {IEEE Access},
  year = {2019},
  volume = {7},
  pages = {52976--52996},
  doi = {10.1109/ACCESS.2019.2911732}
}
```

If the optional RepairLLaMA article is also used, replacing both Docker web
documents with this one article yields 22 academic references: sixteen journal
articles and six conference papers. The journal survey does not require adding
the institutional metadata page or manuscript-hosting page as separate website
entries in the dissertation bibliography.
