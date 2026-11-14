# -*- coding: utf-8 -*-
"""Clickable citations for the generated Word manuscript.

Two kinds of navigation are inserted directly at the OOXML level, because
python-docx has no first-class API for either:

  * internal  -- `w:hyperlink w:anchor="bib_ref_N"` in the body, resolved
                 against a `w:bookmarkStart` placed on reference entry N.
  * external  -- `w:hyperlink r:id="rIdX"` pointing at doi.org / arxiv.org,
                 where rIdX is a real relationship on the document part.

Fake links (blue text with no target) are worse than no links at all, so every
helper here writes a real target and the acceptance script re-opens the .docx
to prove each anchor resolves.
"""
from __future__ import annotations

import itertools

from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

LINK_COLOR = "1155CC"
FONT = "Times New Roman"

_bm_id = itertools.count(9001)


def _run(text, size, color, underline, bold):
    """A minimal w:r whose rPr children follow the schema order."""
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), FONT)
    rPr.append(rFonts)
    if bold:
        rPr.append(OxmlElement("w:b"))
    if color:
        c = OxmlElement("w:color")
        c.set(qn("w:val"), color)
        rPr.append(c)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(int(round(size * 2))))
    rPr.append(sz)
    szcs = OxmlElement("w:szCs")
    szcs.set(qn("w:val"), str(int(round(size * 2))))
    rPr.append(szcs)
    if underline:
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rPr.append(u)
    r.append(rPr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r


def bookmark_start(paragraph, name):
    """Open a bookmark range at the start of the paragraph. Returns its id."""
    bid = str(next(_bm_id))
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), bid)
    start.set(qn("w:name"), name)
    p = paragraph._p
    # bookmarkStart must follow pPr, never precede it.
    if p.pPr is not None:
        p.pPr.addnext(start)
    else:
        p.insert(0, start)
    return bid


def bookmark_end(paragraph, bid):
    """Close the range so the anchor covers the whole entry, not an empty run."""
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), bid)
    paragraph._p.append(end)


def add_bookmark(paragraph, name):
    """Empty anchor. Kept for one-shot use; prefer start/end around content."""
    bid = bookmark_start(paragraph, name)
    bookmark_end(paragraph, bid)
    return name


def add_internal_link(paragraph, text, anchor, size=10, color=LINK_COLOR,
                      underline=False):
    """Click-through from a citation number to its bibliography entry."""
    h = OxmlElement("w:hyperlink")
    h.set(qn("w:anchor"), anchor)
    h.set(qn("w:history"), "1")
    h.append(_run(text, size, color, underline, False))
    paragraph._p.append(h)


def add_external_link(paragraph, text, url, size=10, color=LINK_COLOR,
                      underline=True):
    """Click-through from a bibliography entry to doi.org / arxiv.org."""
    r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), r_id)
    h.set(qn("w:history"), "1")
    h.append(_run(text, size, color, underline, False))
    paragraph._p.append(h)


def audit(docx_path):
    """Re-open the saved file and report link integrity.

    Returns dict with resolved/unresolved anchor counts, external relationship
    count, and the list of dangling anchors (should always be empty).
    """
    import re
    import zipfile
    from docx import Document

    d = Document(str(docx_path))
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    bookmarks = set()
    anchors = []
    for p in d.paragraphs:
        for bm in p._p.iter(W + "bookmarkStart"):
            name = bm.get(W + "name")
            if name and name.startswith("bib_ref_"):
                bookmarks.add(name)
        for h in p._p.iter(W + "hyperlink"):
            a = h.get(W + "anchor")
            if a and a.startswith("bib_ref_"):
                anchors.append(a)
    dangling = sorted({a for a in anchors if a not in bookmarks})

    # external hyperlinks live as relationships, not in the paragraph XML text
    with zipfile.ZipFile(docx_path) as z:
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
    ext = re.findall(r'Type="[^"]*/hyperlink"[^>]*Target="([^"]+)"', rels)
    ext += re.findall(r'Target="([^"]+)"[^>]*Type="[^"]*/hyperlink"', rels)
    return {
        "bookmarks": len(bookmarks),
        "anchors": len(anchors),
        "dangling": dangling,
        "external": len(set(ext)),
        "external_urls": sorted(set(ext)),
    }
