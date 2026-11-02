"""Inspect the actual Impress-rendered PDF, PPTX notes and slide geometry."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation

OUT = Path(__file__).resolve().parent
pdf = pymupdf.open(OUT / "stage1_report.pdf")
ppt = Presentation(OUT / "stage1_report.pptx")
notes_md = (OUT / "stage1_speaker_notes.md").read_text()
assert len(pdf) == len(ppt.slides) == 21
assert len(re.findall(r"^## 第 \d+ 页：", notes_md, re.M)) == 21
preview_dir = OUT / "preview"
preview_dir.mkdir(exist_ok=True)
outside = []
missing_titles = []
missing_text_lines = []
empty_notes = []
text_collisions = []
font_names = set()
thumbs = []


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


for i, (page, slide) in enumerate(zip(pdf, ppt.slides, strict=True), 1):
    text = page.get_text()
    assert len(text.strip()) > 100, (i, "blank page")
    title = [shape.text for shape in slide.shapes if shape.has_text_frame and shape.text][0]
    if compact(title) not in compact(text):
        missing_titles.append(i)
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for expected in shape.text.splitlines():
            if len(compact(expected)) > 6 and compact(expected) not in compact(text):
                missing_text_lines.append({"slide": i, "text": expected})
    if len(slide.notes_slide.notes_text_frame.text) < 120:
        empty_notes.append(i)
    spans = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                font_names.add(span["font"])
                bounds = pymupdf.Rect(span["bbox"])
                if not page.rect.contains(bounds):
                    outside.append({"slide": i, "text": span["text"], "bbox": list(bounds)})
                if span["text"].strip():
                    spans.append(span)
    # Spans may touch within one rendered line; only flag substantive two-dimensional overlap.
    for j, a in enumerate(spans):
        for b in spans[j + 1 :]:
            ra, rb = pymupdf.Rect(a["bbox"]), pymupdf.Rect(b["bbox"])
            overlap = ra & rb
            if overlap.width > 3 and overlap.height > min(ra.height, rb.height) * 0.5:
                text_collisions.append({"slide": i, "a": a["text"], "b": b["text"]})
    pix = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
    pix.save(preview_dir / f"slide-{i:02d}.png")
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    img.thumbnail((640, 360))
    thumbs.append(img)

contact = Image.new("RGB", (1920, 7 * 396), "#e3e7e8")
draw = ImageDraw.Draw(contact)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
for i, img in enumerate(thumbs):
    x, y = (i % 3) * 640, (i // 3) * 396
    contact.paste(img, (x, y + 26))
    draw.text(
        (x + 12, y + 3), f"{i + 1:02d}" + ("  BACKUP" if i >= 18 else ""), font=font, fill="#24292d"
    )
contact.save(OUT / "stage1_overview.png")
audit = json.loads((OUT / "build_audit.json").read_text())
root = OUT.parents[2]
baseline = json.loads((root / "eval/evidence/repair-implementation.json").read_text())
mismatches = [
    name
    for name, digest in baseline["files"].items()
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest
]
audit["archived_implementation"] = {
    "checked_files": len(baseline["files"]),
    "fingerprint_mismatches": mismatches,
    "business_tests_rerun": False,
}
audit["rendered_pdf"] = {
    "renderer": "LibreOffice Impress 7.3.7.2, headless, impress_pdf_Export",
    "pages": len(pdf),
    "page_size_pt": list(pdf[0].rect),
    "missing_titles": missing_titles,
    "missing_text_lines": missing_text_lines,
    "empty_notes": empty_notes,
    "out_of_bounds_spans": outside,
    "substantive_span_overlap": text_collisions,
    "font_names": sorted(font_names),
}
audit["delivery_sha256"] = {
    name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
    for name in ["stage1_report.pptx", "stage1_report.pdf", "stage1_speaker_notes.md"]
}
(OUT / "build_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(audit["rendered_pdf"], ensure_ascii=False, indent=2))
assert (
    not outside
    and not missing_titles
    and not missing_text_lines
    and not empty_notes
    and not text_collisions
    and not mismatches
)
