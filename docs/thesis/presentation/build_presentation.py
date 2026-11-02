"""Build an editable stage-one deck and matching Chinese speaker notes.

Run from any directory with python-pptx==1.0.2 and Pillow installed.
All code excerpts and experimental numbers are read from repository evidence.
"""

# Long Chinese slide copy and narration are intentionally authored as single strings.
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import re
import textwrap
from pathlib import Path

from PIL import ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
FONT = "Noto Sans CJK SC"
MONO = "DejaVu Sans Mono"
FONT_DIR = Path.home() / ".local/share/fonts/project1-noto-cjk"
REGULAR = FONT_DIR / "NotoSansCJKSC-Regular.otf"
BOLD = FONT_DIR / "NotoSansCJKSC-Bold.otf"
MONO_FILE = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
INK = "24292D"
MUTED = "606A70"
ACCENT = "236C70"
LIGHT = "EDF4F4"
GRAY = "F4F5F6"
LINE = "CCD4D7"
RUST = "A34738"
WHITE = "FFFFFF"
W, H = 13.333333, 7.5
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(W), Inches(H)
prs.core_properties.title = "面向代码修复的多智能体协作与验证系统设计与实现 | 第一阶段成果汇报"
prs.core_properties.subject = "BEng 第一阶段：核心设计、代码实现与论文前半部分"
prs.core_properties.author = ""
prs.core_properties.language = "zh-CN"
notes: list[dict] = []
layout_checks: list[dict] = []
sources: dict[str, str] = {}


