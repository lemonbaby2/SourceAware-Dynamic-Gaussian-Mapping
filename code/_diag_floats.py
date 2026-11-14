# -*- coding: utf-8 -*-
"""One-off diagnostic: why are only some floats picked up by the Word builder?"""
import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bld", HERE / "build_extended_docx.py")
m = importlib.util.module_from_spec(spec)
sys.modules["bld"] = m
spec.loader.exec_module(m)

tex = m.TEX.read_text(encoding="utf-8")
ab, kw, chunks, ph = m.extract_blocks(tex)
print("placeholders:", Counter(v[0] for v in ph.values()))
for v in ph.values():
    if v[0] == "figure":
        print("  FIG", v[1], "|", v[2])
    elif v[0] == "table":
        print("  TAB", v[1])

body = tex.split("\\begin{document}", 1)[1].split("\\bibliographystyle", 1)[0]
for pat, name in ((r"\\begin\{figure\}", "begin figure"),
                  (r"\\begin\{figure\*\}", "begin figure*"),
                  (r"\\end\{figure\}", "end figure"),
                  (r"\\end\{figure\*\}", "end figure*"),
                  (r"\\begin\{table\}", "begin table"),
                  (r"\\begin\{table\*\}", "begin table*"),
                  (r"\\includegraphics", "includegraphics")):
    print(f"{name:18s}", len(re.findall(pat, body)))

print("\nchunks containing a leftover figure:", sum(1 for c in chunks if "figure" in c))
for c in chunks:
    if "figure" in c and len(c) > 5:
        print("  ->", c[:90].replace("\n", " "))
