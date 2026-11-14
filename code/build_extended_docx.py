from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from latex2mathml.converter import convert
from lxml import etree


TEX = Path(__file__).parent / "latex" / "main.tex"
AUX = Path(__file__).parent / "latex" / "main.aux"
FIG = Path(__file__).parent / "figures"
OUT = ROOT / "SourceAware_Dynamic_Gaussian_Mapping_完整扩展稿_18页_引用可跳转.docx"
MML_XSL = Path(r"C:\Program Files\Microsoft Office\root\Office16\MML2OMML.XSL")

FIGURES = {
    "fig:overview": ("method_overview.png", "Fig. 1. Source-aware pooling and its connection to mapping. Derived motion cues share one family budget; geometry receives a separate budget. The mapping experiment uses oracle masks and does not validate a learned mask front end."),
    "fig:fusion": ("fusion_stress_extended.png", "Fig. 2. Exact-replication stress test over ten seeds. Error bars are sample standard deviations. Fixed channel multiplication becomes overconfident; the source-family pool is invariant."),
    "fig:mapping": ("mapping_summary.png", "Fig. 3. Held-out mapping summary over three seeds. Static-only initialization helps, while loss masking supplies the larger and more stable reduction in transient contamination."),
    "fig:perview": ("per_view_results.png", "Fig. 4. Per-view held-out results averaged over three seeds. Loss masking is especially important for views 8 and 11."),
    "fig:qual": ("qualitative_view8.png", "Fig. 5. Qualitative held-out comparison for view 8, seed 0. Columns show the dynamic input, Gaussian render, and static ground truth; rows show the three training configurations."),
    "fig:resources": ("resource_profile.png", "Fig. 6. Recorded optimization time, render time, and peak allocated GPU memory. These are controlled-component measurements, not end-to-end SLAM throughput."),
}

