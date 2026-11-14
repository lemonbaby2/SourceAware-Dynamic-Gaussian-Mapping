# -*- coding: utf-8 -*-
"""Single source of truth for every result table in the manuscript.

Both the LaTeX source and the Word builder read from the table specs produced
here, so a number can only appear in one place and cannot drift between the two
output formats.  Every value is computed from stored experiment JSON.
"""
import json
import statistics
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXT = ROOT / "experiments" / "extended2"
OLD = ROOT / "experiments" / "heldout_results"
MODES = ("naive", "no-dyn-data", "dyn-mask")
MODE_LABEL = {"naive": "All pixels", "no-dyn-data": "Static init.", "dyn-mask": "Init. + mask"}
ABL_PREFIX = ("pts", "iter", "noise", "soft", "dilate")


def load_runs():
    runs = []
    for d in list(EXT.glob("*/metrics.json")) + list(OLD.glob("*/metrics.json")):
        try:
            j = json.loads(d.read_text(encoding="utf-8"))
        except Exception:
            continue
        j["_dir"] = str(d.parent)
        runs.append(j)
    return runs


def is_main(r):
    tag = r.get("tag") or ""
    if tag.startswith(ABL_PREFIX):
        return False
    it = r.get("iters", r.get("iterations", 1200))
    return (it == 1200 and r.get("points", 2500) == 2500
            and r.get("mask_noise", 0) == 0 and r.get("mask_dilate", 0) == 0
            and r.get("mask_mode", "hard") == "hard")


def ms(vals, nd):
    if not vals:
        return "n/a"
    v = [float(x) for x in vals]
    m = float(np.mean(v))
    s = float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
    return f"{m:.{nd}f}±{s:.{nd}f}"


def _mean_sd(vals, nd):
    v = [float(x) for x in vals]
    m = float(np.mean(v))
    s = float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
    return m, s


def build(runs=None):
    runs = runs if runs is not None else load_runs()
    main = [r for r in runs if is_main(r) and r.get("mode") in MODES]
    by_mode = {m: [r for r in main if r.get("mode") == m] for m in MODES}
    n_seed = max((len(v) for v in by_mode.values()), default=0)

    out = {}

    # ---- main mapping table ----
    rows = []
    for m in MODES:
        rs = by_mode[m]
        if not rs:
            continue
        rows.append([MODE_LABEL[m],
                     ms([r["agg"]["psnr_static_mean"] for r in rs], 3),
                     ms([r["agg"]["ghost_residual_mean"] for r in rs], 4),
                     ms([r["agg"]["ssim_mean"] for r in rs], 4)])
    out["tab:mapping"] = {
        "caption": f"Held-out mapping results. Mean ± sample SD over {n_seed} seeds.",
        "header": ["Configuration", "Static PSNR", "Ghost L1", "SSIM"],
        "colspec": "lccc",
        "rows": rows,
    }

    # ---- ablation matrix ----
    main_mask = by_mode["dyn-mask"]
    clean_row = ["Morphology", "hard oracle (main)",
                 ms([r["agg"]["psnr_static_mean"] for r in main_mask], 2),
                 ms([r["agg"]["ghost_residual_mean"] for r in main_mask], 4),
                 str(len(main_mask))]
    groups = []
    pts = sorted({r.get("points") for r in runs if (r.get("tag") or "").startswith("pts")})
    if pts:
        rows_p = []
        for p in pts:
            rs = [r for r in runs if (r.get("tag") or "").startswith(f"pts{p}_")]
            rows_p.append(["Gaussians", f"{p:,}", ms([r["agg"]["psnr_static_mean"] for r in rs], 2),
                           ms([r["agg"]["ghost_residual_mean"] for r in rs], 4), str(len(rs))])
        groups.append(rows_p)
    its = sorted({r.get("iters") for r in runs if (r.get("tag") or "").startswith("iter")})
    if its:
        rows_i = []
        for it in its:
            rs = [r for r in runs if (r.get("tag") or "").startswith(f"iter{it}_")]
            rows_i.append(["Iterations", f"{it:,}", ms([r["agg"]["psnr_static_mean"] for r in rs], 2),
                           ms([r["agg"]["ghost_residual_mean"] for r in rs], 4), str(len(rs))])
        groups.append(rows_i)
    nzs = sorted({r.get("mask_noise") for r in runs if (r.get("tag") or "").startswith("noise")})
    if nzs:
        rows_n = [["Mask noise", "0% (oracle)"] + clean_row[2:]]
        for nz in nzs:
            rs = [r for r in runs if (r.get("tag") or "").startswith(f"noise{int(round(nz * 100))}_")]
            rows_n.append(["Mask noise", f"{nz * 100:.0f}%",
                           ms([r["agg"]["psnr_static_mean"] for r in rs], 2),
                           ms([r["agg"]["ghost_residual_mean"] for r in rs], 4), str(len(rs))])
        groups.append(rows_n)
    morph = [clean_row]
    for tag, name in (("soft_s", "soft weight"), ("dilate2_s", "dilated +2 px"), ("dilate-2_s", "eroded -2 px")):
        rs = [r for r in runs if (r.get("tag") or "").startswith(tag)]
        if rs:
            morph.append(["Morphology", name,
                          ms([r["agg"]["psnr_static_mean"] for r in rs], 2),
                          ms([r["agg"]["ghost_residual_mean"] for r in rs], 4), str(len(rs))])
    if len(morph) > 1:
        groups.append(morph)
    flat = [row for g in groups for row in g]
    out["tab:ablation"] = {
        "caption": "Ablation matrix for the masked configuration. Mean ± sample SD over independent seeds; each row holds the remaining factors fixed.",
        "header": ["Factor", "Setting", "Static PSNR", "Ghost L1", "Runs"],
        "colspec": "llccc",
        "rows": flat or [clean_row],
    }

    # ---- per-seed table ----
    rows = []
    for m in MODES:
        for r in sorted(by_mode[m], key=lambda x: (x.get("seed") if x.get("seed") is not None else -1)):
            seed = r.get("seed")
            rows.append([MODE_LABEL[m], str(seed) if seed is not None else "-",
                         f"{r['agg']['psnr_static_mean']:.3f}",
                         f"{r['agg']['ghost_residual_mean']:.4f}",
                         f"{r['agg']['ssim_mean']:.4f}",
                         f"{r['train_wall_s']:.1f}",
                         f"{r['render_ms']:.2f}"])
    out["tab:seedfull"] = {
        "caption": "Per-seed held-out mapping results and resource measurements.",
        "header": ["Mode", "Seed", "Static PSNR", "Ghost L1", "SSIM", "Train s", "Render ms"],
        "colspec": "llccccc",
        "rows": rows,
    }

    # ---- per-view table ----
    views = sorted({f["frame"] for m in MODES for r in by_mode[m] for f in r.get("per_frame", [])})
    rows = []
    for v in views:
        for m in MODES:
            ps, gh = [], []
            for r in by_mode[m]:
                for f in r.get("per_frame", []):
                    if f["frame"] == v:
                        ps.append(f["psnr_static"])
                        gh.append(f["ghost_residual"])
            if ps:
                rows.append([str(v), MODE_LABEL[m], ms(ps, 2), ms(gh, 4)])
    out["tab:viewfull"] = {
        "caption": "Per-view held-out results. Mean ± sample SD over seeds; these values underlie the per-view figure.",
        "header": ["View", "Configuration", "Static PSNR", "Ghost L1"],
        "colspec": "llcc",
        "rows": rows,
    }
    return out, n_seed


