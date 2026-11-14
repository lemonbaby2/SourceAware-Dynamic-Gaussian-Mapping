# -*- coding: utf-8 -*-
"""Build references.bib from the Crossref/arXiv-verified record set.

Every entry written here has been resolved against Crossref (DOI) or the arXiv
API by verify_refs_42.py.  Nothing is typed from memory: the script copies
title / venue / year / authors / DOI out of references_verified_42.json and,
for DOI records, re-queries Crossref for volume, issue and page range so the
bibliography is complete enough for IEEEtran.

Unverified candidates are dropped, not guessed.
"""
import json, re, time, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
VER = ROOT / "references_verified_42.json"
OUT = HERE / "latex" / "references.bib"
CACHE = HERE / "crossref_detail_cache.json"
UA = "SourceAwareBib/1.0 (mailto:anonymous@example.org)"

# Stable keys for entries the manuscript already cites, plus readable keys for
# everything else.  idx -> bibtex key.
KEYS = {
    1: "bescos2018dynaslam", 2: "yu2018dsslam", 3: "campos2021orb",
    4: "murartal2017orbslam2", 5: "teed2021droid", 6: "zhong2018detectslam",
    7: "bescos2021dynaslam2", 8: "kim2018staticweight", 9: "ballester2025dynamon",
    10: "kerbl2023", 11: "mildenhall2020nerf", 12: "matsuki2024",
    13: "keetha2024splatam", 14: "zhu2022nice", 15: "sucar2021imap",
    16: "huang2024photoslam", 17: "yan2024gsslam", 18: "yunus2024loopyslam",
    19: "sandstrom2023pointslam", 20: "zhu2024nicerslam", 21: "wang2023coslam",
    22: "zheng2025wildgs", 23: "xu2024dg", 24: "li2025dy3dgs",
    25: "li2025garad", 26: "wu20244dgs", 27: "yang2024deformable",
    28: "pumarola2021dnerf", 29: "jiang2024rodynslam", 30: "yuan2024ddnslam",
    31: "li2024nidslam", 32: "teed2020raft", 33: "piccinelli2024unidepth",
    34: "yang2024depth", 35: "huang2022flowformer", 36: "he2017maskrcnn",
    37: "kirillov2023sam", 38: "chen2018deeplab", 39: "dosovitskiy2015flownet",
    40: "guo2017calibration", 41: "lakshminarayanan2017ensembles",
    42: "kendall2017uncertainties", 43: "ovadia2019trust",
    44: "decarvalho2023pool", 46: "shafer1976evidence",
    48: "dong2025calsurvey",
    49: "sturm2012tum", 50: "straub2019replica",
    52: "wang2004ssim", 53: "zhang2018lpips",
}

# references_verified_42.json is the single source of truth.  Only the entry
# type of the 1976 monograph needs to be forced, because Crossref reports it
# under a reprint record whose "container title" is the book title itself.
MANUAL_FIX = {46: {"_force_book": True}}


def curl_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def detail(doi):
    """Fetch volume/issue/page and full author names for a DOI, cached on disk."""
    cache = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    if doi in cache and "authors" in cache[doi]:
        return cache[doi]
    out = {}
    try:
        m = curl_json("https://api.crossref.org/works/" + urllib.parse.quote(doi))["message"]
        names = []
        for a in m.get("author", []):
            g, f = (a.get("given") or "").strip(), (a.get("family") or "").strip()
            names.append((g + " " + f).strip() if (g or f) else "")
        out = {"volume": m.get("volume", ""), "issue": m.get("issue", ""),
               "page": m.get("page", ""), "article-number": m.get("article-number", ""),
               "type": m.get("type", ""), "publisher": m.get("publisher", ""),
               "authors": [n for n in names if n]}
    except Exception as e:
        out = {"error": str(e)[:80]}
    cache[doi] = out
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    time.sleep(0.35)
    return out


def clean_title(t):
    t = (t or "").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    t = re.sub(r"\s+", " ", t).strip()
    return t


ACRONYMS = {"3D", "4D", "RGB-D", "SLAM", "NeRF", "PSNR", "SSIM", "LiDAR", "CNN", "RNN"}