TABLES = {
    "tab:fusion": (
        "TABLE I. Fusion results at one and eight motion copies. Mean ± sample SD over ten seeds.",
        ["Copies", "Method", "NLL", "ECE10"],
        [
            ["1", "Fixed product", "0.4788±0.0023", "0.0148±0.0019"],
            ["1", "Channel mean", "0.4788±0.0023", "0.0148±0.0019"],
            ["1", "Family pool", "0.4788±0.0023", "0.0148±0.0019"],
            ["8", "Fixed product", "1.0455±0.0210", "0.1787±0.0020"],
            ["8", "Channel mean", "0.4930±0.0023", "0.0232±0.0031"],
            ["8", "Family pool", "0.4788±0.0023", "0.0148±0.0019"],
        ],
    ),
    "tab:mapping": (
        "TABLE II. Held-out mapping results. Mean ± sample SD over three seeds.",
        ["Configuration", "Static PSNR", "Ghost L1", "SSIM"],
        [
            ["All pixels", "27.899±0.281", "0.0383±0.0045", "0.8880±0.0031"],
            ["Static init.", "29.338±0.548", "0.0270±0.0103", "0.8978±0.0005"],
            ["Init. + mask", "31.647±0.217", "0.0058±0.0003", "0.9088±0.0006"],
        ],
    ),
    "tab:fusionfull": (
        "TABLE III. Complete evidence-replication summary over ten seeds.",
        ["Copies", "Method", "NLL", "Brier", "ECE10", "F1"],
        [
            ["1", "Fixed product", "0.4788±0.0023", "0.1578±0.0009", "0.0148±0.0019", "0.6388±0.0039"],
            ["1", "Channel mean", "0.4788±0.0023", "0.1578±0.0009", "0.0148±0.0019", "0.6388±0.0039"],
            ["1", "Family pool", "0.4788±0.0023", "0.1578±0.0009", "0.0148±0.0019", "0.6388±0.0039"],
            ["2", "Fixed product", "0.5073±0.0038", "0.1634±0.0010", "0.0639±0.0030", "0.6373±0.0036"],
            ["2", "Channel mean", "0.4814±0.0023", "0.1587±0.0009", "0.0157±0.0022", "0.6373±0.0036"],
            ["2", "Family pool", "0.4788±0.0023", "0.1578±0.0009", "0.0148±0.0019", "0.6388±0.0039"],
            ["4", "Fixed product", "0.6520±0.0095", "0.1811±0.0012", "0.1282±0.0022", "0.6334±0.0040"],
            ["4", "Channel mean", "0.4873±0.0023", "0.1610±0.0009", "0.0190±0.0028", "0.6334±0.0040"],
            ["4", "Family pool", "0.4788±0.0023", "0.1578±0.0009", "0.0148±0.0019", "0.6388±0.0039"],
            ["8", "Fixed product", "1.0455±0.0210", "0.2035±0.0015", "0.1787±0.0020", "0.6295±0.0040"],
            ["8", "Channel mean", "0.4930±0.0023", "0.1631±0.0009", "0.0232±0.0031", "0.6295±0.0040"],
            ["8", "Family pool", "0.4788±0.0023", "0.1578±0.0009", "0.0148±0.0019", "0.6388±0.0039"],
        ],
    ),
    "tab:seedfull": (
        "TABLE IV. Per-seed held-out mapping results and resource measurements.",
        ["Mode", "Seed", "Static PSNR", "Ghost L1", "SSIM", "Train s", "Render ms"],
        [
            ["All pixels", "0", "28.214", "0.0336", "0.8903", "121.58", "25.702"],
            ["All pixels", "1", "27.807", "0.0388", "0.8892", "107.48", "25.689"],
            ["All pixels", "2", "27.676", "0.0426", "0.8844", "107.49", "25.668"],
            ["Static init.", "0", "29.402", "0.0359", "0.8983", "107.62", "25.712"],
            ["Static init.", "1", "29.852", "0.0158", "0.8975", "107.48", "25.673"],
            ["Static init.", "2", "28.761", "0.0294", "0.8975", "107.46", "25.767"],
            ["Init. + mask", "0", "31.400", "0.0061", "0.9081", "107.62", "25.796"],
            ["Init. + mask", "1", "31.734", "0.0055", "0.9090", "107.61", "25.746"],
            ["Init. + mask", "2", "31.808", "0.0058", "0.9093", "107.59", "25.672"],
        ],
    ),
    "tab:viewfull": (
        "TABLE V. Per-view mean ± sample SD over three seeds.",
        ["View", "Mode", "Static PSNR", "Ghost L1"],
        [
            ["2", "All pixels", "27.258±0.214", "0.0079±0.0019"], ["2", "Static init.", "28.748±0.309", "0.0061±0.0007"], ["2", "Init. + mask", "29.405±0.213", "0.0035±0.0002"],
            ["5", "All pixels", "27.324±0.506", "0.0292±0.0111"], ["5", "Static init.", "29.054±0.342", "0.0525±0.0360"], ["5", "Init. + mask", "30.102±0.196", "0.0053±0.0004"],
            ["8", "All pixels", "31.982±0.110", "0.0717±0.0082"], ["8", "Static init.", "31.614±1.780", "0.0394±0.0083"], ["8", "Init. + mask", "33.649±0.421", "0.0094±0.0011"],
            ["11", "All pixels", "25.031±0.383", "0.0446±0.0028"], ["11", "Static init.", "27.937±0.155", "0.0099±0.0019"], ["11", "Init. + mask", "33.434±0.478", "0.0050±0.0003"],
        ],
    ),
    "tab:failures": (
        "TABLE VI. Failure modes and diagnostics for a source-aware dynamic Gaussian mapper.",
        ["Stage", "Failure", "Symptom", "Diagnostic"],
        [
            ["Motion", "Camera/occlusion motion", "Dynamic edges or fast rotations", "Flow validity and occlusion strata"],
            ["Geometry", "Depth-scale drift", "Static planes disagree", "Per-sequence scale plots"],
            ["Provenance", "Derived cue split", "Confidence changes on duplication", "Replication/family sweeps"],
            ["Calibration", "Leakage/domain shift", "Held-out NLL rises", "Sequence-level calibration"],
            ["Fusion", "Weak family overweighted", "Precision/recall collapse", "Single-family ablations"],
            ["Init.", "False negatives seed map", "Persistent colored blobs", "Mask-error injection"],
            ["Optimization", "Dynamic loss remains", "Gaussians stretch/recolor", "Init/loss ablations"],
            ["Tracking", "Static texture removed", "ATE failures", "Inliers and FP sweep"],
            ["Evaluation", "Wrong target metric", "PSNR falls as ghosts vanish", "Static/clean metrics"],
            ["Timing", "Renderer called system FPS", "Front end excluded", "Synchronized stage latency"],
        ],
    ),
    "tab:claims": (
        "TABLE VII. Claim status for the extended manuscript.",
        ["Claim", "Status", "Evidence or missing requirement"],
        [
            ["Exact copies leave the family pool unchanged", "Supported", "Proposition 1 and copy-count stress test"],
            ["Fixed multiplication becomes overconfident", "Stress-test support", "Ten seeds and rising NLL/Brier/ECE"],
            ["Oracle static initialization improves mapping", "Studied-scene support", "Three seeds and four held-out views"],
            ["Oracle loss masking adds a gain", "Studied-scene support", "Consistent paired PSNR/ghost results"],
            ["Real-image masks improve", "Not established", "Need real channels, calibration, IoU/F1/NLL/ECE"],
            ["Tracking improves", "Not established", "Need ATE/RPE and failure rate"],
            ["Metric scale is recovered", "Not established", "Need declared metric prior"],
            ["State of the art", "Not established", "Need matched official-baseline runs"],
            ["End-to-end real time", "Not established", "Need synchronized critical-path timing"],
        ],
    ),
    "tab:datasets": (
        "TABLE VIII. Proposed real-sequence and rendering evaluation matrix.",
        ["Block", "Candidate data", "Metrics", "Controls"],
        [
            ["Dynamic RGB-D", "TUM dynamic", "ATE/RPE/failures", "Inputs and alignment declared"],
            ["Challenging scenes", "BONN dynamic", "ATE/RPE/mask metrics", "Motion strata and calibration"],
            ["Held-out render", "Replica/equivalent", "PSNR/SSIM/LPIPS/ghost", "Fixed split; clean target"],
            ["Mask calibration", "Held-out labels", "NLL/Brier/ECE/IoU/F1", "Disjoint calibration sequences"],
            ["Scale", "Metric-depth data", "Scale drift/depth error", "Checkpoint and alignment named"],
            ["Efficiency", "Matched workstation", "Stage/end-to-end latency", "Synchronization and warm-up"],
        ],
    ),
}

