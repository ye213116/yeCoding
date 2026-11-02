"""Convert the English dissertation sources, render figures, and compile the thesis.

Run with uv run --no-project --with pypandoc_binary==1.17 --with pymupdf==2.0.0
python docs/thesis/latex/build.py. Build tools use user caches; product code is untouched.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pypandoc

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "en"
TABLE_WIDTHS = {
    "2-1": [0.22, 0.24, 0.25, 0.29],
    "2-2": [0.12, 0.25, 0.36, 0.27],
    "2-3": [0.23, 0.34, 0.43],
    "3-1": [0.18, 0.34, 0.48],
    "3-2": [0.14, 0.27, 0.59],
    "3-3": [0.15, 0.27, 0.58],
    "3-4": [0.10, 0.25, 0.48, 0.17],
    "4-1": [0.30, 0.49, 0.21],
    "4-2": [0.14, 0.30, 0.33, 0.23],
    "4-3": [0.20, 0.52, 0.28],
    "4-4": [0.32, 0.68],
    "4-5": [0.15, 0.43, 0.42],
    "5-1": [0.22, 0.44, 0.34],
    "5-2": [0.20, 0.48, 0.32],
    "5-3": [0.29, 0.23, 0.48],
    "5-4": [0.20, 0.50, 0.30],
    "6-1": [0.22, 0.78],
    "6-2": [0.44, 0.28, 0.28],
    "6-3": [0.17, 0.35, 0.48],
    "6-4": [0.25, 0.09, 0.17, 0.49],
    "6-5": [0.15, 0.20, 0.32, 0.33],
    "6-6": [0.16, 0.25, 0.25, 0.18, 0.16],
    "6-7": [0.17, 0.26, 0.30, 0.27],
    "6-8": [0.34, 0.22, 0.22, 0.22],
    "A-1": [0.37, 0.21, 0.21, 0.21],
    "A-2": [0.10, 0.25, 0.43, 0.22],
    "A-3": [0.22, 0.47, 0.31],
    "A-4": [0.23, 0.43, 0.34],
}
SHORT_CAPTIONS = {
    "fig:4-1": "System architecture and shared capabilities",
    "fig:5-1": "Context-budget sensitivity and coverage",
    "fig:5-2": "Concrete candidate patch and test evidence",
    "fig:6-1": "Per-task workflow and candidate outcomes",
    "fig:6-2": "Paired per-task model-token costs",
    "fig:6-3": "Model-token allocation by role",
    "fig:6-4": "Actual execution and budget trajectories",
    "tab:2-1": "Research findings and design implications",
    "tab:3-2": "Functional requirements",
    "tab:3-3": "Non-functional requirements",
    "tab:4-2": "Role contracts",
    "tab:4-4": "Run states",
    "tab:4-5": "Public entry points",
    "tab:6-1": "Experimental configuration",
    "tab:6-2": "Archived engineering checks",
    "tab:6-4": "Injected defects and split",
    "tab:6-5": "Comparison strategies",
    "tab:6-6": "Held-out repair outcomes",
    "tab:6-7": "Mean resource consumption",
    "tab:A-1": "Per-task outcomes",
    "tab:A-2": "Acceptance traceability",
    "tab:A-3": "Container arguments",
    "tab:A-4": "Snapshot limits",
}
FIGURE_KINDS: dict[str, str] = {}


def plain(node) -> str:
    if isinstance(node, list):
        return "".join(plain(n) for n in node)
    if not isinstance(node, dict):
        return ""
    kind = node.get("t")
    if kind == "Str":
        return node["c"]
    if kind in {"Space", "SoftBreak", "LineBreak"}:
        return " "
    if kind in {"Code", "Math"}:
        return node["c"][1]
    return plain(node.get("c", []))


def escaped(text: str) -> str:
    mapping = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(mapping.get(char, char) for char in text)


def raw(text: str, inline: bool = False) -> dict:
    return {"t": "RawInline" if inline else "RawBlock", "c": ["latex", text]}


def reference_inlines(node):
    if isinstance(node, list):
        result = []
        for item in node:
            if isinstance(item, dict) and item.get("t") == "Str":
                text = item["c"]
                last = 0
                for match in re.finditer(
                    r"(Figure|Table|Algorithm)([1-8A-Z]-\d+)|Chapter([1-8])", text
                ):
                    if match.start() > last:
                        result.append({"t": "Str", "c": text[last : match.start()]})
                    if match[3]:
                        value = rf"Chapter~\ref{{chap:{match[3]}}}"
                    else:
                        prefix = {"Figure": "fig", "Table": "tab", "Algorithm": "alg"}[match[1]]
                        value = match[1] + rf"~\ref{{{prefix}:{match[2]}}}"
                    result.append(raw(value, inline=True))
                    last = match.end()
                if last:
                    if last < len(text):
                        result.append({"t": "Str", "c": text[last:]})
                    continue
            result.append(reference_inlines(item))
        return result
    if not isinstance(node, dict):
        return node
    if node.get("t") == "Code":
        text = node["c"][1]
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,11}", text):
            return raw(r"\texttt{" + escaped(text) + "}", inline=True)
        if re.search(r"[\u3400-\u9fff]", text):
            return raw(r"\texttt{" + escaped(text) + "}", inline=True)
        delimiter = next(c for c in "|!+;" if c not in text)
        return raw(r"\code" + delimiter + text + delimiter, inline=True)
    if node.get("t") in {"RawInline", "RawBlock", "Math", "CodeBlock", "Header", "Cite"}:
        return node
    return {key: reference_inlines(value) if key == "c" else value for key, value in node.items()}


def find_mermaid() -> list[str]:
    if executable := shutil.which("mmdc"):
        return [executable]
    cached = (
        Path.home()
        / ".cache/yecoding-thesis-tools/mermaid/node_modules/@mermaid-js/mermaid-cli/src/cli.js"
    )
    if cached.exists():
        return ["node", str(cached)]
    candidates = sorted(
        (Path.home() / ".npm/_npx").glob("*/node_modules/@mermaid-js/mermaid-cli/src/cli.js")
    )
    for candidate in candidates:
        metadata = json.loads((candidate.parents[1] / "package.json").read_text())
        if metadata["version"] == "12.0.0":
            return ["node", str(candidate)]
    raise RuntimeError("Install @mermaid-js/mermaid-cli@12.0.0 in a user cache or put mmdc on PATH")


def find_browser() -> Path:
    if custom := os.environ.get("THESIS_CHROME"):
        return Path(custom)
    for name in ("chromium", "chromium-browser", "google-chrome"):
        if path := shutil.which(name):
            return Path(path)
    candidates = sorted(
        (Path.home() / ".cache/ms-playwright").glob("chromium-*/chrome-linux*/chrome")
    )
    candidates += sorted(
        (Path.home() / ".cache/puppeteer").glob("chrome/linux-*/chrome-linux64/chrome")
    )
    if candidates:
        return candidates[-1]
    raise RuntimeError("No Chromium found; set THESIS_CHROME to an executable")


def render_diagram(identifier: str, body: str, command: list[str], browser: Path) -> None:
    if identifier in {"5-1", "6-1"}:
        body = "%%{init: {'flowchart': {'wrappingWidth': 400}}}%%\n" + body
    elif identifier == "4-1":
        body = (
            "%%{init: {'themeVariables': {'fontSize': '24px'}, "
            "'flowchart': {'nodeSpacing': 10, 'rankSpacing': 18, "
            "'padding': 6, 'wrappingWidth': 125}}}%%\n" + body
        )
    folder = HERE / "figures"
    folder.mkdir(exist_ok=True)
    input_path = folder / f"fig-{identifier}.mmd"
    input_path.write_text(body + "\n")
    config = HERE / "build/puppeteer.json"
    config.parent.mkdir(exist_ok=True)
    config.write_text(json.dumps({"executablePath": str(browser), "args": ["--no-sandbox"]}))
    signature = hashlib.sha256(
        (body + (HERE / "mermaid-config.json").read_text()).encode()
    ).hexdigest()
    marker = folder / f"fig-{identifier}.sha256"
    if (
        marker.exists()
        and marker.read_text() == signature
        and all((folder / f"fig-{identifier}.{suffix}").exists() for suffix in ("svg", "pdf"))
    ):
        return
    for suffix in ("svg", "pdf"):
        target = folder / f"fig-{identifier}.{suffix}"
        subprocess.run(
            command
            + [
                "-i",
                str(input_path),
                "-o",
                str(target),
                "-c",
                str(HERE / "mermaid-config.json"),
                "-p",
                str(config),
                "-q",
            ],
            check=True,
            timeout=90,
        )
    marker.write_text(signature)


def figure(identifier: str, caption: str) -> dict:
    height = "0.85"
    return raw(
        "\n".join(
            [
                r"\begin{figure}[htbp]",
                r"\centering",
                rf"\includegraphics[width=\linewidth,height={height}\textheight,keepaspectratio]{{figures/fig-{identifier}.pdf}}",
                rf"\caption[{escaped(SHORT_CAPTIONS[f'fig:{identifier}'])}]"
                rf"{{{escaped(caption)}}}\label{{fig:{identifier}}}",
                r"\end{figure}",
            ]
        )
    )


def convert(path: Path, command: list[str], browser: Path, counts: dict) -> None:
    document = json.loads(
        pypandoc.convert_text(
            path.read_text(), "json", format="markdown-implicit_figures+tex_math_single_backslash"
        )
    )
    source = document["blocks"]
    output = []
    chapter = int(path.name[:2]) if path.name[:2].isdigit() else None
    index = 0
    equation = 0
    while index < len(source):
        block = copy.deepcopy(source[index])
        text = plain(block) if block["t"] in {"Para", "Plain"} else ""
        if block["t"] == "Header":
            level, attr, inlines = block["c"]
            title = plain(inlines)
            if level == 1:
                if chapter == 0:
                    index += 1
                    continue
                title = re.sub(r"^Chapter\s+\d+\s+", "", title)
                attr[0] = f"chap:{chapter}" if chapter else "app:artefacts"
            elif chapter is not None:
                match = re.match(r"^(\d+(?:\.\d+)+)\s+(.+)$", title)
                if not match:
                    raise ValueError(f"Unnumbered heading in {path.name}: {title}")
                attr[0], title = f"sec:{match[1]}", match[2]
            block["c"] = [level, attr, [{"t": "Str", "c": title}]]
        elif block["t"] == "CodeBlock":
            classes, body = block["c"][0][1], block["c"][1]
            if "mermaid" in classes:
                caption = plain(source[index + 1])
                match = re.fullmatch(r"Figure(\d+-\d+)\s+(.+)", caption)
                if not match:
                    raise ValueError(f"Missing figure caption in {path.name}")
                render_diagram(match[1], body, command, browser)
                FIGURE_KINDS[match[1]] = "mermaid"
                block = figure(match[1], match[2])
                counts["figures"] += 1
                index += 1
            else:
                block = raw(
                    "\\begin{Verbatim}[fontsize=\\normalsize,breaklines=true,breakanywhere=true,frame=single,framesep=2mm]\n"
                    + body
                    + "\n\\end{Verbatim}"
                )
        elif (
            (match := re.fullmatch(r"Table([1-8A-Z]-\d+)\s+(.+)", text))
            and index + 1 < len(source)
            and source[index + 1]["t"] == "Table"
        ):
            index += 1
            block = copy.deepcopy(source[index])
            if block["t"] != "Table":
                raise ValueError(f"Missing table after {match[0]}")
            block["c"][0][0] = f"tab:{match[1]}"
            block["c"][1] = [
                [{"t": "Str", "c": SHORT_CAPTIONS[f"tab:{match[1]}"]}],
                [{"t": "Plain", "c": [{"t": "Str", "c": match[2]}]}],
            ]
            widths = TABLE_WIDTHS[match[1]]
            if len(widths) != len(block["c"][2]):
                raise ValueError(f"Incorrect column widths for {match[0]}")
            for spec, width in zip(block["c"][2], widths, strict=True):
                spec[1] = {"t": "ColWidth", "c": width}
            if match[1] in {"4-2", "4-5", "6-5", "6-6", "6-7"}:
                output.append(raw(r"\needspace{14\baselineskip}"))
            counts["tables"] += 1
        elif match := re.fullmatch(r"Algorithm(\d+-\d+)\s+(.+)", text):
            block = raw(
                r"\needspace{5\baselineskip}\refstepcounter{thesisalgorithm}"
                + rf"\label{{alg:{match[1]}}}"
                + "\n"
                + rf"\noindent\textbf{{Algorithm \thethesisalgorithm\quad {escaped(match[2])}}}"
                + r"\par\nopagebreak"
            )
            counts["algorithms"] += 1
        elif block["t"] == "Para" and len(block["c"]) == 1 and block["c"][0]["t"] == "Image":
            caption = plain(source[index + 1])
            match = re.fullmatch(r"Figure(\d+-\d+)\s+(.+)", caption)
            if not match:
                raise ValueError(f"Missing image caption in {path.name}")
            original = (path.parent / block["c"][0]["c"][2][0]).with_suffix(".pdf")
            shutil.copyfile(original, HERE / f"figures/fig-{match[1]}.pdf")
            if original.with_suffix(".svg").exists():
                shutil.copyfile(original.with_suffix(".svg"), HERE / f"figures/fig-{match[1]}.svg")
            FIGURE_KINDS[match[1]] = "image"
            block = figure(match[1], match[2])
            counts["figures"] += 1
            index += 1
        elif (
            block["t"] == "Para"
            and len(block["c"]) == 1
            and block["c"][0]["t"] == "Math"
            and block["c"][0]["c"][0]["t"] == "DisplayMath"
        ):
            equation += 1
            value = block["c"][0]["c"][1].strip()
            block = raw(
                "\\begin{equation}\n"
                + value
                + rf"\label{{eq:{chapter}-{equation}}}"
                + "\n\\end{equation}"
            )
            counts["equations"] += 1
        output.append(reference_inlines(block))
        index += 1
    document["blocks"] = output
    latex = pypandoc.convert_text(
        json.dumps(document),
        "latex",
        format="json",
        extra_args=["--top-level-division=chapter", "--number-sections", "--natbib", "--wrap=none"],
    )
    (HERE / "chapters" / f"{path.stem}.tex").write_text(
        "% Generated from en/" + path.name + "; edit Markdown, then rebuild.\n" + latex
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate-only", action="store_true")
    args = parser.parse_args()
    (HERE / "chapters").mkdir(exist_ok=True)
    (HERE / "figures").mkdir(exist_ok=True)
    (HERE / "build").mkdir(exist_ok=True)
    command, browser = find_mermaid(), find_browser()
    inputs = sorted(SOURCE.glob("0[0-8]-*.md")) + [SOURCE / "appendix-artefacts.md"]
    counts = {"figures": 0, "tables": 0, "algorithms": 0, "equations": 0}
    for path in inputs:
        print(f"Converting {path.name}", flush=True)
        convert(path, command, browser, counts)
    if counts != {"figures": 7, "tables": 16, "algorithms": 2, "equations": 5}:
        raise ValueError(f"Unexpected manuscript counts: {counts}")
    report = {
        "markdown_sources": {
            p.relative_to(HERE.parent).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in inputs
        },
        "language": "en",
        "template_source": "Instructions on Project reports 22Feb16.pdf",
        "layout": "A4, 12pt Times, 1.5 spacing, left 25.4mm, other margins 20mm",
        "pandoc_version": str(pypandoc.get_pandoc_version()),
        "mermaid_version": subprocess.check_output(command + ["--version"], text=True).strip(),
        "counts": counts,
        "figure_kinds": FIGURE_KINDS,
        "compiled": False,
        "requirements": json.loads((HERE / "report-requirements.json").read_text()),
        "bibliography": json.loads(
            pypandoc.convert_text((HERE / "references.bib").read_text(), "csljson", format="bibtex")
        ),
    }
    chapter_files = [HERE / "chapters" / f"{path.stem}.tex" for path in inputs]
    auxiliary_sources = [
        HERE / name
        for name in (
            "main.tex",
            "metadata.tex",
            "references.bib",
            "report-requirements.json",
            "mermaid-config.json",
            "build.py",
            "audit.py",
        )
    ] + chapter_files
    report["latex_sources"] = {
        p.relative_to(HERE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in auxiliary_sources
    }
    active_figures = {
        name
        for path in chapter_files
        for name in re.findall(r"\\includegraphics\[[^]]*\]\{([^}]+)\}", path.read_text())
    }
    report["figure_sources"] = {
        name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
        for name in sorted(active_figures)
    }
    stats_path = HERE.parent / "notes/visual-evidence-statistics.json"
    report["visual_evidence_statistics_sha256"] = hashlib.sha256(
        stats_path.read_bytes()
    ).hexdigest()
    if not args.generate_only:
        compiler = (
            os.environ.get("THESIS_TECTONIC")
            or shutil.which("tectonic")
            or str(Path.home() / ".cache/yecoding-thesis-tools/tectonic")
        )
        subprocess.run(
            [compiler, "--keep-logs", "--keep-intermediates", "--outdir", "build", "main.tex"],
            cwd=HERE,
            check=True,
            timeout=600,
        )
        import pymupdf

        pdf = HERE / "build/main.pdf"
        with pymupdf.open(pdf) as document:
            text = "\n".join(page.get_text() for page in document)
            if "Conclusions and Further Work" not in text or "References" not in text:
                raise ValueError("Compiled document missing final sections")
            report.update(
                compiled=True,
                pages=len(document),
                pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
            )
        report["tectonic_version"] = subprocess.check_output(
            [compiler, "--version"], text=True
        ).strip()
        package = HERE.parent / "thesis-latex-source.zip"
        files = inputs + chapter_files
        files += [
            HERE / name
            for name in (
                "main.tex",
                "metadata.tex",
                "references.bib",
                "README.md",
                "build.py",
                "audit.py",
                "mermaid-config.json",
                "report-requirements.json",
            )
        ]
        figure_paths = {
            name
            for path in chapter_files
            for name in re.findall(r"\\includegraphics\[[^]]*\]\{([^}]+)\}", path.read_text())
        }
        for name in sorted(figure_paths):
            identifier = Path(name).stem.removeprefix("fig-")
            suffixes = (
                (".mmd", ".svg", ".pdf")
                if FIGURE_KINDS[identifier] == "mermaid"
                else (".svg", ".pdf")
            )
            for suffix in suffixes:
                path = (HERE / name).with_suffix(suffix)
                if path.exists():
                    files.append(path)
        visual_stats = json.loads(stats_path.read_text())
        files += [HERE.parent / "figures" / "plot_evidence_figures.py", stats_path]
        files += [
            HERE.parent / "figures" / f"{stem}.{suffix}"
            for stem in visual_stats["generated_figures"]
            for suffix in ("svg", "pdf")
        ]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, path.relative_to(HERE.parent).as_posix())
        report["source_package_sha256"] = hashlib.sha256(package.read_bytes()).hexdigest()
    (HERE / "build/build-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    summary = {
        key: value
        for key, value in report.items()
        if key not in {"bibliography", "markdown_sources", "latex_sources"}
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