def read(relative: str) -> str:
    path = ROOT / relative
    sources[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path.read_text()


repair_source = read("src/yecoding/agent/repair.py")
workspace_source = read("src/yecoding/sandbox/workspace.py")
read("src/yecoding/sandbox/docker.py")
read("src/yecoding/config.py")
live = json.loads(read("eval/evidence/repair-heldout-live.json"))
checks = json.loads(read("eval/evidence/repair-verification.json"))
read("docs/thesis/latex/references.bib")
for chapter in [
    "01-introduction",
    "02-related-technologies",
    "03-requirements-analysis",
    "04-system-design",
    "05-core-implementation",
]:
    read(f"docs/thesis/en/{chapter}.md")


def excerpt(source: str, start: str, end: str) -> str:
    a = source.index(start)
    b = source.index(end, a)
    return textwrap.dedent(source[a:b]).strip()


def color(value: str) -> RGBColor:
    return RGBColor.from_string(value)


def wrap(value: str, width: float, size: float, *, bold=False, mono=False) -> list[str]:
    font = ImageFont.truetype(
        str(MONO_FILE if mono else BOLD if bold else REGULAR), round(size * 4)
    )
    max_width = width * 72 * 4
    lines = []
    for paragraph in value.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for token in re.findall(r"[A-Za-z0-9_./:~=-]+|[^A-Za-z0-9_./:~=-]", paragraph):
            if font.getlength(current + token) > max_width and current:
                lines.append(current.rstrip())
                current = token.lstrip()
            else:
                current += token
        lines.append(current)
    return lines


def rect(slide, x, y, w, h, fill=WHITE, stroke=LINE):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color(fill)
    if stroke:
        shape.line.color.rgb = color(stroke)
        shape.line.width = Pt(0.8)
    else:
        shape.line.fill.background()
    shape._element.spPr.append(OxmlElement("a:effectLst"))
    for ref in shape._element.xpath("./p:style/a:effectRef"):
        ref.set("idx", "0")
    return shape


def txt(slide, value, x, y, w, h, size=18, bold=False, fill=INK, align=None, mono=False):
    lines = value.split("\n") if mono else wrap(value, w - 0.02, size, bold=bold)
    if mono:
        measured = ImageFont.truetype(str(MONO_FILE), round(size * 4))
        if max((measured.getlength(line) for line in lines), default=0) > w * 72 * 4:
            raise ValueError(f"Code width overflow on slide {len(prs.slides)}: {value!r}")
    needed = len(lines) * size * 1.25 / 72
    if needed > h + 0.04:
        raise ValueError(
            f"Text overflow on slide {len(prs.slides)}: {value[:70]!r}, need={needed:.2f}, h={h}"
        )
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear()
    # Fixed text boxes avoid Impress centring SHAPE_TO_FIT_TEXT during import.
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.word_wrap = False
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.line_spacing = Pt(size * 1.25)
        p.space_before = p.space_after = Pt(0)
        p.alignment = align if align is not None else PP_ALIGN.LEFT
        for run in p.runs:
            run.font.name = MONO if mono else FONT
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.color.rgb = color(fill)
            props = run._r.get_or_add_rPr()
            props.set("lang", "zh-CN")
            ea = OxmlElement("a:ea")
            ea.set("typeface", FONT)
            props.append(ea)
    layout_checks.append(
        {
            "slide": len(prs.slides),
            "text": value[:70],
            "lines": len(lines),
            "height": h,
            "required_height": needed,
        }
    )
    return shape


def arrow(slide, x, y, w=0.34, h=0.20, down=False, left=False):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.DOWN_ARROW if down else MSO_SHAPE.RIGHT_ARROW,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color(ACCENT)
    shape.line.fill.background()
    shape._element.spPr.append(OxmlElement("a:effectLst"))
    for ref in shape._element.xpath("./p:style/a:effectRef"):
        ref.set("idx", "0")
    if left:
        shape.rotation = 180
    return shape


def box(slide, title, body, x, y, w, h, *, fill=GRAY, size=17):
    rect(slide, x, y, w, h, fill)
    txt(slide, title, x + 0.17, y + 0.15, w - 0.34, 0.45, size=19, bold=True, fill=ACCENT)
    txt(slide, body, x + 0.17, y + 0.76, w - 0.34, h - 0.88, size=size)


def banner(slide, value, y=6.35, fill=LIGHT, text_color=ACCENT, size=17):
    rect(slide, 0.55, y, 12.23, 0.50, fill, None)
    txt(slide, value, 0.73, y + 0.08, 11.87, 0.34, size=size, bold=True, fill=text_color)


def new(title, section, seconds, script, cue, source="", *, backup=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    rect(slide, 0, 0, W, H, WHITE, None)
    rect(slide, 0.55, 0.42, 0.07, 0.43, ACCENT, None)
    txt(slide, title, 0.78, 0.37, 11.95, 0.62, 27, True)
    txt(slide, section, 0.57, 1.08, 12.1, 0.33, 12, fill=MUTED)
    rect(slide, 0.55, 7.06, 12.23, 0.012, LINE, None)
    txt(
        slide,
        "yeCoding Python  |  BEng 第一阶段汇报" + ("  |  备份" if backup else ""),
        0.57,
        7.16,
        6.8,
        0.22,
        10.5,
        fill=MUTED,
    )
    txt(
        slide,
        f"{len(prs.slides):02d}",
        12.13,
        7.13,
        0.63,
        0.26,
        12,
        fill=MUTED,
        align=PP_ALIGN.RIGHT,
    )
    if source:
        txt(slide, "依据：" + source, 0.57, 6.88, 12.16, 0.18, 9, fill=MUTED)
    notes.append(
        {
            "title": title,
            "seconds": seconds,
            "script": script,
            "cue": cue,
            "source": source,
            "backup": backup,
        }
    )
    slide.notes_slide.notes_text_frame.text = f"{'备份，不计主讲时间' if backup else str(seconds) + ' 秒'}\n\n{script}\n\n演示提示：{cue}\n\n依据：{source}"
    return slide


def table(slide, headers, rows, widths, *, x=0.55, y=1.66, row_h=0.65, font=17):
    for row_index, row in enumerate([headers, *rows]):
        xx = x
        for i, value in enumerate(row):
            rect(
                slide,
                xx,
                y + row_index * row_h,
                widths[i],
                row_h,
                LIGHT if row_index == 0 else WHITE if row_index % 2 == 0 else GRAY,
            )
            txt(
                slide,
                str(value),
                xx + 0.13,
                y + row_index * row_h + 0.12,
                widths[i] - 0.26,
                row_h - 0.16,
                size=font if row_index else font - 1,
                bold=row_index == 0,
                fill=ACCENT if row_index == 0 else INK,
            )
            xx += widths[i]


def code(slide, content, x, y, w, h, size=15):
    rect(slide, x, y, w, h, GRAY)
    for i, line in enumerate(content.splitlines()):
        prefix = line.lstrip()
        ink = (
            ACCENT
            if prefix.startswith("+") and not prefix.startswith("+++")
            else MUTED
            if prefix.startswith("#")
            else INK
        )
        txt(
            slide,
            line,
            x + 0.16,
            y + 0.15 + i * size * 1.25 / 72,
            w - 0.32,
            size * 1.25 / 72 + 0.02,
            size=size,
            fill=ink,
            mono=True,
        )


# 1
s = new(
    "第一阶段成果汇报",
    "本科毕业设计 · 核心设计 / 代码实现 / 论文前半部分",
    25,
    "老师好，我今天汇报的题目是面向代码修复的多智能体协作与验证系统设计与实现。这一阶段的重点，是把修复任务从模型生成一段代码，推进到有角色分工、有执行边界、有固定验收和交付记录的完整流程。接下来我先讲设计，再用关键源码和已有记录说明设计如何落地，最后汇报论文进展与下一步工作。",
    "封面只交代课题与本次汇报范围，不逐字念英文题目。",
)
txt(s, "面向代码修复的多智能体\n协作与验证系统设计与实现", 0.78, 2.0, 11.9, 1.75, 34, True)
txt(
    s,
    "Design and Implementation of a Multi-Agent Collaboration\nand Verification System for Code Repair",
    0.8,
    4.0,
    11.8,
    0.9,
    20,
    fill=MUTED,
)
rect(s, 0.8, 5.5, 11.7, 0.015, LINE, None)
txt(
    s,
    "项目载体：yeCoding Python    |    汇报重点：设计可解释、代码可定位、结果可核查",
    0.8,
    5.88,
    11.8,
    0.6,
    18,
)

# 2
s = new(
    "研究问题与第一阶段目标",
    "01 研究定位",
    40,
    "本课题要解决的不是让模型声称已经修复，而是如何建立可信、可检查的修复过程。我把任务输入限定为问题描述、当前源码、预先准备的容器镜像、固定测试命令和预算。对应三个问题：第一，怎样限制文件与命令操作；第二，怎样把真实补丁、测试和角色交接关联起来；第三，多角色在相同外部预算下是否值得。第一阶段已经形成可运行核心和论文前部；修复质量提升仍然需要实验检验。",
    "指向输入与输出，强调不自动回写原仓库；不要把研究问题说成已证明的结论。",
    "论文第 1、3 章；agent/repair.py",
)
box(
    s,
    "任务输入",
    "问题描述 + 当前源码\n预备镜像 + 固定测试\n尝试 / 调用 / Token / 时间预算",
    0.55,
    1.7,
    5.75,
    1.85,
    size=17,
)
arrow(s, 6.46, 2.4, 0.4, 0.22)
box(
    s,
    "任务输出",
    "候选补丁 + 验证证据\n明确终止状态 + 消耗记录\n原始仓库不自动修改",
    7.02,
    1.7,
    5.75,
    1.85,
    size=17,
)
table(
    s,
    ["研究问题", "本阶段对应交付"],
    [
        ["RQ1：怎样约束修改与执行？", "双副本工作区、受限容器、清理机制"],
        ["RQ2：怎样形成可验证的协作闭环？", "角色权限、固定测试、反馈与状态记录"],
        ["RQ3：多角色带来什么收益与成本？", "对比方案与初步证据，保留失败结果"],
    ],
    [5.75, 6.48],
    y=3.88,
    row_h=0.56,
    font=16,
)
banner(s, "适用范围：具备可运行测试的 Python 修复任务；不涉及模型训练或并行补丁合并。", size=16)

# 3
s = new(
    "文献依据如何转化为设计选择",
    "02 相关工作与技术路线",
    40,
    "相关工作主要提供三类依据。ReAct 和 SWE-agent 说明了模型通过工具读取、编辑、执行的基本路线；AutoGen 提供角色协作的参考，但没有理由预设角色越多效果越好；自动程序修复研究则提醒我们，通过现有测试的补丁不等于普遍正确。因此本系统采用顺序交接和单写者控制复杂度，用程序掌握固定验收，再用不反馈给模型的追加测试做事后检查。这些是技术选择，不是对已有论文效果的复现声明。",
    "每行讲清一项选择；文献完整题名放在备份第 21 页。",
    "论文第 2 章；references.bib 中 ReAct / SWE-agent / AutoGen / APR 与补丁评估文献",
)
table(
    s,
    ["研究方向", "已有启发", "本课题的实现选择"],
    [
        [
            "工具型 Agent\nReAct / SWE-agent",
            "观察、行动、执行反馈",
            "复用 query 与 ToolExecutor\n把验收提升到流程控制层",
        ],
        ["多角色协作\nAutoGen", "任务分工与上下文隔离", "协调 → 修改 → 审查\n顺序交接，单个写入者"],
        [
            "Automatic Program Repair\n补丁过拟合与独立评估",
            "测试通过不等于语义正确",
            "固定验收 + 事后追加测试\n区分候选正确性与流程完成",
        ],
    ],
    [3.2, 4.0, 5.03],
    row_h=1.2,
    font=17,
)
banner(s, "研究假设保持开放：多角色可能改善检查，也可能因交接成本消耗预算。", y=6.05)

# 4
s = new(
    "系统总体架构",
    "03 完整设计 · 四个逻辑层，运行于同一 Python 应用",
    60,
    "整体分为四个逻辑层。最上层是 CLI、交互终端、SDK 和 Runtime 入口；第二层是编排，通用模式和专用修复模式在这里分开。CLI 的 repair 直接建立 VerifiedRepair，其他适配入口通过 QueryEngine 调用同一修复核心。第三层复用模型交互、工具、代码上下文、Skill 和 Memory。最下层负责副本、容器执行和证据落盘。这里不是微服务架构，也不能把 repair 的容器和固定验收约束，直接说成所有通用模式都具备。",
    "按从上到下讲解；指出通用模式与专用修复在编排层分开，执行约束由修复核心持有。",
    "agent/query_engine.py；agent/repair.py；entrypoints/cli.py",
)
for y, label, body, f in [
    (1.65, "接口层", "CLI repair   /   REPL /repair   /   SDK   /   Runtime + Task Worker", GRAY),
    (2.76, "编排层", "QueryEngine：通用 ReAct / Plan / Team     |     专用 VerifiedRepair", LIGHT),
    (
        3.87,
        "能力层",
        "query 模型循环   +   工具执行器   +   AST 代码上下文   +   Skill / Memory",
        GRAY,
    ),
    (
        4.98,
        "执行与存储层",
        "RepairWorkspace 双副本   +   DockerSandbox   +   JSON / JSONL / Patch",
        LIGHT,
    ),
]:
    rect(s, 0.55, y, 12.23, 0.82, f)
    txt(s, label, 0.75, y + 0.2, 1.7, 0.4, 18, True, fill=ACCENT)
    txt(s, body, 2.48, y + 0.2, 10.05, 0.4, 17)
for y in [2.51, 3.62, 4.73]:
    arrow(s, 6.4, y, 0.25, 0.2, True)
banner(
    s,
    "入口差异：CLI → VerifiedRepair；REPL / SDK / Runtime → QueryEngine.repair → 同一核心。",
    y=6.16,
    size=15.5,
)

# 5
s = new(
    "模块组成与核心代码位置",
    "03 完整设计 · 现有平台与本课题新增工作的边界",
    40,
    "代码组织上，我没有把整个 CLI 都作为本课题从零实现的成果。底部的模型客户端、工具循环、代码索引、Skill 和 Memory 来自已有平台；本阶段核心新增是修复编排器、双副本工作区、受限容器执行，以及相应的入口接线和验证。表中列出了模块和实际路径，后面三处关键代码分别展示候选检查、预算控制和验收门槛。这种划分可以把平台能力和本课题贡献区分开。",
    "简述新增前三行，复用模块一笔带过；源码统一以 src/yecoding/ 为根目录。",
    "源码目录；论文第 3、4、5 章",
)
table(
    s,
    ["模块", "代码路径（相对 src/yecoding/）", "责任 / 工作性质"],
    [
        ["VerifiedRepair", "agent/repair.py", "专用闭环、角色交接、预算与证据；新增"],
        ["RepairWorkspace", "sandbox/workspace.py", "源码快照、候选检查、双副本；新增"],
        ["DockerSandbox", "sandbox/docker.py", "命令隔离、资源限制、清理；新增"],
        ["入口适配", "entrypoints/；agent/query_engine.py", "CLI / REPL / SDK / Runtime 接线"],
        ["模型与工具循环", "agent/query.py；llm/；tools/", "复用，按角色收紧注册工具"],
        ["代码上下文", "rag/", "复用 AST 索引与分层上下文"],
        ["知识与经验", "skill/；memory/；builtin_skills/", "复用机制，新增修复 Skill 与接入约束"],
    ],
    [2.3, 5.05, 4.88],
    row_h=0.56,
    font=15,
)
banner(s, "本课题重点：把已有编码能力组织为可约束、可验收、可追溯的专用修复流程。", y=6.38, size=16)

# 6
s = new(
    "修复闭环：从失败复现到补丁交付",
    "03 完整设计 · 测试与交接由程序编排",
    50,
    "一次任务先检查输入，再对当前源码建立快照，并在验证副本执行基线测试。只有确认存在可复现失败，才进入协调与修改。修改角色结束后，系统从真实文件计算补丁，检查保护路径，然后重建验证副本并执行固定测试。多角色模式还需要完成审查交接，随后程序才决定成功、重试或停止。失败反馈在预算内交给新一轮修改上下文；基线本来就通过、执行环境异常、没有有效修改，也都有独立状态，不计作成功修复。",
    "沿箭头：上排从左到右，下排从右到左；底部说明反馈分支，不把模型总结当成补丁来源。",
    "agent/repair.py：VerifiedRepair.run",
)
steps = [
    ("1 输入与副本", "校验选项\n快照 + 指纹"),
    ("2 基线复现", "固定命令执行\n确认真实失败"),
    ("3 协调与修改", "计划 → Worker\n真实文件变更"),
    ("4 候选检查", "保护文件 + diff\n重建 verify"),
    ("5 测试与审查", "固定测试\nVerifier 交接"),
    ("6 决策与交付", "成功 / 重试 / 停止\n报告 + 补丁"),
]
for i, (title, body) in enumerate(steps):
    row, col = divmod(i, 3)
    if row:
        col = 2 - col
    box(
        s,
        title,
        body,
        0.55 + col * 4.2,
        1.68 + row * 2.1,
        3.83,
        1.65,
        fill=LIGHT if i in [1, 4, 5] else GRAY,
    )
    if i in {0, 1}:
        arrow(s, 4.44 + col * 4.2, 2.39, 0.26, 0.18)
    if i in {3, 4}:
        arrow(s, 4.44 + (col - 1) * 4.2, 4.49, 0.26, 0.18, left=True)
arrow(s, 10.78, 3.42, 0.25, 0.27, down=True)
txt(
    s,
    "失败且预算允许 → 反馈返回 Worker；修改副本保留，角色对话重新建立。",
    0.7,
    5.8,
    11.96,
    0.35,
    16,
    fill=ACCENT,
)
banner(
    s,
    "分支：基线已通过 ≠ 修复成功；环境异常单列；空补丁 / 重复补丁停止为 no_progress。",
    y=6.32,
    size=15.5,
)

# 7
s = new(
    "三角色协作与权限契约",
    "03 完整设计 · 顺序交接、单写者、独立上下文",
    50,
    "这里的多智能体是三个逻辑角色，不要求三个不同模型或独立进程。协调者只读，给出短计划；修改者拥有受限写入和容器命令能力，是唯一修改业务源码的角色；审查者读取验证副本和允许提供的测试证据，输出分析建议。每次调用都建立新的 history 和 Skill 缓冲，避免把所有聊天历史无差别复制给下一个角色。重试保留工作区修改，但不继承完整对话。角色顺序执行，因此当前不涉及多补丁并发合并。",
    "依次指向三个角色的输入、工具和交付；强调只读指业务源码，内部索引可产生缓存。",
    "agent/repair.py：_agent / _registry",
)
for i, (title, body) in enumerate(
    [
        (
            "Coordinator · 协调",
            "输入：任务、约束、经验\n工具：只读与代码搜索\n工作区：work\n交付：简短修复计划",
        ),
        (
            "Worker · 修改",
            "输入：任务、计划、反馈\n工具：读写 + 容器命令\n工作区：work\n交付：文件变更与摘要",
        ),
        (
            "Verifier · 审查",
            "输入：候选 diff、证据\n工具：只读与代码搜索\n工作区：verify\n交付：问题分析与建议",
        ),
    ]
):
    box(s, title, body, 0.55 + i * 4.2, 1.74, 3.83, 3.02, fill=LIGHT if i == 1 else GRAY, size=17)
    if i < 2:
        arrow(s, 4.44 + i * 4.2, 3.02, 0.26, 0.18)
txt(
    s,
    "每次角色调用：history=[] + 独立 SkillContextBuffer",
    0.73,
    5.18,
    11.9,
    0.4,
    21,
    True,
    fill=ACCENT,
)
txt(
    s,
    "跨角色传递结构化任务、计划、候选和证据；不传递共享的可写聊天状态。",
    0.73,
    5.82,
    11.9,
    0.4,
    18,
)
banner(s, "权限通过工具注册表落实；角色提示词负责指导行为，但不是安全边界。", y=6.35, size=16)

# 8
s = new(
    "工作区与候选：原仓库不作为试验场",
    "03 完整设计 + 源码 ①",
    50,
    "文件隔离分为原始源码、修改副本、验证副本和交付目录。快照记录当前支持文件的字节和指纹，而不只记录 Git HEAD。Worker 在 work 中修改；候选检查比较真实字节，拒绝测试或配置等受保护文件的变化，再从候选内容重建 verify。右侧是真实源码，关键是先列出变化，再检查保护路径，而不是相信模型口头报告。合法 diff 和结果落在原仓库之外，结束后临时副本清理，补丁不会自动应用到原始项目。",
    "先看左侧文件流，再读右侧 changes 与 protected 两行；不逐行念代码。",
    "sandbox/workspace.py：RepairWorkspace.__init__ / candidate；完整原始节选见口播稿",
)
for i, (title, body) in enumerate(
    [
        ("原始源码 → 快照", "路径 + 文件字节 + SHA256；只读取"),
        ("work 修改副本", "Worker 编辑；跨尝试保留修改"),
        ("候选检查 → verify", "检查保护文件；合法候选重建验证副本"),
        ("独立交付目录", "报告 / 事件 / 尝试补丁；成功才导出最终补丁"),
    ]
):
    rect(s, 0.55, 1.7 + i * 1.05, 5.0, 0.86, LIGHT if i == 2 else GRAY)
    txt(s, title, 0.72, 1.8 + i * 1.05, 4.66, 0.3, 17, True, fill=ACCENT)
    txt(s, body, 0.72, 2.16 + i * 1.05, 4.66, 0.24, 12.5)
    if i < 3:
        arrow(s, 2.91, 2.59 + i * 1.05, 0.19, 0.15, down=True)
candidate_code = excerpt(
    workspace_source, "        current = inventory(self.work)", "        patch = []"
)
# The exception message is omitted, not rewritten, to keep the excerpt legible.
candidate_display = (
    candidate_code[: candidate_code.index("if forbidden:")]
    + "if forbidden:\n    # reject protected-file edits\n    ..."
)
code(s, candidate_display, 5.85, 1.7, 6.93, 3.45, 13.5)
txt(
    s,
    "展示节选：省略异常消息，保留原始检查逻辑。\n测试与配置禁止变化；不支持二进制候选与符号链接。",
    5.98,
    5.48,
    6.62,
    0.7,
    16,
)
banner(s, "验证对象始终是候选文件本身，不是 Worker 的“已修好”描述。", y=6.35, size=17)

# 9
s = new(
    "工具边界：按角色构造能力白名单",
    "03 完整设计 · 权限落实在程序，不只在 Prompt",
    50,
    "工具控制采用重新构造注册表的方式。只读角色拿不到写工具；Worker 的写工具还会经过路径检查和保护文件检查。命令工具不沿用宿主机执行器，而是改接 DockerSandbox。修复配置也单独复制，在这条路径关闭任意 MCP、网络工具和自动记忆写入，避免扩展工具绕过修复约束。左侧代码展示的是白名单筛选的实际实现。这里说的收紧仅作用于 repair，不会把用户原有会话的权限配置整体改掉。",
    "说明 readonly 分支与 shell 替换；源码节选省略了后续包装部分。",
    "agent/repair.py：_registry；run 中的复制配置与策略调整",
)
registry_code = excerpt(
    repair_source, "        registry = ToolRegistry()", "            original = tool.handler"
)
code(s, registry_code, 0.55, 1.78, 12.23, 1.55, 16)
table(
    s,
    ["边界", "落实方式"],
    [
        ["角色可用工具", "READ_TOOLS / WRITE_TOOLS；只读角色不注册写入与命令"],
        ["文件路径与保护文件", "PathGuard + protected；命令改动仍会在候选阶段检查"],
        ["命令执行", "bash / execute_command handler → DockerSandbox"],
        ["外部工具与会话状态", "专用修复配置副本；不暴露任意 MCP / web / 记忆写工具"],
    ],
    [3.0, 9.23],
    y=3.68,
    row_h=0.56,
    font=16,
)
banner(s, "失效即停止：容器镜像缺失或启动异常，不降级为宿主机 shell。", y=6.35)

# 10
s = new(
    "容器执行边界与资源约束",
    "03 完整设计 · 容器限制命令，宿主机保留编排与模型通信",
    45,
    "执行边界需要准确说明。模型通信、文件工具、索引和报告仍在宿主机，只有命令进入一次性容器。修改命令挂载可写的 work，固定测试挂载只读的 verify。容器默认断网、只读根文件系统、丢弃 capabilities，并限制进程、内存、CPU 和临时空间。每条命令新建容器，标准输出与错误分别限量保留，超时或取消时清理容器。这能降低风险，但容器共享宿主内核，不等价于虚拟机级隔离，也不能宣称绝对安全。",
    "指出 host/container 分界；不要声称完整 Agent 都在 Docker 内。",
    "sandbox/docker.py：arguments / execute / _remove",
)
box(
    s,
    "Host · 宿主机",
    "VerifiedRepair 编排与预算\nLLM 通信、文件工具、AST 索引\n快照、候选检查、记录落盘",
    0.55,
    1.74,
    5.1,
    2.38,
    size=18,
)
arrow(s, 5.82, 2.7, 0.5, 0.25)
box(
    s,
    "Docker · 每条命令一个容器",
    "Worker：work 可写挂载\n固定测试：verify 只读挂载\n执行结束 / 超时 / 取消 → 清理",
    6.5,
    1.74,
    6.28,
    2.38,
    fill=LIGHT,
    size=18,
)
table(
    s,
    ["隔离配置", "资源与生命周期"],
    [
        ["--network=none；--read-only", "--memory=512m；--cpus=1"],
        ["--cap-drop=ALL；no-new-privileges", "128 个进程；/tmp 为 64 MiB tmpfs"],
        ["--pull=never；只挂载任务副本", "stdout / stderr 各保留 20,000 bytes；持续排空"],
    ],
    [6.1, 6.13],
    y=4.42,
    row_h=0.45,
    font=14,
)
banner(s, "边界声明：共享内核；依赖预备镜像；容器启动失败不会回退到宿主机执行。", y=6.35, size=16)

# 11
s = new(
    "共享预算与明确终止状态",
    "03 完整设计 + 源码 ②",
    55,
    "三个角色和所有尝试共用同一个 BudgetClient，避免每个角色都重新获得一份预算。左侧是实际检查代码：在发起下一次模型请求前检查调用数和累计 Token，再累计服务端返回的 usage。产品默认是三次尝试、三十六次模型调用、六万 Token 请求前阈值、九百秒流程和六十秒单命令。注意这个 Token 阈值不是最终硬上限，最后一次响应可能越过它。系统把预算不足、没有进展、环境问题、超时和取消分别记录，保证失败仍能解释。",
    "讲清共享实例与请求前阈值；产品默认和实验设置不同，备份页另列。",
    "agent/repair.py：BudgetClient / run；config.py：RepairConfig",
)
budget_code = excerpt(
    repair_source, "    async def chat(self, *args, **kwargs):", "\n\nclass VerifiedRepair"
)
code(s, budget_code, 0.55, 1.72, 8.75, 3.9, 13.0)
box(
    s,
    "产品默认预算",
    "3 次尝试\n36 次模型调用\n60,000 Token 请求前阈值\n900 秒流程 / 60 秒命令",
    9.56,
    1.72,
    3.22,
    3.9,
    fill=LIGHT,
    size=15,
)
txt(
    s,
    "成功：verified    |    非成功：baseline_passed / no_progress / budget_exhausted 等",
    0.72,
    5.95,
    11.9,
    0.35,
    16,
)
banner(
    s,
    "所有角色与重试共享预算；响应可能越过请求前 Token 阈值，不把它写成最终硬上限。",
    y=6.38,
    size=15.5,
)

# 12
s = new(
    "上下文、Skill 与 Memory 如何配合",
    "03 完整设计 · 代码证据、过程知识与项目经验分开管理",
    45,
    "除了流程控制，还需要给模型合适的信息。代码上下文使用 Python AST 和本地索引组织符号、关系、源码片段及文件摘要，不是向量检索，也不是完整运行时调用图。Skill 按角色加载复现、最小修改和验证流程，记录版本及内容指纹；它只提供指导，不授予工具权限。Memory 在原项目作用域召回一次，修复经验需要匹配源码指纹，只有成功且启用时才写入。当前实验关闭跨任务记忆，所以不能拿已有结果证明 Memory 或 Skill 的独立增益。",
    "解释三列分别回答“代码在哪、怎样做、过去做过什么”；避免笼统称为 RAG 增强。",
    "rag/context_builder.py；skill/；agent/repair.py：_agent / _recall / _remember",
)
for i, (title, body) in enumerate(
    [
        (
            "AST 代码上下文",
            "Python 词法符号与近似关系\n签名 → 关系 → 源码 → 摘要\n片段长度与来源可见\n不等于完整语义调用图",
        ),
        (
            "Skill · 过程知识",
            "协调：repair-reproduce\n修改：reproduce + minimal\n审查：repair-verify\n按角色注入，记录版本与哈希",
        ),
        (
            "Memory · 项目经验",
            "原项目作用域只召回一次\n修复经验校验 base_hash\n成功且启用时才写入\n经验按不可信数据处理",
        ),
    ]
):
    box(s, title, body, 0.55 + i * 4.2, 1.78, 3.83, 3.45, fill=LIGHT if i == 1 else GRAY, size=16)
txt(
    s,
    "任务 + 代码上下文 + 角色 Skill + 合格经验 → 独立角色上下文 → 工具执行",
    0.72,
    5.65,
    11.94,
    0.45,
    19,
    True,
    fill=ACCENT,
)
banner(
    s, "已完成机制接入；尚未通过独立消融实验证明 Skill / Memory 带来修复质量提升。", y=6.35, size=16
)

# 13
s = new(
    "验收核心：测试决定门槛，审查不能覆盖失败",
    "04 核心实现 + 源码 ③",
    50,
    "这页是整个系统的验收核心。第一处代码执行固定测试，再把所有结果汇总成 passed；第二处代码在必要的审查交接完成后，才根据 passed 设置 verified 并导出最终补丁。因此审查角色说通过，不能覆盖失败测试；但测试已经通过、审查因预算耗尽没有完成，也不能算工作流成功。这样的定义把候选行为和流程完成区分开。报告里会同时保存测试、审查、状态和消耗，避免仅凭最终一句话判断结果。",
    "两处为原始源码节选；中间审查代码未展示。指出固定测试通过只覆盖已给验收条件。",
    "agent/repair.py：run 中 verification / review / if passed",
)
acceptance = excerpt(
    repair_source,
    "                        verification = await self._tests",
    '                        review = ""',
)
export = excerpt(
    repair_source, "                        if passed:", "                            try:"
)
code(s, acceptance, 0.55, 1.8, 12.23, 1.42, 16)
txt(
    s,
    "中间步骤：非 single 策略执行 Verifier 审查交接，失败 / 超预算会中断成功出口。",
    0.74,
    3.56,
    11.9,
    0.44,
    18,
    fill=ACCENT,
    bold=True,
)
code(s, export, 0.55, 4.22, 12.23, 1.4, 14.5)
banner(
    s,
    "verified = 固定验收通过 + 所需交接完成；不是多 Agent 投票，也不是模型自报成功。",
    y=6.35,
    size=16,
)

# 14
case = next(r for r in live["records"] if r["id"] == "none-value")["runs"][0]
patch_path = f"eval/evidence/repair-runs/{case['id']}/candidate.patch"
patch = read(patch_path)
s = new(
    "一次真实修复的交付结果",
    "04 核心代码与可检查产物 · 归档案例，不是现场模型演示",
    40,
    "这是一条归档的真实模型运行，用单角色路径展示最小交付链路，不用它证明多角色效果。任务来自 python-dotenv 的人工缺陷：环境变量为 None 时错误输出字符串 None。补丁只增加空值判断，原测试从一个失败变成九项通过，事后加入四项检查后，合计十三项也通过。系统保留 report、事件和补丁，并未回写原始项目。这条案例说明交付链路已经打通，完整多角色效果仍要看统一对比。",
    "绿色两行为真实新增代码；这是 single 路径真实案例。可打开源补丁核对，不现场调用付费模型。",
    patch_path,
)
code(s, patch, 0.55, 1.77, 8.05, 3.75, 12.1)
box(
    s,
    "none-value · single",
    f"模型调用：{case['llm_calls']} 次\n累计 Token：{case['usage']['total_tokens']:,}\n固定测试：9 / 9 通过\n追加后总计：13 / 13 通过",
    8.88,
    1.77,
    3.9,
    3.75,
    fill=LIGHT,
    size=17,
)
txt(
    s,
    "交付：report.json  /  events.jsonl  /  attempt-1.patch  /  candidate.patch",
    0.73,
    5.85,
    11.88,
    0.4,
    18,
    True,
    fill=ACCENT,
)
banner(s, "本例只证明该任务的可执行交付链路；不把单例成功外推为通用修复质量。", y=6.35, size=16)

# 15
s = new(
    "论文前半部分：已经形成的论证链",
    "05 论文进展 · 英文 BEng 论文，本次聚焦第 1–5 章",
    40,
    "论文方面已经有英文 BEng 稿，本次汇报聚焦前五章。第一章定义问题和研究边界；第二章梳理工具型 Agent、程序修复和补丁评估；第三章把目标写成输入输出、权限和非功能需求；第四章给出架构、角色、文件流和状态；第五章用核心源码解释实现。也就是说，论文不是只有背景和概念图，已经能从需求追到设计，再追到真实代码。后半部分已有初步实验材料，下一步主要按导师意见修订论证和扩展证据。",
    "指明英文论文来源路径；不把全稿存在说成导师已验收或最终定稿。",
    "docs/thesis/en/01–05；docs/thesis/latex/build/main.pdf",
)
table(
    s,
    ["章节", "已形成内容", "对应本次汇报"],
    [
        ["1 Introduction", "背景、任务定义、RQ1–RQ3、贡献边界", "第 2 页"],
        ["2 Related Technologies", "Agent / APR / 补丁评估与技术选择", "第 3 页"],
        ["3 Requirements Analysis", "功能、权限、验收、失败与预算需求", "第 2、5、11 页"],
        ["4 System Design", "架构、角色、双副本、状态、入口契约", "第 4–12 页"],
        ["5 Core Implementation", "候选检查、容器执行、预算与固定验收", "第 8–14 页"],
    ],
    [3.2, 6.3, 2.73],
    row_h=0.7,
    font=16,
)
banner(
    s, "当前状态：可讲解、可定位的论文稿；本次聚焦前部，后半已有实验仅作初步验证。", y=6.35, size=16
)

# 16
s = new(
    "第一阶段验证：能运行，不等于已证明优越",
    "06 已有证据与边界 · 以下为 2026-10-20 归档结果",
    50,
    "验证分为工程功能与真实模型两部分。归档的完整测试是一百六十项通过，覆盖原有功能、新增修复和一个快照回归；其中使用脚本模型控制分支，并让命令在真实 Docker 中执行，因此不是一百六十个真实模型修复任务。真实模型部分是八个留出人工缺陷乘三种策略，共二十四次运行。流程成功分别为八、五、四，七次失败都耗尽 Token。当前证据支持工程闭环已打通，但没有证明多角色优于单角色，反而提示需要优先研究交接成本和预算分配。",
    "两类证据分开解释；这些是归档结果，本次制作 PPT 未重跑业务回归或模型实验。",
    "eval/evidence/repair-verification.json；repair-heldout-live.json；论文第 6 章",
)
box(
    s,
    "功能验证 · 160 passed",
    "134 项原有测试\n25 项修复测试 + 1 项快照回归\n脚本模型 + 真实 Docker 执行\n覆盖重试、保护文件、预算、取消等",
    0.55,
    1.75,
    5.7,
    3.25,
    size=18,
)
box(
    s,
    "真实模型 · 24 次运行",
    "8 个留出人工缺陷 × 3 种策略\n同一项目、同一模型、每条件 1 次\nsingle / team / verified\n完成数：8/8  ·  5/8  ·  4/8",
    6.52,
    1.75,
    6.26,
    3.25,
    fill=LIGHT,
    size=18,
)
txt(
    s,
    "关键发现：7 次 Token 预算失败；多角色开销可能抵消收益。追加检查无已观测误接收。",
    0.72,
    5.47,
    11.94,
    0.65,
    18,
    True,
    fill=ACCENT,
)
banner(
    s,
    "不能推断：多角色一定更好、追加测试覆盖全部语义、或小样本结果可泛化到真实仓库。",
    y=6.35,
    size=15.5,
)

# 17
s = new(
    "下一阶段：补强证据与完善论文",
    "07 后续安排 · 提议，待与导师确认优先级",
    45,
    "下一阶段我想把重点放在已有设计的证据强度，而不是继续增加角色数量。首先扩展任务来源，优先补充可复现的真实缺陷，并做重复和随机顺序实验；其次分析 Token 消耗与交接失败，比较更紧凑上下文和角色预算分配，提前固定验收定义；再次在需要时做 Skill、Memory 的独立消融。论文则围绕研究问题补齐结果解释、局限和复现材料。具体任务规模和排期希望本次和老师确认，不把这些计划说成已经完成。",
    "这是待确认工作计划；不承诺尚未执行的收益或随意填写已批准日期。",
    "基于当前限制提出；尚未执行",
)
table(
    s,
    ["任务", "下一步产物", "验收方式"],
    [
        ["扩展与重复评估", "真实缺陷清单、重复运行与完整失败记录", "冻结任务与划分；报告全部运行"],
        ["协作开销分析", "角色 Token / 调用 / 交接阶段统计", "控制外部预算，比较成功与成本"],
        ["知识机制消融", "按需设计 Skill / Memory 开关对照", "同任务同条件，隔离跨任务污染"],
        ["论文与交付整理", "修订结果、讨论、局限及复现说明", "图表—原始记录—源码可互相定位"],
    ],
    [3.0, 5.1, 4.13],
    row_h=0.85,
    font=16,
)
banner(s, "优先级建议：先扩大评估与解释失败，再决定是否调整架构。", y=6.35)

# 18
s = new(
    "本阶段小结与希望确认的问题",
    "08 总结",
    30,
    "总结这一阶段，我已经形成三类成果：完整设计，包括角色、工作区、执行边界和验收规则；实际代码，包括共享修复核心、关键保护机制和结构化交付；论文前部，包括从研究问题到设计实现的论证。现有结果还不能支持多角色更优的结论。希望老师重点确认：当前课题范围是否合适，下一阶段是否优先补充真实缺陷和重复实验，以及论文是否应进一步突出验收与协作成本分析。我的汇报到这里。",
    "在此停留并接受提问；第 19–21 页是备份，不默认继续播放。",
)
for i, (title, body) in enumerate(
    [
        ("设计", "四层架构 + 三角色契约\n双副本 + 受限执行 + 固定验收"),
        ("代码", "VerifiedRepair / Workspace / Docker\n统一核心、失败状态、证据交付"),
        ("论文", "英文第 1–5 章可对应设计与源码\n初步实验如实保留成本与失败"),
    ]
):
    rect(s, 0.55, 1.75 + i * 1.1, 12.23, 0.88, LIGHT if i == 0 else GRAY)
    txt(s, title, 0.75, 1.98 + i * 1.1, 1.4, 0.4, 23, True, fill=ACCENT)
    txt(s, body, 2.3, 1.92 + i * 1.1, 10.2, 0.65, 17)
txt(s, "请导师确认", 0.75, 5.4, 2.0, 0.4, 21, True, fill=ACCENT)
txt(s, "课题范围   ·   真实缺陷与重复实验的优先级   ·   论文论证重点", 2.9, 5.45, 9.6, 0.6, 20)

# 19 backup
summary = live["summary"]
s = new(
    "备份 A：三种策略的实际结果与设置",
    "技术追问备用 · 不计入主讲时间",
    0,
    "三种策略都使用同一固定验收门槛。single 只有修改角色，接收执行反馈；team 有三个角色，但审查不获得新的测试输出，后续仅给审查反馈；verified 同时给执行和审查反馈。这里的 team 是 repair 的消融标签，不是通用 Team 模式。verified 有一个候选已通过测试，但后续审查耗尽预算，因此追加检查通过数比流程成功数多一。七次失败均为 Token 耗尽；所有运行只形成一次尝试，所以不能声称实验已经验证多轮重试收益。",
    "根据提问选择讲设置、指标差异或失败原因，不全部朗读。",
    "repair-heldout-live.json：summary / records；论文第 6 章",
    backup=True,
)
table(
    s,
    ["策略", "流程成功", "追加检查通过*", "平均累计 Token", "角色 / 后续反馈"],
    [
        [
            k,
            f"{summary[k]['verified']}/8",
            f"{summary[k]['independently_passed']}/8",
            f"{summary[k]['mean_tokens']:,.0f}",
            desc,
        ]
        for k, desc in [
            ("single", "Worker / 执行"),
            ("team", "三角色 / 审查"),
            ("verified", "三角色 / 执行 + 审查"),
        ]
    ],
    [1.6, 1.8, 2.4, 2.45, 3.98],
    row_h=0.65,
    font=16,
)
txt(
    s,
    "设置：python-dotenv v1.1.1；deepseek-v4-flash；temperature=0；每响应最多 2,048 Token。\n预算：3 次尝试、18 次调用、60,000 Token 请求前阈值、180 秒流程、60 秒命令。\n知识：Skill 开启、跨任务 Memory 关闭；8 个留出人工缺陷，每条件仅运行一次。",
    0.72,
    4.6,
    11.95,
    1.2,
    16,
)
txt(
    s,
    "* 18 个可用补丁的追加检查均通过；其余 6 次无补丁，未执行追加检查，不标成测试失败。",
    0.72,
    6.03,
    11.95,
    0.55,
    15,
    fill=RUST,
)

# 20 backup
s = new(
    "备份 B：状态与公开入口契约",
    "技术追问备用 · 不计入主讲时间",
    0,
    "成功出口只有 verified。baseline_passed 表示没有建立修复前失败，environment_error 和 timeout 区分环境及流程截止，no_progress 表示没有有效变化，其他状态保留失败原因。CLI 仅在 verified 时返回成功退出码；SDK 调用者需要检查报告状态；Runtime 把非成功修复映射为错误，同时保留原有任务领取、租约与取消语义。任务队列 ID 与修复运行 ID 是两种标识，不能混用。",
    "有实现追问时使用；invalid_patch 是尝试级类别，不是表中的运行终态。",
    "agent/repair.py；entrypoints/cli.py；runtime/api.py / tasks.py",
    backup=True,
)
table(
    s,
    ["状态", "含义"],
    [
        ["verified", "固定测试通过，所需交接完成，导出 candidate.patch"],
        ["baseline_passed", "基线已通过，没有建立成功修复"],
        ["environment_error", "执行环境异常或单命令超时"],
        ["no_progress", "空候选或连续相同候选"],
        ["attempts_exhausted", "尝试数耗尽"],
        ["budget_exhausted", "调用 / Token 请求前阈值触发"],
        ["timeout / canceled / error", "流程截止 / 取消 / 其他异常"],
    ],
    [4.3, 7.93],
    row_h=0.49,
    font=15,
)
txt(
    s,
    "CLI：仅 verified → exit 0；REPL：/repair；SDK：QueryEngine.repair，调用方检查 status。\nRuntime：mode=repair；非成功报告映射为 error；取消状态不被迟到结果覆盖。",
    0.72,
    6.0,
    11.95,
    0.65,
    16,
    fill=ACCENT,
)

# 21 backup
s = new(
    "备份 C：关键文献与材料位置",
    "技术追问备用 · 题名及出版信息来自论文参考文献库",
    0,
    "这些文献分别对应工具交互、角色组织、程序修复和补丁评估。展示时不需要逐项念，老师询问依据时指出对应方向即可。完整二十二项学术引用在论文参考文献中，源码、归档结果和英文论文的位置也已经列在页面底部。",
    "如需展示完整论文，打开 docs/thesis/latex/build/main.pdf；不把文献结果当作本系统实验结果。",
    "docs/thesis/latex/references.bib；docs/thesis/en/；eval/evidence/",
    backup=True,
)
references = [
    "[1] Yao et al. ReAct: Synergizing Reasoning and Acting in Language Models. ICLR, 2023.",
    "[2] Yang et al. SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering. NeurIPS 37, 2024.",
    "[3] Wu et al. AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversations. COLM, 2024.",
    "[4] Gazzola et al. Automatic Software Repair: A Survey. IEEE TSE, 45(1): 34–67, 2019.",
    "[5] Yu et al. Alleviating Patch Overfitting with Automatic Test Generation: A Study of Feasibility and Effectiveness for the Nopol Repair System. EMSE, 24(1): 33–67, 2019.",
    "[6] Ye et al. Automated Patch Assessment for Program Repair at Scale. EMSE, 26(2), Article 20, 2021.",
]
for i, ref in enumerate(references):
    txt(s, ref, 0.72, 1.68 + i * 0.62, 11.95, 0.57, 14)
txt(
    s,
    "代码：src/yecoding/agent/repair.py；sandbox/\n论文：docs/thesis/en/；docs/thesis/latex/build/main.pdf\n证据：eval/evidence/repair-verification.json；repair-heldout-live.json",
    0.72,
    5.67,
    11.95,
    0.94,
    16,
    fill=ACCENT,
)


def write_notes():
    total = sum(n["seconds"] for n in notes if not n["backup"])
    output = [
        "# 第一阶段成果汇报：逐页口播稿",
        "",
        f"主讲 18 页，建议用时 **{total // 60} 分 {total % 60} 秒**；第 19–21 页为问答备份，不计入主讲时间。",
        "",
        "中文主讲，专业名词按页上英文读法即可。以下口播可直接使用，不必朗读页脚路径、全部代码或每项指标。PPT 同时内嵌相同讲稿至备注。",
        "",
        "## 汇报口径",
        "",
        "- 第一阶段重点：完整核心设计、实际代码和英文论文第 1–5 章。已有后半实验只作为初步可行性证据。",
        "- 未将已有平台全部称为从零开发；区分现有基础、修复新增和入口接线。",
        "- 功能回归及模型结果归档于 2026-10-20；本次制作材料未重跑业务测试或模型实验。",
        "- 不预设多角色优于单角色；不把测试通过说成语义完全正确；不把容器说成绝对安全。",
        "- 主讲 18 页结束后停留提问，不主动翻备份页。",
        "",
        "## 快速导航",
        "",
        "| 页码 | 内容 | 建议时长 |",
        "| --- | --- | --- |",
    ]
    for i, item in enumerate(notes, 1):
        output.append(
            f"| {i:02d} | {item['title']} | {'备份' if item['backup'] else str(item['seconds']) + ' 秒'} |"
        )
    elapsed = 0
    for i, item in enumerate(notes, 1):
        duration = (
            "问答备用"
            if item["backup"]
            else f"{item['seconds']} 秒；累计 {(elapsed + item['seconds']) // 60:02d}:{(elapsed + item['seconds']) % 60:02d}"
        )
        output.extend(
            [
                "",
                f"## 第 {i:02d} 页：{item['title']}",
                "",
                f"**时长：{duration}**",
                "",
                "### 口播",
                "",
                item["script"],
                "",
                "### 指示与切换",
                "",
                item["cue"],
            ]
        )
        if item["source"]:
            output.extend(["", f"**依据：** {item['source']}"])
        if not item["backup"]:
            elapsed += item["seconds"]
    output.extend(
        [
            "",
            "## 常见追问的简短回答",
            "",
            "### 为什么选多智能体，而不是单 Agent？",
            "",
            "角色分工的动机是分离规划、修改和检查，并使交接可审计；是否改善修复质量是待验证问题。目前小样本下单角色完成数更高，多角色有明显预算开销，所以不能声称多角色已经胜出。",
            "",
            "### Verifier 说通过就算成功吗？",
            "",
            "不是。固定测试由程序执行，审查文字不能覆盖失败测试。多角色模式还要求审查交接完成，因此测试通过但审查超预算也可能使工作流失败。",
            "",
            "### 这是不是把三个 Prompt 连在一起？",
            "",
            "不只是。角色有不同工具注册表和工作区，候选从实际字节生成，固定测试及共享预算由程序控制，失败和补丁被持久记录。三个角色可以使用同一模型，当前顺序交接，不涉及并行合并。",
            "",
            "### 160 passed 代表多少真实模型任务？",
            "",
            "这是工程测试数量：134 项原有测试、25 项修复测试、1 项快照回归。修复分支主要由脚本模型驱动并使用真实 Docker。真实模型对比是另一个口径，共 24 次运行。",
            "",
            "### 论文和代码哪个是最新依据？",
            "",
            "运行行为与可核查源码优先。论文和 PPT 依据当前源码及归档证据组织；未来代码变化需要同步更新设计与指标，归档结果不能冒充新版本测试。",
            "",
            "## 第 08 页完整候选检查节选",
            "",
            "```python",
            candidate_code,
            "```",
            "",
            "## 现场材料位置",
            "",
            "- 演示文稿：`docs/thesis/presentation/stage1_report.pptx`",
            "- PDF 预览：`docs/thesis/presentation/stage1_report.pdf`（实际 PPTX 转换）",
            "- 英文论文：`docs/thesis/latex/build/main.pdf`",
            "- 核心编排：`src/yecoding/agent/repair.py`",
            "- 工作区与容器：`src/yecoding/sandbox/workspace.py`、`docker.py`",
            "- 真实补丁案例：`" + patch_path + "`",
            "",
            "不建议临场运行真实模型来保证展示节奏；可直接打开归档补丁、报告和论文核对。",
            "",
        ]
    )
    (OUT / "stage1_speaker_notes.md").write_text("\n".join(output))


def audit_structure():
    violations = []
    for i, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if (
                shape.left < 0
                or shape.top < 0
                or shape.left + shape.width > prs.slide_width + 100
                or shape.top + shape.height > prs.slide_height + 100
            ):
                violations.append({"slide": i, "shape": shape.name, "issue": "outside slide"})
    if violations:
        raise ValueError(violations)
    return {
        "slides": len(prs.slides),
        "main_slides": 18,
        "backup_slides": 3,
        "main_seconds": sum(n["seconds"] for n in notes),
        "text_boxes": len(layout_checks),
        "geometry_violations": violations,
        "sources_sha256": sources,
        "scope": "Document generation only; archived business/model results, not rerun.",
    }


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    audit = audit_structure()
    prs.save(OUT / "stage1_report.pptx")
    write_notes()
    (OUT / "build_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in audit.items() if k != "sources_sha256"}, ensure_ascii=False, indent=2
        )
    )