# Tables produced by table_rows.py win over the literals above, so the Word
# output always matches the stored experiment JSON.
TDATA = Path(__file__).parent / "tables_data.json"
if TDATA.exists():
    for _label, _spec in json.loads(TDATA.read_text(encoding="utf-8")).items():
        TABLES[_label] = (_spec["caption"], _spec["header"], _spec["rows"])

try:
    from refs_render import build_refs_struct
    REFS = build_refs_struct()
except Exception as _e:  # pragma: no cover - fallback keeps the build running
    print("!! 参考文献渲染失败:", _e)
    REFS = []

from docx_links import (add_bookmark, add_external_link, add_internal_link,
                        bookmark_end, bookmark_start)

# Citation numbers are routed through a private-use sentinel so that body text
# can be split into ordinary runs and clickable anchors after LaTeX cleanup.
CITE_OPEN, CITE_CLOSE = "\ue000", "\ue001"
CITE_RE = re.compile(CITE_OPEN + "([^" + CITE_CLOSE + "]*)" + CITE_CLOSE)


def anchor_for(n):
    return f"bib_ref_{n}"


def emit_cites(text):
    r"""Turn \cite{a,b} into [<sentinel>3,7<sentinel>] before cleanup."""
    def repl(m):
        nums = [CITES.get(k.strip(), "") for k in m.group(1).split(",")]
        return CITE_OPEN + ",".join(n for n in nums if n) + CITE_CLOSE
    return re.sub(r"\\cite\{([^}]+)\}", repl, text)


def set_font(run, name="Times New Roman", size=None, bold=None, italic=None):
    run.font.name = name
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def set_columns(section, count=2, space=360):
    sect = section._sectPr
    old = sect.find(qn("w:cols"))
    if old is not None:
        sect.remove(old)
    cols = OxmlElement("w:cols")
    cols.set(qn("w:num"), str(count))
    cols.set(qn("w:space"), str(space))
    sect.append(cols)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_borders(cell, color="D9D9D9", size="4"):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        el = borders.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            borders.append(el)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), size)
        el.set(qn("w:color"), color)


