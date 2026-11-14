# -*- coding: utf-8 -*-
"""Render the Word reference list from references.bib, ordered by the citation
numbers that LaTeX assigned in main.aux.

Hard-coding the bibliography in the Word builder was the last place where the
.docx could disagree with the .tex, so it is generated here instead.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIB = HERE / "latex" / "references.bib"
AUX = HERE / "latex" / "main.aux"

STOP_KEEP = {"de", "van", "von", "der", "den", "da", "di", "la", "le"}


def parse_bib(text):
    out = {}
    for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", text, re.S):
        typ, key, body = m.group(1).lower(), m.group(2).strip(), m.group(3)

        def field(name):
            mm = re.search(r"\n\s*" + name + r"\s*=\s*\{(.*?)\}\s*,?\s*(?=\n|$)", body, re.S)
            return mm.group(1).strip() if mm else ""
        fields = {f: field(f) for f in
                  ("author", "title", "journal", "booktitle", "publisher", "year",
                   "volume", "number", "pages", "doi", "note")}
        fields["type"] = typ
        out[key] = fields
    return out


def initials(name):
    """'Jose M. Facil' -> 'J. M. Facil'."""
    parts = [p for p in name.replace(".", ". ").split() if p]
    if len(parts) == 1:
        return parts[0]
    fam = parts[-1]
    ini = []
    for p in parts[:-1]:
        if p.lower() in STOP_KEEP:
            ini.append(p)
        else:
            ini.append(p[0].upper() + ".")
    return " ".join(ini + [fam])


def fmt_authors(raw):
    names = [n.strip() for n in re.split(r"\s+and\s+", raw) if n.strip()]
    if not names:
        return ""
    short = [initials(n) for n in names]
    if len(short) == 1:
        return short[0]
    if len(short) <= 6:
        return ", ".join(short[:-1]) + ", and " + short[-1]
    return short[0] + " et al."


LATEX_ESC = {"\\&": "&", "\\%": "%", "\\_": "_", "\\#": "#", "\\$": "$"}


def strip_braces(t):
    # make_bib.py escapes these for LaTeX; the Word list must print the glyph.
    for esc, ch in LATEX_ESC.items():
        t = t.replace(esc, ch)
    return re.sub(r"[{}]", "", t).replace("–", "–")


def render(key, f):
    au = fmt_authors(f["author"])
    title = strip_braces(f["title"]).rstrip(".")
    bits = []
    if au:
        bits.append(au + ",")
    bits.append(f"‘{title},’")
    venue = f["journal"] or f["booktitle"] or f["publisher"]
    if venue:
        bits.append(strip_braces(venue) + ",")
    if f["volume"]:
        s = f"vol. {f['volume']}"
        if f["number"]:
            s += f", no. {f['number']}"
        bits.append(s + ",")
    if f["pages"]:
        bits.append(f"pp. {f['pages']},")
    if f["year"]:
        bits.append(f["year"] + ".")
    if f["doi"]:
        bits.append(f"doi: {f['doi']}.")
    elif f["note"] and "arxiv" not in (f["journal"] or "").lower():
        bits.append(f["note"] + ".")
    return " ".join(bits).replace(",.", ".").replace(",,", ",")


ARXIV_RE = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5})(v\d+)?")


def link_target(f):
    """(visible label, url) for the clickable tail of one entry, or (None, None).

    DOI first, then an arXiv identifier already printed in the venue, then one
    carried in `note`.  Books without either stay unlinked on purpose rather
    than pointing at a URL that was never verified.
    """
    if f["doi"]:
        doi = f["doi"].strip()
        return f"doi: {doi}", "https://doi.org/" + doi
    for field in ("journal", "booktitle", "note"):
        m = ARXIV_RE.search(strip_braces(f[field] or ""))
        if m:
            return m.group(0), "https://arxiv.org/abs/" + m.group(1)
    return None, None


def ordered_keys():
    if not BIB.exists():
        return [], {}
    bib = parse_bib(BIB.read_text(encoding="utf-8"))
    order = {}
    if AUX.exists():
        for k, n in re.findall(r"\\bibcite\{([^}]+)\}\{([^}]+)\}", AUX.read_text(encoding="utf-8", errors="ignore")):
            try:
                order[k] = int(n)
            except ValueError:
                pass
    return sorted(bib, key=lambda k: (order.get(k, 10**6), k)), bib


def build_refs():
    keys, bib = ordered_keys()
    return [f"[{i}] " + render(k, bib[k]) for i, k in enumerate(keys, 1)]


def build_refs_struct():
    """Bibliography as link-aware parts.

    Each item is {'n': k, 'parts': [(text, url|None), ...]}.  The plain text is
    still produced by render(), so splitting the link out cannot change the
    wording of the entry; if the label is not literally present the entry is
    emitted as one unlinked part instead of guessing at an offset.
    """
    keys, bib = ordered_keys()
    out = []
    for i, k in enumerate(keys, 1):
        f = bib[k]
        plain = render(k, f)
        label, url = link_target(f)
        if url and label and label in plain:
            j = plain.index(label)
            parts = [(plain[:j], None), (label, url), (plain[j + len(label):], None)]
        else:
            parts = [(plain, None)]
        out.append({"n": i, "key": k, "parts": [(t, u) for t, u in parts if t]})
    return out


if __name__ == "__main__":
    rs = build_refs()
    print(len(rs), "references")
    for r in rs[:3] + rs[-2:]:
        print(r)
