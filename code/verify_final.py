# -*- coding: utf-8 -*-
"""Final acceptance check for the delivered manuscript.

Checks the properties the revision was asked to guarantee, and prints a single
PASS/FAIL table so a reviewer does not have to trust a summary.
"""
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extended"
TEX = EXT / "latex" / "main.tex"
BIB = EXT / "latex" / "references.bib"
AUX = EXT / "latex" / "main.aux"
DOCX = ROOT / "SourceAware_Dynamic_Gaussian_Mapping_完整扩展稿_16-20页.docx"
DOCX_REV = ROOT / "SourceAware_Dynamic_Gaussian_Mapping_完整扩展稿_16-20页_修订版.docx"
DOCX_LINKED = ROOT / "SourceAware_Dynamic_Gaussian_Mapping_完整扩展稿_18页_引用可跳转.docx"
STATS = ROOT / "manuscript_stats.json"

TARGET = {"refs_min": 42, "figs_min": 12, "appendix": 3, "contrib": 5,
          "pages": (16, 20)}


def rows():
    tex = TEX.read_text(encoding="utf-8")
    bib = BIB.read_text(encoding="utf-8")
    keys = re.findall(r"@\w+\{([^,]+),", bib)
    cited = set()
    for grp in re.findall(r"\\cite\{([^}]+)\}", tex):
        cited |= {k.strip() for k in grp.split(",")}
    figs = len(re.findall(r"\\includegraphics", tex))
    apps = len(re.findall(r"\\section\{", tex.split("\\appendices", 1)[1].split("\\bibliographystyle")[0])) \
        if "\\appendices" in tex else 0
    contrib_zone = tex.split("\\subsection{Contributions}", 1)
    contrib = len(re.findall(r"\\item", contrib_zone[1].split("\\end{enumerate}", 1)[0])) \
        if len(contrib_zone) > 1 else 0
    out = []

    def add(name, value, ok, note=""):
        out.append((name, value, "PASS" if ok else "FAIL", note))

    add("references in bib", len(keys), len(keys) >= TARGET["refs_min"], f"min {TARGET['refs_min']}")
    add("references cited", len(set(keys) & cited), set(keys) <= cited, "every entry must be cited")
    add("figures", figs, figs >= TARGET["figs_min"], f"min {TARGET['figs_min']}")
    add("appendix sections", apps, apps == TARGET["appendix"], f"target {TARGET['appendix']}")
    add("contribution bullets", contrib, contrib == TARGET["contrib"], f"target {TARGET['contrib']}")

    specs = EXT / "tables_data.json"
    if specs.exists():
        t = json.loads(specs.read_text(encoding="utf-8"))
        add("ablation rows", len(t["tab:ablation"]["rows"]),
            len(t["tab:ablation"]["rows"]) >= 8, "capacity + budget + noise + morphology")
        add("per-seed rows", len(t["tab:seedfull"]["rows"]),
            len(t["tab:seedfull"]["rows"]) >= 15, "3 modes x seeds")
        add("'n/a' left in tables", "n/a" in str(t), "n/a" not in str(t), "no unfilled ablation cells")

    if STATS.exists():
        n = json.loads(STATS.read_text(encoding="utf-8")).get("n_seed")
        add("main seeds", n, (n or 0) >= 5, "5+ independent seeds")

    for bad in ("XXX", "TODO", "Insert New Name", "??"):
        hit = bad in tex
        add(f"placeholder '{bad}'", "absent" if not hit else "FOUND", not hit)

    # double braces are only legal in \graphicspath{{...}}
    stray = [ln for ln in tex.splitlines()
             if "{{" in ln and not ln.strip().startswith("\\graphicspath")]
    add("stray '{{' outside graphicspath", len(stray), not stray,
        stray[0][:40] if stray else "")

    # abstract numbers must equal the measured aggregate
    if STATS.exists():
        s = json.loads(STATS.read_text(encoding="utf-8"))["stats"]
        abs_txt = tex.split("\\begin{abstract}", 1)[1].split("\\end{abstract}")[0]
        p1 = f"{s['dyn-mask']['psnr'][0]:.2f}"
        p0 = f"{s['naive']['psnr'][0]:.2f}"
        add("abstract PSNR matches data", f"{p0}/{p1}", p0 in abs_txt and p1 in abs_txt,
            "abstract must not drift from experiment JSON")

    # delivered Word file: the link-enabled build is authoritative; other
    # copies are only a fallback so a stale file cannot mask a regression
    if DOCX_LINKED.exists():
        docx = DOCX_LINKED
    else:
        cands = [p for p in (DOCX, DOCX_REV) if p.exists()]
        cands += [p for p in ROOT.glob("*.docx") if "SourceAware" in p.name and p not in cands]
        docx = max(cands, key=lambda p: p.stat().st_mtime) if cands else None
    if docx is not None and docx.exists():
        with zipfile.ZipFile(docx) as z:
            imgs = [n for n in z.namelist() if n.startswith("word/media")]
        from docx import Document  # local vendor copy via sys.path
        d = Document(str(docx))
        refs = [p.text for p in d.paragraphs if re.match(r"^\[\d+\]", p.text)]
        add("docx images", len(imgs), len(imgs) >= TARGET["figs_min"], docx.name)
        add("docx tables", len(d.tables), len(d.tables) >= 5)
        add("docx references", len(refs), len(refs) >= TARGET["refs_min"], f"min {TARGET['refs_min']}")
        # nothing from the LaTeX source may leak into the Word text
        leak = []
        for p in d.paragraphs:
            t = p.text
            if re.search(r"\\[a-zA-Z]{2,}", t) or re.search(r"\b(?:sec|tab|fig|eq):[a-z]", t):
                leak.append(t[:60])
        add("LaTeX leakage in docx", len(leak), not leak, leak[0] if leak else "")
        # a literal backslash in the bibliography means an escape was never
        # resolved for the Word target (e.g. \& inside a title)
        bad_refs = [t for t in refs if "\\" in t]
        add("escapes left in references", len(bad_refs), not bad_refs,
            bad_refs[0][:40] if bad_refs else "")
        # clickable citations: body [n] -> bookmark on reference n, plus doi/arxiv URLs
        try:
            from docx_links import audit
            a = audit(docx)
            body_cites = sum(len(g.split(",")) for g in re.findall(r"\\cite\{([^}]+)\}", tex))
            add("docx citation anchors", a["anchors"], a["anchors"] == body_cites,
                f"body \\cite numbers = {body_cites}")
            add("docx ref bookmarks", a["bookmarks"], a["bookmarks"] == len(refs),
                f"one per entry = {len(refs)}")
            add("dangling anchors", len(a["dangling"]), not a["dangling"],
                a["dangling"][0] if a["dangling"] else "every anchor resolves")
            add("external doi/arxiv links", a["external"], a["external"] >= len(refs) - 1,
                "all but DOI-less books")
        except Exception as e:
            add("docx citation anchors", "n/a", False, str(e)[:60])
        try:
            from pages import page_count
            pages, words = page_count(docx)
            lo, hi = TARGET["pages"]
            add("docx pages", pages, lo <= pages <= hi, f"target {lo}-{hi}, {words} words")
        except Exception as e:
            add("docx pages", "n/a", False, str(e)[:60])
    return out


def main():
    sys.path.insert(0, str(ROOT / "vendor"))
    sys.path.insert(0, str(EXT))
    out = rows()
    w = max(len(r[0]) for r in out)
    print(f"{'check'.ljust(w)}  {'value':>10}  result  note")
    print("-" * (w + 34))
    for name, value, res, note in out:
        print(f"{name.ljust(w)}  {str(value):>10}  {res:6s}  {note}")
    bad = [r for r in out if r[2] != "PASS"]
    print("-" * (w + 34))
    print("ALL PASS" if not bad else f"{len(bad)} FAILED")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
