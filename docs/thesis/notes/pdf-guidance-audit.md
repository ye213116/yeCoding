# Final-Report PDF Requirements: Revision Audit

> The visual-evidence revision supersedes the measured-output figures and hashes below. See [the latest revision record](visual-evidence-refresh.md) and `latex/build/pdf-audit.json` for the current PDF. The following text is retained as the earlier formatting baseline, not a current count.

Date: 26 October 2026, Asia/Shanghai. Branch: `main`. Full HEAD: `b90335dbe1e739b2092c846aec59983bfa15ce04`. The workspace includes uncommitted implementation and manuscript files; HEAD is background provenance rather than a complete implementation identifier.

## Authoritative requirements

The user supplied `C:\Users\zyh\Downloads\Instructions on Project reports 22Feb16.pdf`, read at `/mnt/c/Users/zyh/Downloads/Instructions on Project reports 22Feb16.pdf`. All four pages were extracted and reviewed. SHA256: `3d1be9a92c239e9dc557d29da0d860a90ac94235dab63543feef9b82c04be03a`.

This PDF supersedes the earlier `reports.tex` layout where requirements differ. Its requirements are recorded in `latex/report-requirements.json`: 11 or 12 point permitted fonts, 1.5 spacing, left margin at least 25 mm and other margins at least 20 mm; cover, abstract, acknowledgements, contents and figure/table lists; methods, results, discussion, conclusions, numbered citations and supporting appendices.

The PDF limits BEng reports to 30-40 counted pages and twenty figures. Its length interval begins after Contents and ends before References. The student subsequently confirmed BEng; the specific programme name remains unspecified. BEng page/figure limits are enforced, while word counts are informational. The separate MEng word cap is not imposed on this report.

## Changes

- Applied A4, 12-point Times, 1.5 line spacing, 25.4 mm left margin and 20 mm other margins. Compiler-log measurements are checked, not merely source declarations.
- Added Acknowledgements, List of Figures and List of Tables in the required front-matter order. Acknowledgements remains an explicit author placeholder, without invented contributors or funding.
- Condensed repetitive background and implementation narration. Removed three redundant general-purpose diagrams while retaining five principal architecture, handoff, workspace and evaluation figures.
- Kept task definitions, essential mechanisms, experiment settings, aggregate results and limitations in the main text. Moved per-task outcomes, detailed functional traceability, full container arguments and snapshot limits to supporting appendix tables.
- Expanded the critical literature review and bibliography to twenty-two academic references: sixteen journal articles and six conference papers. Two website entries were replaced with a peer-reviewed container-security survey. Journal publication fields and first-citation numbering are checked.
- Retained the actual 24-run experiment and its negative multi-role finding. No proposed future evaluation was substituted for the archived result.
- Added checks for page/word limits, physical layout, front matter, prior references to captions, reference order, journal majority and publication metadata. Source archives contain only active figure assets and generated chapters.

Primary-source verification and qualified publication metadata are documented in [the source audit](pdf-guidance-source-audit.md). The later follow-up resolves SequenceR pagination and Tufano article numbering and verifies RepairLLaMA and container-security journal sources. Research claims are limited to what the verified papers support; no claim is made that their methods or benchmark scores were reproduced here.

## Final measured output

The final PDF contains **45 physical pages**:

| Portion | Physical pages | Count |
| --- | --- | --- |
| Cover and front matter | 1-7 | 7 |
| Introduction through Conclusions | 8-40 | 33 |
| References | 41-42 | 2 |
| Supporting appendix | 43-45 | 3 |

The PDF-guidance interval after Contents includes List of Figures (page 6), List of Tables (page 7) and the 33 main-text pages: **35 counted pages**, within 30-40. The narrower Introduction-to-References interval is also within that range.

Inclusive machine-extracted counts are **7,261 words** for the main text and **7,393 words** for the guidance interval. The method normalises ligatures and includes extractable table, caption, code, equation and page-label text. It is not a certified institutional word-counter result, but leaves substantial room below 9,000.

There are eight chapters, five main-text figures, twelve main-text tables, four appendix tables, two algorithms, five equations, twenty-two references and 57 bookmarks. All sixteen journal entries have journal, volume, year and page/article fields. All bibliography entries are cited and numbered by first use. Twenty-eight cross-reference targets resolve.

Measured body font is 12 TeX points with baseline 17.99446 points, consistent with 1.5 spacing. Measured margins are approximately 25.4 mm left and 20.0 mm top/right/bottom. The A4 page dimensions pass checks. The abstract page has 242 extracted words including heading, keywords and page marker, retaining the earlier guide's 100-250 range.

## Verification actually executed

1. `uv run --no-project --with pypandoc_binary==1.17 --with pymupdf==2.0.0 python docs/thesis/latex/build.py`: passed; regenerated English TeX, rendered active diagrams, compiled and packaged sources.
2. `uv run --no-project --with pymupdf==2.0.0 python docs/thesis/latex/audit.py`: passed against final PDF, Markdown and LaTeX-input hashes. No missing glyphs, overfull/underfull boxes, undefined references, duplicate labels, empty pages or out-of-page text.
3. `uv run --extra dev ruff check docs/thesis/latex/build.py docs/thesis/latex/audit.py docs/thesis/figures/plot_repair_results.py`: passed.
4. `uv run --extra dev ruff format --check docs/thesis/latex/build.py docs/thesis/latex/audit.py docs/thesis/figures/plot_repair_results.py`: passed for three files.
5. `git diff --check`: passed for tracked differences.
6. All 45 final pages were rendered and reviewed in two contact sheets. Cover/front matter, role table, sequence diagram, result chart and appendix were also inspected at full-page scale. Small tables were kept together, short inline identifiers were kept unbroken and an orphaned reference line was removed.
7. Source ZIP: 43 entries; CRC, SHA256, active source identity and English-text checks passed. Packaged main TeX, bibliography, requirements, audit and README match local files.

PDF SHA256: `3ac29f934113f1b01c5754e0826e2646a88d7c3ca80dd115226c48686f1a6597`.

ZIP SHA256: `52a8761563138ad247e68e3d24a4cc2178dfc18b323e31ef0eafebe3a3b09e9d`.

The final audit matched all seventeen archived implementation fingerprints and experiment source SHA256 `79f7a86c54aabe7d2d1f723e68928c8e50164670a034e59949c963a732bb7746`. Historical business tests and model runs were not rerun. Outcomes remain 8/8, 5/8 and 4/8 workflow completion; eighteen available patches passed additional checks, six runs were unassessed and seven workflows exhausted tokens.

## Remaining author input and tool limitations

Personal cover fields and genuine acknowledgements require the author. The approved original plan and submitted interim reports requested by earlier supplementary guidance were not supplied and are not invented. The current PDF's numerical constraints are met, but this does not certify academic approval, originality declarations or the student's personal reading of every source.

Tectonic still reports an encoding notice in cached third-party `lineno.sty` and ignores accessibility tags on imported diagram PDFs. The resulting document contains no replacement/missing glyphs in the text audit; PDF accessibility conformance is not claimed. Automated checks complement rather than replace the recorded visual inspection.
