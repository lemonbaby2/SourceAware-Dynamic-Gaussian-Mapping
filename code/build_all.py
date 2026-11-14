# -*- coding: utf-8 -*-
"""Rebuild the whole manuscript from the stored experiment results.

Order matters: bibliography -> tables + prose from data -> related work ->
figures -> LaTeX (for citation numbers) -> Word -> acceptance check.
Every step is idempotent, so the script can be re-run after new GPU runs land.
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LATEX = HERE / "latex"


def sh(cmd, cwd=None, quiet=True):
    r = subprocess.run(cmd, cwd=str(cwd or HERE), shell=True,
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print(f"!! failed: {cmd}")
        print((r.stdout or "")[-1500:])
        print((r.stderr or "")[-1500:])
        raise SystemExit(1)
    if not quiet:
        print(r.stdout)
    return r.stdout


def step(name):
    print(f"\n=== {name} ===", flush=True)


def main():
    py = sys.executable
    # figures need matplotlib, which lives in the conda env used for the runs
    cand = Path("D:/Anaconda/python.exe")
    fig_py = str(cand) if cand.exists() else py
    cands = [LATEX / "main.tex.pristine", LATEX / "main.tex.bak_before_expand"]
    prist = next((c for c in cands if c.exists()), cands[0])

    step("bibliography from verified records")
    sh(f'"{py}" make_bib.py', quiet=False)

    step("restore pristine LaTeX source")
    if prist.exists():
        shutil.copy2(prist, LATEX / "main.tex")
        print("restored", prist.name)
    else:
        print("!! pristine backup missing; editing current main.tex in place")

    step("tables and prose from experiment JSON")
    sh(f'"{py}" rewrite_manuscript.py', quiet=False)

    step("related work")
    sh(f'"{py}" expand_related.py', quiet=False)

    step("figures")
    sh(f'"{fig_py}" make_figures_ext.py', quiet=False)
    sh(f'"{py}" inject_figures.py', quiet=False)

    step("LaTeX compile")
    for _ in range(2):
        sh("pdflatex -interaction=nonstopmode main.tex", cwd=LATEX)
    sh("bibtex main", cwd=LATEX)
    for _ in range(2):
        sh("pdflatex -interaction=nonstopmode main.tex", cwd=LATEX)
    log = (LATEX / "main.log").read_text(encoding="utf-8", errors="ignore")
    import re
    pages = re.search(r"Output written on main\.pdf \((\d+) pages", log)
    print("PDF pages:", pages.group(1) if pages else "unknown")

    step("Word")
    sh(f'"{py}" build_extended_docx.py', quiet=False)

    step("acceptance check")
    r = subprocess.run(f'"{py}" verify_final.py', cwd=str(HERE), shell=True,
                       capture_output=True, text=True, errors="replace")
    print(r.stdout)
    print(r.stderr[-800:] if r.returncode else "")


if __name__ == "__main__":
    main()