def _tex(cell):
    """Make a plain-text cell safe for pdflatex (no UTF-8 math symbols)."""
    s = str(cell)
    s = s.replace("±", r"$\pm$")
    s = s.replace("–", "--").replace("—", "---")
    s = s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
    s = s.replace("#", r"\#")
    return s


def latex_env(spec, label, wide=False):
    env = "table*" if wide else "table"
    lines = [f"\\begin{{{env}}}[t]",
             f"\\caption{{{spec['caption']}}}",
             f"\\label{{{label}}}",
             "\\centering\\scriptsize",
             f"\\begin{{tabular}}{{{spec['colspec']}}}",
             "\\toprule",
             " & ".join(_tex(h) for h in spec["header"]) + " \\\\",
             "\\midrule"]
    prev = None
    for row in spec["rows"]:
        if prev is not None and row[0] != prev and len(spec["header"]) >= 5:
            lines.append("\\midrule")
        lines.append(" & ".join(_tex(c) for c in row) + " \\\\")
        prev = row[0]
    lines += ["\\bottomrule", "\\end{tabular}", f"\\end{{{env}}}"]
    return "\n".join(lines)


def main():
    specs, n_seed = build()
    (HERE / "tables_data.json").write_text(
        json.dumps(specs, ensure_ascii=False, indent=1), encoding="utf-8")
    tdir = HERE / "latex" / "tables"
    tdir.mkdir(exist_ok=True)
    for label, spec in specs.items():
        name = label.split(":")[1]
        (tdir / f"{name}.tex").write_text(latex_env(spec, label, wide=len(spec["header"]) >= 6),
                                          encoding="utf-8")
    print(f"tables_data.json + {len(specs)} latex tables written | main seeds = {n_seed}")
    for label, spec in specs.items():
        print(f"  {label:14s} rows={len(spec['rows'])} cols={len(spec['header'])}")


if __name__ == "__main__":
    main()
