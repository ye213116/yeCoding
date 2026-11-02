# English Dissertation and Template Audit

Historical audit of the first English adaptation. The later user-supplied PDF requirements
supersede this layout and length baseline; see [the current audit](pdf-guidance-audit.md).

Date: 26 October 2026 (Asia/Shanghai). Branch: `main`. Full Git HEAD: `b90335dbe1e739b2092c846aec59983bfa15ce04`. The implementation and manuscript include uncommitted working files; HEAD alone does not identify their complete contents.

## Scope and adaptation

The user requested changes to the final dissertation, using the engineering-report guidance in the repository-root `reports.tex`, and conversion to English. This is distinct from the earlier preliminary-report request. The preliminary report's eight-page limit has not been applied to the final dissertation.

English Markdown in `docs/thesis/en/` is now the source of the final generated TeX. The original Chinese Markdown remains available for comparison. The adaptation includes the abstract, eight chapters, supporting appendix, all diagram labels, chart labels and bibliography presentation. Discussion and Conclusions are separate chapters. Existing results, task provenance and limitations are retained without adopting the preliminary draft's proposed future experiments.

The layout uses A4, 12-point Times-family text and mathematics, 25.4 mm margins, separate cover/abstract/contents, new-page chapter starts, numbered captions and sequential numerical citations. The supplied guide permits project-specific body headings. References precedes the appendix. Personal fields are explicit placeholders in `metadata.tex`.

## Verification executed in this task

- `uv run --no-project --with matplotlib==3.11.2 python docs/thesis/figures/plot_repair_results.py --language en`: passed; recomputed existing statistics and rendered the English chart without model or Docker calls.
- `uv run --no-project --with pypandoc_binary==1.17 --with pymupdf==2.0.0 python docs/thesis/latex/build.py`: passed; generated, compiled and packaged the English dissertation.
- `uv run --no-project --with pymupdf==2.0.0 python docs/thesis/latex/audit.py`: passed against the final PDF and English source hashes.
- `uv run --extra dev ruff check docs/thesis/latex/build.py docs/thesis/latex/audit.py docs/thesis/figures/plot_repair_results.py`: passed.
- `uv run --extra dev ruff format --check docs/thesis/latex/build.py docs/thesis/latex/audit.py docs/thesis/figures/plot_repair_results.py`: passed for all three files.
- `git diff --check`: passed for tracked working-tree changes.

Final PDF: **59 pages**, 63 bookmarks, 8 numbered chapters, 8 figures, 24 tables, 2 algorithms, 5 equations and 9 bibliography entries. Forty cross-reference targets resolved. The audit found no missing glyphs, overfull boxes, undefined references, duplicate labels, empty pages, out-of-page text or Chinese characters in the PDF text.

The abstract page contains 242 extracted words including heading, keywords and page marker, within the guide's 100-250-word range. Font inspection confirms Times-compatible Nimbus Roman with main text approximately 11.96 PDF points, corresponding to 12 TeX points. Front matter begins with cover, Abstract and Contents on separate pages. The contents occupies two pages; References fits on one page.

All 59 pages were reviewed in three rendered contact sheets. Cover, abstract, architecture, role sequence, workspace flow, results chart and per-task table were also rendered at full-page scale. The role-sequence frame and diagram labels were adjusted for readable spacing, the results chart was arranged vertically, and orphaned contents/reference fragments were removed. Preview images remain local build artefacts.

The source ZIP contains 51 entries. CRC checks passed, packaged `main.tex` matches the local file, and packaged Markdown/TeX/Mermaid/bibliography text contains no Chinese characters. Only active generated chapters are packaged, excluding obsolete historical chapter files.

## Evidence consistency

The audit matched all 17 archived implementation fingerprints and the experiment-source hash. The held-out result source SHA256 is `79f7a86c54aabe7d2d1f723e68928c8e50164670a034e59949c963a732bb7746`.

The results remain 24 real-model runs on eight held-out injected defects, with workflow successes of 8, 5 and 4. Additional checks passed for 8, 5 and 5 runs, with 18 assessed patches overall and six runs unassessed because no patch was exported. All seven workflow failures exhausted the token budget. No multi-role success-rate benefit is claimed.

The reported 160 passing business tests are archived evidence, not tests rerun during this document adaptation. No models, Docker execution, product regressions, commits or pushes were performed for the adaptation.

Final PDF SHA256: `d6d592e738fdc11c98d98b369866a75b176ef37ae8d919bc365f1a047bef6fe0`.

Source ZIP SHA256: `c569bacc2ca0cc01fd24ad97a3871a2026e07c415c0d44068b07b343deb348af`.

## Remaining information and tool notices

Student name, matriculation number, UESTC number, supervisor, degree programme, academic year and submission date still require the student's information. An approved original project plan and submitted interim reports were not supplied; Appendix A states that gap instead of reconstructing an approved historical schedule. Submission-specific declarations and any additional final-report length limit require the actual institutional instructions.

Tectonic reports a UTF-8 replacement warning from the cached third-party `lineno.sty` and notices that imported PDFs have accessibility tags which it ignores. These do not correspond to missing/replacement glyphs or unresolved text in the resulting PDF; no accessibility conformance claim is made. BibTeX reports no warnings after representing undated documentation explicitly as `n.d.` and retaining the actual access dates.
