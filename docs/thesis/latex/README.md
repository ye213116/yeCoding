# English Final-Year Dissertation

The authoritative formatting and length requirements for this revision are **Instructions on Project reports 22Feb16.pdf**, supplied by the user from Windows Downloads. Its SHA256 is recorded in report-requirements.json. The earlier reports.tex is supplementary guidance; the PDF takes precedence.

Open the [compiled dissertation](build/main.pdf), edit [main.tex](main.tex), or use the [complete source archive](../thesis-latex-source.zip). This is the final dissertation, not the preliminary report.

## Requirements Applied

- A4, 12-point Times, 1.5 line spacing; left margin 25.4 mm, other margins 20 mm.
- Cover, Abstract, Acknowledgements, Contents, List of Figures and List of Tables.
- Introduction/literature review, specification, methods/design/implementation, results, discussion and conclusions.
- Numerical citations in first-use order; no duplicate bibliography entries.
- Figure captions below, table captions above, with prior references in the text.
- References before supporting appendices; essential methods and findings remain in the body.
- Seven main-text figures and sixteen tables, including four supporting appendix tables.
- Twenty-two cited academic sources: sixteen journal articles and six conference papers. Journal entries identify publication, volume and pages or article number; online access is not substituted for publication metadata. Container principles cite a journal survey, while actual command flags are documented as implementation details.

The literature review was expanded around repair oracles, overfitting, independent assessment, learned generation, benchmarks and localisation. The visual-evidence revision retains one architecture diagram and replaces repetitive handoff, workspace and evaluation flowcharts with empirical plots: context-budget sensitivity, per-task outcomes, paired token costs, role allocations, actual execution traces and a concrete patch. All have associated analysis and input fingerprints. Functional traceability and execution limits remain in the appendix.

## Page and Word Counts

The student has confirmed BEng. The specific programme name remains to be supplied. The PDF specifies 30-40 BEng pages and at most twenty figures, with length measured after Contents and before References. Its separate MEng word limit is not a requirement for this BEng report.

audit.py checks both the Introduction-to-References interval and the more conservative after-Contents interval, which includes the figure/table lists. Both must remain within 30-40 pages, with at most twenty figures. Word counts are informational and include tables, captions, code and equation text where extractable; exact figures are in build/pdf-audit.json and ../notes/pdf-guidance-audit.md. Total PDF pages include excluded front matter, references and appendices and must not be mistaken for body length.

## Sources and Artefacts

- ../en/: English Markdown, the authoritative generated-body source.
- main.tex: layout and document assembly.
- metadata.tex: project title and personal fields.
- report-requirements.json: requirements extracted from the supplied PDF.
- chapters/: generated TeX; edit Markdown before regenerating.
- references.bib: the actual cited academic sources.
- figures/: active English vector figures and Mermaid sources.
- build.py: conversion, rendering, compilation, source hashing and packaging.
- audit.py: PDF, layout, length, bibliography, reference and archived-evidence checks.
- build/: PDF, logs, manifests and audit results.

The original Chinese Markdown is retained for comparison, but is not the English build input. The source archive contains active generated chapters and figures plus English Markdown. Evidence audit and statistics regeneration require the original repository.

## Rebuild

From the repository root:

~~~bash
uv run --no-project --with pypandoc_binary==1.17 --with pymupdf==2.0.0 python docs/thesis/latex/build.py
uv run --no-project --with pymupdf==2.0.0 python docs/thesis/latex/audit.py
~~~

To rerun the model-free supplement (240 retrieval contexts and 12 Docker fixture checks), then regenerate the six empirical figures:

~~~bash
uv run python eval/run_visual_evidence.py
uv run --no-project --with matplotlib==3.11.2 python docs/thesis/figures/plot_evidence_figures.py
~~~

To regenerate chapters and diagrams without compilation:

~~~bash
uv run --no-project --with pypandoc_binary==1.17 --with pymupdf==2.0.0 python docs/thesis/latex/build.py --generate-only
~~~

Pandoc 3.9, cached Tectonic 0.17.0 and Mermaid CLI 12.0.0 are used. Set THESIS_TECTONIC or THESIS_CHROME to override tools. With a conventional TeX installation, compile generated sources from this directory:

~~~bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex
~~~

The document uses standard report, Times-family fonts, setspace, natbib and BibTeX. Mermaid rerendering requires Chromium, but existing figure PDFs can be compiled without it. No project dependency or lockfile changes are required.

## Remaining Author Information

Complete metadata.tex with the student's name, identifiers, supervisor, programme, academic year and submission date. Acknowledgements must name only actual contributors and funding; a clearly marked author placeholder is retained.

An approved original plan and submitted interim reports were not supplied and are not invented. Original diagrams and charts describe this implementation and its archived data; no third-party illustrations were copied.

The 160-test engineering result and 24 real-model runs remain historical evidence. The 26 October visual-evidence supplement freshly executes deterministic retrieval and real Docker fixture validation; it makes no new model calls. Role usage is reconstructed from archived events and reconciled against all 24 report totals. Raw supplement records are in eval/evidence/visual-refresh-20261026, and derived values and input hashes are in ../notes/visual-evidence-statistics.json. Primary-source research notes remain in ../notes/pdf-guidance-source-audit.md.
