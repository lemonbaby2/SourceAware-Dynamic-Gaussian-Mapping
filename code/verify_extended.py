from __future__ import annotations

import json
import re
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extended"
TEX = EXT / "latex" / "main.tex"
BIB = EXT / "latex" / "references.bib"
FUSION = ROOT / "experiments" / "fusion_results" / "results.json"
MAPPING = ROOT / "experiments" / "heldout_results" / "summary.json"
DOCX = ROOT / "SourceAware_Dynamic_Gaussian_Mapping_完整扩展稿_16-20页.docx"
PDF = EXT / "latex" / "main.pdf"


def pdf_pages(path: Path) -> int:
    out = subprocess.check_output(["pdfinfo", str(path)], text=True, errors="replace")
    return int(re.search(r"^Pages:\s+(\d+)", out, re.M).group(1))


def main() -> None:
    fusion = json.loads(FUSION.read_text(encoding="utf-8"))
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    rows = fusion["rows"]
    assert len(rows) == 120
    assert {(r["motion_copies"], r["method"]) for r in rows} == {
        (c, m) for c in (1, 2, 4, 8) for m in ("fixed_product", "channel_mean", "family_pool")
    }

    run_dirs = sorted((ROOT / "experiments" / "heldout_results").glob("seed*_*"))
    assert len(run_dirs) == 9
    assert all((p / "metrics.json").is_file() for p in run_dirs)
    manifest = mapping["manifest"]
    assert manifest["seeds"] == [0, 1, 2]
    assert manifest["test_ids"] == [2, 5, 8, 11]
    assert manifest["gpu"] == "NVIDIA GeForce RTX 5060 Ti"

    tex = TEX.read_text(encoding="utf-8")
    bib = BIB.read_text(encoding="utf-8")
    cite_keys = set()
    for group in re.findall(r"\\cite\{([^}]+)\}", tex):
        cite_keys.update(k.strip() for k in group.split(","))
    bib_keys = set(re.findall(r"^@\w+\{([^,]+),", bib, re.M))
    assert len(bib_keys) == 18
    assert not (cite_keys - bib_keys), sorted(cite_keys - bib_keys)
    assert not (bib_keys - cite_keys), sorted(bib_keys - cite_keys)

    assert pdf_pages(PDF) == 16
    with zipfile.ZipFile(DOCX) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
        image_count = len([n for n in zf.namelist() if n.startswith("word/media/")])
    assert image_count == 6
    assert xml.count("<m:oMath") >= 10
    assert "oracle poses" in xml and "not end-to-end SLAM results" in xml

    report = {
        "status": "pass",
        "fusion_rows": len(rows),
        "fusion_aggregate_cells": 12,
        "mapping_runs": len(run_dirs),
        "held_out_views": manifest["test_ids"],
        "bibliography_entries": len(bib_keys),
        "missing_citations": [],
        "unused_bibliography": [],
        "latex_pdf_pages": 16,
        "docx_images": image_count,
        "docx_native_equation_nodes": xml.count("<m:oMath"),
        "scope": "controlled mechanism study; oracle pose/depth/masks; no end-to-end SLAM claim",
    }
    (EXT / "verification_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