def add_omml(paragraph, latex, display=True):
    latex = latex.replace("\\sigmoid", r"\operatorname{sigmoid}")
    latex = latex.replace("\\logit", r"\operatorname{logit}")
    latex = latex.replace("\\dyn", r"\mathrm{dyn}").replace("\\stat", r"\mathrm{stat}")
    latex = latex.replace("\\E", r"\mathbb{E}").replace("\\R", r"\mathbb{R}")
    latex = latex.replace("\\begin{aligned}", "").replace("\\end{aligned}", "")
    latex = latex.replace("&", "").replace("\\\\", " ")
    mml = convert(latex)
    xslt = etree.XSLT(etree.parse(str(MML_XSL)))
    omml = xslt(etree.fromstring(mml.encode("utf-8")))
    paragraph._p.append(parse_xml(etree.tostring(omml.getroot())))


def bib_maps():
    aux = AUX.read_text(encoding="utf-8", errors="ignore")
    cites = {k: v for k, v in re.findall(r"\\bibcite\{([^}]+)\}\{([^}]+)\}", aux)}
    labels = {}
    for key, val in re.findall(r"\\newlabel\{([^}]+)\}\{\{([^}]*)\}", aux):
        labels[key] = val
    return cites, labels


CITES, LABELS = bib_maps()


def clean_text(text):
    text = re.sub(r"\\cite\{([^}]+)\}", lambda m: "[" + ", ".join(CITES.get(k.strip(), "?") for k in m.group(1).split(",")) + "]", text)
    text = re.sub(r"\\eqref\{([^}]+)\}", lambda m: "(" + LABELS.get(m.group(1), "?") + ")", text)
    text = re.sub(r"\\ref\{([^}]+)\}", lambda m: LABELS.get(m.group(1), "?"), text)
    text = re.sub(r"\\text(?:bf|it)\{([^{}]*)\}", r"\1", text)
    text = text.replace("\\%", "%").replace("\\&", "&").replace("\\,", " ").replace("~", " ")
    text = text.replace("``", '“').replace("''", '”').replace("--", "-")
    text = text.replace("\\textwidth", "text width")
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = text.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", text).strip()


def append_cited_text(paragraph, text, size=10):
    """Append cleaned prose, turning every [n] citation into an internal link.

    Brackets and separators stay plain runs; only the digits are anchors, so a
    multi-citation such as [3, 7] gives two independently clickable numbers.
    """
    pos = 0
    for m in CITE_RE.finditer(text):
        if m.start() > pos:
            set_font(paragraph.add_run(text[pos:m.start()]), size=size)
        nums = [n.strip() for n in m.group(1).split(",") if n.strip()]
        if nums:
            set_font(paragraph.add_run("["), size=size)
            for i, n in enumerate(nums):
                if i:
                    set_font(paragraph.add_run(", "), size=size)
                add_internal_link(paragraph, n, anchor_for(n), size=size)
            set_font(paragraph.add_run("]"), size=size)
        pos = m.end()
    if pos < len(text):
        set_font(paragraph.add_run(text[pos:]), size=size)


def append_mixed_content(paragraph, text, size=10):
    """Append prose and inline OMML while preserving word boundaries."""
    parts = re.split(r"(\$[^$]+\$)", text)
    has_content = bool(paragraph.text or paragraph._p.xpath(".//m:oMath"))
    for part in parts:
        if not part:
            continue
        if part.startswith("$") and part.endswith("$"):
            if has_content:
                set_font(paragraph.add_run(" "), size=size)
            try:
                add_omml(paragraph, part[1:-1], display=False)
            except Exception:
                set_font(paragraph.add_run(clean_text(part[1:-1])), name="Cambria Math", size=size)
            has_content = True
            continue

        cleaned = clean_text(emit_cites(part))
        if not cleaned:
            continue
        # clean_text intentionally normalizes whitespace. Restore exactly one
        # boundary space unless the next prose fragment begins with punctuation.
        prefix = " " if has_content and not re.match(r"^[,.;:!?%)\]]", cleaned) else ""
        if prefix:
            set_font(paragraph.add_run(prefix), size=size)
        append_cited_text(paragraph, cleaned, size=size)
        has_content = True


