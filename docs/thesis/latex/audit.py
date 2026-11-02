"""Check compiled thesis artifacts without running models or business tests.

Run in the original repository after build.py with:
uv run --no-project --with pymupdf==2.0.0 python docs/thesis/latex/audit.py
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    build = HERE / "build"
    report = json.loads((build / "build-report.json").read_text())
    pdf = build / "main.pdf"
    if not report["compiled"] or digest(pdf) != report["pdf_sha256"]:
        raise ValueError("PDF does not match the latest successful build")
    for name, expected in report["markdown_sources"].items():
        if digest(HERE.parent / name) != expected:
            raise ValueError(f"Markdown changed after build: {name}")
    for name, expected_hash in report["latex_sources"].items():
        if digest(HERE / name) != expected_hash:
            raise ValueError(f"LaTeX input changed after build: {name}")
    for name, expected_hash in report["figure_sources"].items():
        if digest(HERE / name) != expected_hash:
            raise ValueError(f"Figure changed after build: {name}")
    stats_path = HERE.parent / "notes/visual-evidence-statistics.json"
    if digest(stats_path) != report["visual_evidence_statistics_sha256"]:
        raise ValueError("Visual evidence statistics changed after build")
    visual_stats = json.loads(stats_path.read_text())
    for name, expected_hash in visual_stats["source_sha256"].items():
        if digest(ROOT / name) != expected_hash:
            raise ValueError(f"Visual evidence input changed: {name}")
    requirements = report["requirements"]

    log = (build / "main.log").read_text(errors="replace")
    fatal_patterns = {
        "missing_glyphs": r"Missing character:",
        "overfull_boxes": r"Overfull \\[hv]box",
        "undefined_references": (
            r"(?:Reference|Citation).*undefined|undefined references|undefined citations"
        ),
        "duplicate_labels": r"multiply defined|already defined",
    }
    log_checks = {name: len(re.findall(pattern, log)) for name, pattern in fatal_patterns.items()}
    if any(log_checks.values()):
        raise ValueError(f"Unresolved typesetting errors: {log_checks}")

    main_source = (HERE / "main.tex").read_text()
    chapter_paths = re.findall(r"\\input\{(chapters/[^}]+)\}", main_source)
    sources = "\n".join((HERE / name).read_text() for name in chapter_paths)
    aux = (build / "main.aux").read_text()
    labels = re.findall(r"\\newlabel\{([^}]+)\}", aux)
    if len(labels) != len(set(labels)):
        raise ValueError("Duplicate label definitions")
    refs = set(re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", sources))
    if unresolved := refs - set(labels):
        raise ValueError(f"Unresolved cross references: {unresolved}")
    counts = Counter(label.split(":")[0] for label in labels)
    expected = {"chap": 8, "fig": 7, "tab": 16, "alg": 2, "eq": 5}
    if any(counts[key] != value for key, value in expected.items()):
        raise ValueError(f"Unexpected numbered elements: {counts}")
    citations = {
        key for group in re.findall(r"\\citation\{([^}]+)\}", aux) for key in group.split(",")
    }
    bibliography = set(re.findall(r"\\bibcite\{([^}]+)\}", aux))
    entries = {entry["id"]: entry for entry in report["bibliography"]}
    if citations != bibliography or bibliography != set(entries):
        raise ValueError("Bibliography is incomplete")
    if len(bibliography) < requirements["recommended_references_min"]:
        raise ValueError("Bibliography falls below the guidance's recommended coverage")
    journals = [entry for entry in entries.values() if entry["type"] == "article-journal"]
    if len(journals) <= len(entries) / 2:
        raise ValueError("Journal articles do not form the majority of references")
    for entry in journals:
        if not all(entry.get(key) for key in ("container-title", "volume", "page", "issued")):
            raise ValueError(f"Incomplete journal publication metadata: {entry['id']}")
    citation_order = list(
        dict.fromkeys(
            key for group in re.findall(r"\\citation\{([^}]+)\}", aux) for key in group.split(",")
        )
    )
    if citation_order != re.findall(r"\\bibcite\{([^}]+)\}", aux):
        raise ValueError("References are not numbered in first-citation order")
    for label in labels:
        if label.startswith(("fig:", "tab:")):
            first_reference = sources.find(r"\ref{" + label + "}")
            caption_label = sources.find(r"\label{" + label + "}")
            if first_reference < 0 or first_reference > caption_label:
                raise ValueError(f"Figure/table not introduced before its caption: {label}")

    layout_values = {
        name: float(value) for name, value in re.findall(r"Report([A-Za-z]+)=([0-9.]+)(?:pt)?", log)
    }
    if not 10.8 <= layout_values["Font"] <= 12.1:
        raise ValueError("Body font is not 11 or 12 points")
    if abs(layout_values["Baseline"] / layout_values["Font"] - 1.5) > 0.03:
        raise ValueError("Body baseline does not provide 1.5 line spacing")
    tex_points_per_mm = 72.27 / 25.4
    actual_margins = {
        "left": layout_values["Left"] / tex_points_per_mm,
        "top": layout_values["Top"] / tex_points_per_mm,
        "right": (layout_values["PaperWidth"] - layout_values["Left"] - layout_values["TextWidth"])
        / tex_points_per_mm,
        "bottom": (
            layout_values["PaperHeight"] - layout_values["Top"] - layout_values["TextHeight"]
        )
        / tex_points_per_mm,
    }
    if any(
        actual_margins[side] + 0.05 < limit for side, limit in requirements["margins_mm"].items()
    ):
        raise ValueError(f"Insufficient margins: {actual_margins}")

    with pymupdf.open(pdf) as document:
        pages = len(document)
        bookmarks = len(document.get_toc())
        text = "\n".join(page.get_text() for page in document)
        if "\ufffd" in text or "??" in text:
            raise ValueError("Unexpected replacement character or unresolved marker in PDF text")
        if not all(value in text for value in ("Abstract", "Contents", "Discussion", "References")):
            raise ValueError("Expected manuscript text missing")
        if re.search(r"[\u3400-\u9fff]", text):
            raise ValueError("Chinese text remains in the English PDF")
        if report.get("language") != "en":
            raise ValueError("Unexpected manuscript language")
        chapter_starts = {title: page for level, title, page in document.get_toc() if level == 1}
        front_starts = {}
        for number, page in enumerate(document, 1):
            lines = page.get_text().splitlines()
            if lines and lines[0] in requirements["required_front_matter"]:
                front_starts.setdefault(lines[0], number)
        if list(front_starts) != requirements["required_front_matter"]:
            raise ValueError(f"Missing or misordered front matter: {front_starts}")
        intro_page, references_page = chapter_starts["Introduction"], chapter_starts["References"]
        body_pages = references_page - intro_page
        guidance_pages = references_page - front_starts["List of Figures"]
        if (
            not requirements["beng_body_pages_min"]
            <= body_pages
            <= guidance_pages
            <= requirements["beng_body_pages_max"]
        ):
            raise ValueError(
                f"BEng page count outside 30-40: body={body_pages}, "
                f"end-of-contents={guidance_pages}"
            )
        body_text = "\n".join(
            page.get_text() for page in document[intro_page - 1 : references_page - 1]
        )
        guidance_text = "\n".join(
            page.get_text()
            for page in document[front_starts["List of Figures"] - 1 : references_page - 1]
        )
        word_pattern = r"\b[\w]+(?:['_-][\w]+)*\b"
        body_words = len(re.findall(word_pattern, unicodedata.normalize("NFKC", body_text)))
        guidance_words = len(re.findall(word_pattern, unicodedata.normalize("NFKC", guidance_text)))
        if counts["fig"] > requirements["beng_figures_max"]:
            raise ValueError("Too many figures for BEng guidance")
        outside = []
        empty = []
        for number, page in enumerate(document, 1):
            if abs(page.rect.width - 595.276) > 1 or abs(page.rect.height - 841.89) > 1:
                raise ValueError(f"Non-A4 page: {number}")
            if not page.get_text().strip():
                empty.append(number)
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        x0, y0, x1, y1 = span["bbox"]
                        if (
                            min(x0, y0) < -1
                            or x1 > page.rect.width + 1
                            or y1 > page.rect.height + 1
                        ):
                            outside.append({"page": number, "text": span["text"]})
        if outside or empty:
            raise ValueError(f"PDF page bounds or empty pages: {outside}, {empty}")

    implementation = json.loads((ROOT / "eval/evidence/repair-implementation.json").read_text())
    for name, expected_hash in implementation["files"].items():
        if digest(ROOT / name) != expected_hash:
            raise ValueError(f"Implementation evidence changed: {name}")
    statistics = json.loads((HERE.parent / "notes/ch06-statistics.json").read_text())
    if digest(ROOT / statistics["source"]) != statistics["source_sha256"]:
        raise ValueError("Experiment source changed")

    audit = {
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "branch": subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True
        ).strip(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "pdf_sha256": digest(pdf),
        "pages": pages,
        "bookmarks": bookmarks,
        "numbered_elements": {key: counts[key] for key in ("chap", "fig", "tab", "alg", "eq")},
        "bibliography_entries": len(bibliography),
        "journal_articles": len(journals),
        "guidance_source": requirements["source"],
        "guidance_sha256": requirements["source_sha256"],
        "body_pages": body_pages,
        "end_of_contents_to_references_pages": guidance_pages,
        "body_words_including_tables_captions_code": body_words,
        "end_of_contents_to_references_words": guidance_words,
        "front_matter_pages": front_starts,
        "layout_evidence": layout_values,
        "margins_mm": actual_margins,
        "cross_reference_targets": len(refs),
        "log_checks": log_checks,
        "underfull_boxes": len(re.findall(r"Underfull \\[hv]box", log)),
        "text_outside_page": outside,
        "empty_pages": empty,
        "implementation_hashes_matched": len(implementation["files"]),
        "experiment_source_sha256": statistics["source_sha256"],
        "fresh_evidence_manifest": visual_stats["fresh_manifest"],
        "role_usage_reconciled_runs": visual_stats["role_usage_reconciled_runs"],
        "active_figure_hashes_matched": len(report["figure_sources"]),
        "limitations": [
            "Automated text and log checks do not replace visual review of rendered figures.",
            "BEng confirmed: 30-40 pages and <=20 figures enforced; word count is informational.",
            "Personal cover fields and acknowledgements remain to be completed by the author.",
            "An approved original project plan and submitted interim reports were not supplied.",
            "Model runs remain archived; fresh retrieval and Docker fixture checks are separate.",
        ],
    }
    (build / "pdf-audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