def fix_case(title):
    """Protect acronyms and mixed-case tokens from BibTeX lower-casing.

    Works on whole tokens only, so a token is never wrapped twice into
    nested braces such as {DS-{SLAM}}.
    """
    def repl(m):
        tok = m.group(0)
        caps = sum(1 for c in tok if c.isupper())
        if tok in ACRONYMS or caps >= 2:
            return "{" + tok + "}"
        return tok
    return re.sub(r"[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9]", repl, title)


def esc(t):
    t = (t or "").replace("\\", "").replace("{", "").replace("}", "")
    return t.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_") \
            .replace("#", r"\#").replace("$", r"\$")


def esc_keep_braces(t):
    """Escape LaTeX specials but keep the case-protection braces from fix_case."""
    return (t or "").replace("&", r"\&").replace("%", r"\%").replace("_", r"\_") \
                    .replace("#", r"\#").replace("$", r"\$")


def entry_type(rec):
    t = (rec.get("type") or "").lower()
    v = (rec.get("venue") or "")
    if rec.get("_force_book"):
        return "book"
    if "arxiv" in v.lower() or rec.get("source") == "arxiv":
        return "article"
    if t in ("proceedings-article", "paper-conference") or \
       re.search(r"Conference|Proceedings|Workshop|Symposium", v):
        return "inproceedings"
    if t == "book":
        return "book"
    return "article"


def author_field(rec, det):
    """Prefer full given+family names from Crossref; fall back to what we have."""
    full = det.get("authors") or []
    if full:
        return " and ".join(esc(a) for a in full)
    au = rec.get("authors") or []
    if not au:
        return "Anonymous"
    return " and ".join(esc(a) for a in au)


def build():
    d = json.loads(VER.read_text(encoding="utf-8"))
    items = {x["idx"]: x for x in d["items"]}

    entries, dropped, kept_idx = [], [], []
    for idx in sorted(KEYS):
        rec = dict(items.get(idx) or {})
        if idx in MANUAL_FIX:
            rec.update(MANUAL_FIX[idx])
        title = clean_title(rec.get("title"))
        if not title or len(title) < 6 or "supp" in title.lower():
            dropped.append((idx, "no clean title"))
            continue
        if not rec.get("verified"):
            dropped.append((idx, rec.get("drop_reason", "unverified")))
            continue

        key = KEYS[idx]
        typ = entry_type(rec)
        if idx == 46:
            rec["_force_book"] = True
            typ = "book"
        det = detail(rec["doi"]) if rec.get("doi") else {}
        fields = [("author", author_field(rec, det)),
                  ("title", "{" + esc_keep_braces(fix_case(title)) + "}")]
        venue = clean_title(rec.get("venue"))
        if typ == "inproceedings":
            fields.append(("booktitle", esc(venue)))
        elif typ == "book":
            fields.append(("publisher", esc(rec.get("publisher") or venue)))
        elif venue.lower().startswith("arxiv") and rec.get("arxiv"):
            fields.append(("journal", "arXiv preprint arXiv:" + rec["arxiv"]))
        else:
            fields.append(("journal", esc(venue)))
        if rec.get("year"):
            fields.append(("year", str(rec["year"])))
        for k in ("volume", "number", "pages"):
            v = det.get(k if k != "number" else "issue") or ""
            if v:
                fields.append((k, esc(v)))
        if det.get("article-number") and not det.get("page"):
            fields.append(("pages", esc(det["article-number"])))
        if rec.get("arxiv") and not venue.lower().startswith("arxiv"):
            fields.append(("note", "arXiv:" + rec["arxiv"]))
        if rec.get("doi"):
            fields.append(("doi", rec["doi"]))
        body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields)
        entries.append(f"@{typ}{{{key},\n{body}\n}}")
        kept_idx.append(idx)

    header = ("% references.bib -- generated by extended/make_bib.py\n"
              "% Every entry resolved against Crossref (DOI) or the arXiv API.\n"
              "% Regenerate instead of editing by hand.\n\n")
    OUT.write_text(header + "\n\n".join(entries) + "\n", encoding="utf-8")
    print(f"wrote {len(entries)} entries -> {OUT}")
    print("dropped:", dropped)
    return kept_idx


if __name__ == "__main__":
    build()