def add_mixed_paragraph(doc, text, style=None, bullet=False):
    p = doc.add_paragraph(style=style)
    if bullet:
        p.style = doc.styles["List Bullet"]
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    append_mixed_content(p, text, size=10)
    return p


def add_caption(doc, text):
    p = doc.add_paragraph(style="Caption")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = False
    set_font(p.add_run(clean_text(text)), size=7.5)


def grab_caption(content):
    """Return the balanced caption text of a float environment."""
    i = content.find("\\caption{")
    if i < 0:
        return ""
    j = i + len("\\caption{")
    depth, buf = 1, []
    while j < len(content) and depth > 0:
        ch = content[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        buf.append(ch)
        j += 1
    return "".join(buf).strip()


def add_figure(doc, label, filename=None, caption=None, wide=None):
    """Prefer the filename and caption written in the LaTeX source.

    The FIGURES registry remains only as a fallback, so a figure added to
    main.tex appears in the .docx without a second edit here.  `wide` comes
    from the float type in the source (figure* means full text width).
    """
    if filename is None or caption is None:
        reg = FIGURES.get(label, (None, None))
        filename = filename or reg[0]
        caption = caption if caption is not None else reg[1]
    if not filename:
        print("!! figure not resolvable:", label)
        return
    path = FIG / filename
    # A figure* in the LaTeX source spans both columns. Word can only do that
    # through a single-column section, so one is opened and closed around the
    # picture; otherwise the image would overflow into the neighbouring column.
    if wide:
        set_columns(doc.add_section(WD_SECTION.CONTINUOUS), 1)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    try:
        from PIL import Image
        w, h = Image.open(path).size
        aspect = w / max(h, 1)
    except Exception:
        aspect = 2.0
    if wide is True:
        width = 6.15
    elif wide is False:
        width = 3.35
    else:
        width = 6.15 if aspect > 2.6 else (5.0 if aspect > 1.5 else 3.35)
    p.add_run().add_picture(str(path), width=Inches(width))
    add_caption(doc, caption)
    if wide:
        set_columns(doc.add_section(WD_SECTION.CONTINUOUS), 2)


def add_table(doc, label):
    caption, headers, rows = TABLES[label]
    add_caption(doc, caption)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    hdr = table.rows[0].cells
    for i, text in enumerate(headers):
        hdr[i].text = text
        set_cell_shading(hdr[i], "1F4E78")
        for run in hdr[i].paragraphs[0].runs:
            set_font(run, size=6.4, bold=True)
            run.font.color.rgb = RGBColor(255, 255, 255)
        hdr[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        hdr[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_borders(hdr[i])
    for ridx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = text
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 1 else WD_ALIGN_PARAGRAPH.CENTER
            for run in cells[i].paragraphs[0].runs:
                set_font(run, size=6.1)
            if ridx % 2:
                set_cell_shading(cells[i], "EAF2F8")
            set_cell_borders(cells[i])
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def extract_blocks(tex):
    body = tex.split("\\begin{document}", 1)[1].split("\\bibliographystyle", 1)[0]
    body = body.replace("\\maketitle", "")
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", body, re.S).group(1).strip()
    keywords = re.search(r"\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}", body, re.S).group(1).strip()
    body = re.sub(r"\\begin\{abstract\}.*?\\end\{abstract\}", "", body, flags=re.S)
    body = re.sub(r"\\begin\{IEEEkeywords\}.*?\\end\{IEEEkeywords\}", "", body, flags=re.S)
    placeholders = {}
    counter = 0
    for kind in (r"figure\*?", r"table\*?", "equation"):
        pattern = re.compile(rf"\\begin\{{{kind}\}}(.*?)\\end\{{{kind}\}}", re.S)
        while True:
            m = pattern.search(body)
            if not m:
                break
            content = m.group(1)
            token = f"@@BLOCK{counter}@@"
            if kind.startswith("figure"):
                label = re.search(r"\\label\{([^}]+)\}", content).group(1)
                inc = re.search(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", content)
                is_wide = m.group(0).startswith("\\begin{figure*}")
                placeholders[token] = ("figure", label,
                                       inc.group(1) if inc else None,
                                       grab_caption(content) or None,
                                       is_wide)
            elif kind.startswith("table"):
                label = re.search(r"\\label\{([^}]+)\}", content).group(1)
                placeholders[token] = ("table", label)
            else:
                label_m = re.search(r"\\label\{([^}]+)\}", content)
                formula = re.sub(r"\\label\{[^}]+\}", "", content).strip()
                placeholders[token] = ("equation", formula, label_m.group(1) if label_m else None)
            body = body[:m.start()] + "\n\n" + token + "\n\n" + body[m.end():]
            counter += 1
    # Labels have served their purpose once floats are tokenised; leaving them in
    # would print raw "sec:required" text next to a heading.
    body = re.sub(r"\\label\{[^}]*\}", "", body)
    body = re.sub(r"(\\(?:section|subsection)\{[^}]+\})", r"\n\n\1\n\n", body)
    body = body.replace("\\appendices", "\n\n\\appendices\n\n")
    body = re.sub(r"(\\begin\{(?:itemize|enumerate|description)\})", r"\n\n\1", body)
    body = re.sub(r"(\\end\{(?:itemize|enumerate|description)\})", r"\1\n\n", body)
    chunks = [c.strip() for c in re.split(r"\n\s*\n", body) if c.strip()]
    return abstract, keywords, chunks, placeholders


def add_footer(section):
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    footer._p.append(fld)


def build():
    tex = TEX.read_text(encoding="utf-8")
    abstract, keywords, chunks, placeholders = extract_blocks(tex)
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.top_margin = sec.bottom_margin = Inches(0.72)
    sec.left_margin = sec.right_margin = Inches(0.70)
    set_columns(sec, 1)

    for name, size, bold in [("Normal", 10, False), ("Title", 17, False), ("Heading 1", 10, True), ("Heading 2", 10, False), ("Caption", 8, False), ("List Bullet", 10, False), ("List Number", 10, False)]:
        st = doc.styles[name]
        st.font.name = "Times New Roman"
        st.font.size = Pt(size)
        st.font.bold = bold
        st.font.color.rgb = RGBColor(0, 0, 0)
        st._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "Times New Roman")
        st.paragraph_format.space_after = Pt(4.0)
        st.paragraph_format.line_spacing = 1.06
        if name.startswith("Heading"):
            st.paragraph_format.space_before = Pt(5)
            st.paragraph_format.keep_with_next = True
        for border in list(st.element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pBdr')):
            border.getparent().remove(border)
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(title.add_run("Source-Aware Evidence Pooling for Dynamic Gaussian Mapping\nA Reproducible Mechanism Study"), size=17)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run("Anonymous Authors"), size=10, italic=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_font(p.add_run("Abstract—"), size=10, bold=True)
    add_mixed_paragraph_inline(p, abstract)
    p = doc.add_paragraph()
    set_font(p.add_run("Index Terms—"), size=10, bold=True)
    set_font(p.add_run(clean_text(keywords)), size=10)

    body_sec = doc.add_section(WD_SECTION.CONTINUOUS)
    set_columns(body_sec, 2)
    section_no = 0
    subsection_letter = 0
    appendix = False
    appendix_no = 0
    eq_no = 0
    list_mode = None
    for chunk in chunks:
        if chunk == "\\appendices":
            appendix = True
            appendix_no = 0
            continue
        if chunk in placeholders:
            block = placeholders[chunk]
            if block[0] == "figure":
                add_figure(doc, block[1],
                           block[2] if len(block) > 2 else None,
                           block[3] if len(block) > 3 else None,
                           block[4] if len(block) > 4 else None)
            elif block[0] == "table":
                add_table(doc, block[1])
            else:
                eq_no += 1
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                try:
                    add_omml(p, block[1], display=True)
                except Exception:
                    set_font(p.add_run(clean_text(block[1])), name="Cambria Math", size=8)
                set_font(p.add_run(f"    ({eq_no})"), size=8)
            continue
        m = re.fullmatch(r"\\section\{(.+)\}", chunk, re.S)
        if m:
            subsection_letter = 0
            if appendix:
                appendix_no += 1
                if appendix_no in ():
                    doc.add_page_break()
                heading = f"APPENDIX {chr(64 + appendix_no)}  {clean_text(m.group(1)).upper()}"
            else:
                section_no += 1
                heading = f"{roman(section_no)}. {clean_text(m.group(1)).upper()}"
            h = doc.add_paragraph(style="Heading 1")
            h.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_font(h.add_run(heading), size=10, bold=True)
            continue
        m = re.fullmatch(r"\\subsection\{(.+)\}", chunk, re.S)
        if m:
            subsection_letter += 1
            h = doc.add_paragraph(style="Heading 2")
            set_font(h.add_run(f"{chr(64 + subsection_letter)}. {clean_text(m.group(1))}"), size=10, italic=True)
            continue
        if chunk.startswith("\\begin{itemize}") or chunk.startswith("\\begin{enumerate}"):
            ordered = chunk.startswith("\\begin{enumerate}")
            content = re.sub(r"\\begin\{(?:itemize|enumerate)\}|\\end\{(?:itemize|enumerate)\}", "", chunk)
            item_no = 0
            for item in re.split(r"\\item", content):
                if item.strip():
                    item_no += 1
                    if ordered:
                        p = doc.add_paragraph()
                        p.paragraph_format.left_indent = Inches(0.20)
                        p.paragraph_format.first_line_indent = Inches(-0.20)
                        set_font(p.add_run(f"{item_no}. "), size=10)
                        append_mixed_content(p, item.strip(), size=10)
                    else:
                        p = add_mixed_paragraph(doc, item.strip(), style="List Bullet")
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            continue
        if chunk.startswith("\\begin{description}"):
            content = re.sub(r"\\begin\{description\}|\\end\{description\}", "", chunk)
            for label, text in re.findall(r"\\item\[([^]]+)\]\s*(.*?)(?=\\item\[|$)", content, re.S):
                p = doc.add_paragraph()
                set_font(p.add_run(clean_text(label) + " "), size=9, bold=True)
                add_mixed_paragraph_inline(p, text)
            continue
        if chunk.startswith("\\textbf{Proposition"):
            p = doc.add_paragraph()
            add_mixed_paragraph_inline(p, chunk)
            continue
        if chunk.startswith("\\textit{Proof"):
            p = doc.add_paragraph()
            add_mixed_paragraph_inline(p, chunk)
            continue
        add_mixed_paragraph(doc, chunk)

    h = doc.add_paragraph(style="Heading 1")
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(h.add_run("REFERENCES"), size=10, bold=True)
    ref_size = 7.2
    for ref in REFS:
        n = ref["n"]
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.17)
        p.paragraph_format.first_line_indent = Inches(-0.17)
        p.paragraph_format.space_after = Pt(0.8)
        # Target of every in-text [n] anchor. The range spans the whole entry so
        # Word lands on the first line of the reference, not an empty spot.
        bid = bookmark_start(p, anchor_for(n))
        set_font(p.add_run(f"[{n}] "), size=ref_size)
        for text, url in ref["parts"]:
            if url:
                add_external_link(p, text, url, size=ref_size)
            else:
                set_font(p.add_run(text), size=ref_size)
        bookmark_end(p, bid)

    for section in doc.sections:
        section.page_width, section.page_height = Inches(8.5), Inches(11)
        section.top_margin = section.bottom_margin = Inches(0.72)
        section.left_margin = section.right_margin = Inches(0.70)
        pass
    add_footer(doc.sections[0])
    doc.core_properties.title = "Source-Aware Evidence Pooling for Dynamic Gaussian Mapping"
    doc.core_properties.subject = "Extended reproducible mechanism study"
    doc.core_properties.author = "Anonymous Authors"
    try:
        doc.save(OUT)
        print(OUT)
    except PermissionError:
        # Word holds a lock on the delivered file; never destroy the build.
        alt = OUT.with_name(OUT.stem + "_修订版" + OUT.suffix)
        doc.save(alt)
        print("!! 目标文件被 Word 占用，改写到:", alt)
        print(alt)


def add_mixed_paragraph_inline(paragraph, text):
    append_mixed_content(paragraph, text, size=10)


def roman(n):
    vals = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for value, numeral in vals:
        while n >= value:
            out += numeral
            n -= value
    return out


if __name__ == "__main__":
    build()
