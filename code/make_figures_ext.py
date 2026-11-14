# -*- coding: utf-8 -*-
"""Generate publication figures from extended2 experiment outputs.

All numbers come from real GPU runs saved as metrics.json/history.json;
qualitative panels are tiled from the per-view renderings that the training
script itself wrote (input | render | clean | |error|).
"""
import json, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.font_manager as fm
from PIL import Image

HERE = Path(__file__).resolve().parent
EXT = HERE.parent / "experiments" / "extended2"
OLD = HERE.parent / "experiments" / "heldout_results"
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)

# ---- unified style (light theme, print-safe) ----
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.linewidth": 0.6,
    "grid.linewidth": 0.4,
    "grid.color": "#d9d9d9",
    "axes.edgecolor": "#4d4d4d",
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "figure.facecolor": "white",
})
C_NAIVE, C_INIT, C_MASK = "#c55a11", "#7f7f7f", "#1f4e79"
C_ACC = ["#1f4e79", "#c55a11", "#548235", "#7030a0", "#bf9000"]
LBL = {"naive": "All pixels", "no-dyn-data": "Static-only init.", "dyn-mask": "Init. + masked loss"}
MODES = ["naive", "no-dyn-data", "dyn-mask"]


def load_runs():
    runs = []
    for d in list(EXT.glob("*/metrics.json")) + list(OLD.glob("*/metrics.json")):
        try:
            j = json.loads(d.read_text(encoding="utf-8"))
        except Exception:
            continue
        j["_dir"] = d.parent
        j["_src"] = "ext" if d.parent.parent == EXT else "old"
        runs.append(j)
    return runs


def by_tag(runs):
    out = {}
    for r in runs:
        tag = r.get("tag") or f"{r.get('seed')}_{r.get('mode')}"
        out[tag] = r
    return out


def k(r, key):
    return r["agg"][key]


def main_summary(runs):
    """Aggregate 5-seed main experiment: naive / no-dyn-data / dyn-mask @1200it/2500pt."""
    main = []
    for r in runs:
        tag = r.get("tag") or f"{r.get('seed')}_{r.get('mode')}"
        mode = r.get("mode")
        # main experiment = default iters/points and no mask perturbation
        is_main = (r.get("iters", 1200) == 1200 and r.get("points", 2500) == 2500
                   and r.get("mask_noise", 0) == 0 and r.get("mask_dilate", 0) == 0
                   and r.get("mask_mode", "hard") == "hard")
        if mode in MODES and is_main and not tag.startswith(("pts", "iter", "noise", "soft", "dilate")):
            main.append(r)
    stat = {}
    for m in MODES:
        rs = [r for r in main if r.get("mode") == m]
        if not rs:
            continue
        stat[m] = {
            "psnr": [k(r, "psnr_static_mean") for r in rs],
            "ghost": [k(r, "ghost_residual_mean") for r in rs],
            "ssim": [k(r, "ssim_mean") for r in rs],
            "train_s": [r["train_wall_s"] for r in rs],
            "render_ms": [r["render_ms"] for r in rs],
            "peak_mb": [r["peak_allocated_bytes"] / 2**20 for r in rs],
            "seeds": [r.get("seed") for r in rs],
        }
    return stat, main


def save(fig, name):
    p = FIG / name
    fig.savefig(p)
    plt.close(fig)
    print("WROTE", p, flush=True)
    return p


def fig_main(stat):
    if not stat:
        return
    modes = [m for m in MODES if m in stat]
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.25))
    specs = [("psnr", "Static-region PSNR (dB)", "higher is better", "{:.2f}"),
             ("ghost", "Dynamic ghost residual (L1)", "lower is better", "{:.4f}"),
             ("ssim", "SSIM", "higher is better", "{:.4f}")]
    for ax, (key, ylab, note, fmt) in zip(axes, specs):
        vals = [float(np.mean(stat[m][key])) for m in modes]
        errs = [float(np.std(stat[m][key], ddof=1)) if len(stat[m][key]) > 1 else 0.0 for m in modes]
        cols = [C_NAIVE, C_INIT, C_MASK][:len(modes)]
        b = ax.bar(range(len(modes)), vals, yerr=errs, capsize=2.5, color=cols,
                   edgecolor="#333333", linewidth=0.5, width=0.62)
        for i, (v, e) in enumerate(zip(vals, errs)):
            ax.text(i, v + (e if e else 0) + (max(vals) - min(vals) + 1e-9) * 0.04,
                    fmt.format(v), ha="center", va="bottom", fontsize=6.5)
        ax.set_xticks(range(len(modes)))
        ax.set_xticklabels([LBL[m] for m in modes], rotation=12, ha="right")
        ax.set_ylabel(ylab)
        ax.set_title(note, loc="right", fontsize=6.5, color="#666666")
        ax.grid(axis="y", alpha=0.6)
        ax.set_axisbelow(True)
        lo = min(vals) - max(errs) * 1.5
        hi = max(vals) + max(errs) * 1.5
        pad = (hi - lo) * 0.18 if hi > lo else 0.1
        ax.set_ylim(lo - pad, hi + pad * 1.4)
    fig.suptitle("Held-out mapping over independent seeds (GPU, oracle pose/depth)",
                 fontsize=8.5, y=1.02)
    fig.tight_layout()
    save(fig, "mapping_summary.png")
    json.dump({m: {kk: {"mean": float(np.mean(vv)), "std": float(np.std(vv, ddof=1)) if len(vv) > 1 else 0.0,
                       "n": len(vv)} for kk, vv in d.items() if kk != "seeds"}
               for m, d in stat.items()},
              open(HERE / "main_stats.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def fig_seed_variance(stat):
    if not stat:
        return
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.2))
    for ax, (key, ylab) in zip(axes, [("psnr", "Static-region PSNR (dB)"), ("ghost", "Ghost residual (L1)")]):
        data = [stat[m][key] for m in MODES if m in stat]
        labels = [m for m in MODES if m in stat]
        bp = ax.boxplot(data, widths=0.5, patch_artist=True, showmeans=True,
                        medianprops=dict(color="#333333", linewidth=1.0),
                        meanprops=dict(marker="D", markerfacecolor="white", markeredgecolor="#333333", markersize=3.2))
        for patch, c in zip(bp["boxes"], [C_NAIVE, C_INIT, C_MASK]):
            patch.set_facecolor(c)
            patch.set_alpha(0.55)
            patch.set_edgecolor("#333333")
            patch.set_linewidth(0.6)
        for i, d in enumerate(data, 1):
            ax.scatter(np.full(len(d), i) + np.linspace(-0.08, 0.08, len(d)), d,
                       s=9, color="#222222", zorder=3, linewidths=0)
        ax.set_xticklabels([LBL[m] for m in labels], rotation=12, ha="right")
        ax.set_ylabel(ylab)
        ax.grid(axis="y", alpha=0.6)
        ax.set_axisbelow(True)
    axes[0].set_title("Per-seed spread (dots = individual seeds)", loc="left", fontsize=7)
    fig.tight_layout()
    save(fig, "seed_variance.png")


def fig_ablation(runs, prefix, xkey, xlabel, title, fname, logx=False):
    rs = [r for r in runs if (r.get("tag") or "").startswith(prefix)]
    if not rs:
        return
    groups = {}
    for r in rs:
        x = r.get(xkey)
        groups.setdefault(x, []).append(r)
    xs = sorted(groups.keys())
    psnr = [float(np.mean([k(r, "psnr_static_mean") for r in groups[x]])) for x in xs]
    psnr_e = [float(np.std([k(r, "psnr_static_mean") for r in groups[x]], ddof=1)) if len(groups[x]) > 1 else 0 for x in xs]
    ghost = [float(np.mean([k(r, "ghost_residual_mean") for r in groups[x]])) for x in xs]
    ghost_e = [float(np.std([k(r, "ghost_residual_mean") for r in groups[x]], ddof=1)) if len(groups[x]) > 1 else 0 for x in xs]
    fig, ax1 = plt.subplots(figsize=(3.4, 2.3))
    ax2 = ax1.twinx()
    ax1.errorbar(range(len(xs)), psnr, yerr=psnr_e, marker="o", ms=3.2, lw=1.1,
                 color=C_MASK, capsize=2, label="static PSNR")
    ax2.errorbar(range(len(xs)), ghost, yerr=ghost_e, marker="s", ms=3.0, lw=1.1,
                 color=C_NAIVE, capsize=2, label="ghost residual")
    ax1.set_xticks(range(len(xs)))
    ax1.set_xticklabels([str(x) for x in xs])
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel("Static PSNR (dB)", color=C_MASK)
    ax2.set_ylabel("Ghost residual (L1)", color=C_NAIVE)
    ax1.tick_params(axis="y", colors=C_MASK)
    ax2.tick_params(axis="y", colors=C_NAIVE)
    ax1.grid(alpha=0.55)
    ax1.set_axisbelow(True)
    ax1.set_title(title, fontsize=7.5)
    fig.tight_layout()
    save(fig, fname)


def fig_noise(runs):
    rs = [r for r in runs if (r.get("tag") or "").startswith("noise")]
    base = [r for r in runs if (r.get("tag") or "").startswith("main_") and r.get("mode") == "dyn-mask"]
    if not rs:
        return
    xs = [0.0] + sorted({r.get("mask_noise") for r in rs})
    def collect(nz):
        if nz == 0.0:
            sel = base
        else:
            sel = [r for r in rs if r.get("mask_noise") == nz]
        return ([k(r, "psnr_static_mean") for r in sel], [k(r, "ghost_residual_mean") for r in sel])
    ps, ps_e, gh, gh_e = [], [], [], []
    for nz in xs:
        p, g = collect(nz)
        ps.append(float(np.mean(p)) if p else np.nan)
        ps_e.append(float(np.std(p, ddof=1)) if len(p) > 1 else 0.0)
        gh.append(float(np.mean(g)) if g else np.nan)
        gh_e.append(float(np.std(g, ddof=1)) if len(g) > 1 else 0.0)
    fig, ax1 = plt.subplots(figsize=(3.4, 2.3))
    ax2 = ax1.twinx()
    ax1.errorbar([x * 100 for x in xs], ps, yerr=ps_e, marker="o", ms=3.2, lw=1.1,
                 color=C_MASK, capsize=2)
    ax2.errorbar([x * 100 for x in xs], gh, yerr=gh_e, marker="s", ms=3.0, lw=1.1,
                 color=C_NAIVE, capsize=2)
    ax1.set_xlabel("Mask label noise rate (%)")
    ax1.set_ylabel("Static PSNR (dB)", color=C_MASK)
    ax2.set_ylabel("Ghost residual (L1)", color=C_NAIVE)
    ax1.tick_params(axis="y", colors=C_MASK)
    ax2.tick_params(axis="y", colors=C_NAIVE)
    ax1.grid(alpha=0.55)
    ax1.set_axisbelow(True)
    ax1.set_title("Sensitivity to mask-prediction error", fontsize=7.5)
    fig.tight_layout()
    save(fig, "mask_noise_sensitivity.png")


def fig_mask_shape(runs):
    """soft vs hard, dilate +2 / -2 vs base."""
    def agg(tag_pred):
        sel = [r for r in runs if tag_pred(r.get("tag") or "", r)]
        if not sel:
            return None
        p = [k(r, "psnr_static_mean") for r in sel]
        g = [k(r, "ghost_residual_mean") for r in sel]
        return (float(np.mean(p)), float(np.std(p, ddof=1)) if len(p) > 1 else 0.0,
                float(np.mean(g)), float(np.std(g, ddof=1)) if len(g) > 1 else 0.0)
    base = agg(lambda t, r: t.startswith("main_") and r.get("mode") == "dyn-mask")
    soft = agg(lambda t, r: t.startswith("soft"))
    dil = agg(lambda t, r: t.startswith("dilate2"))
    ero = agg(lambda t, r: t.startswith("dilate-2"))
    items = [("Hard (base)", base), ("Soft", soft), ("Dilated +2", dil), ("Eroded -2", ero)]
    items = [(n, v) for n, v in items if v]
    if len(items) < 2:
        return
    fig, axes = plt.subplots(1, 2, figsize=(5.2, 2.15))
    names = [n for n, _ in items]
    for ax, (idx, ylab, note) in zip(axes, [(0, "Static PSNR (dB)", "higher is better"),
                                            (2, "Ghost residual (L1)", "lower is better")]):
        vals = [v[idx] for _, v in items]
        errs = [v[idx + 1] for _, v in items]
        ax.bar(range(len(items)), vals, yerr=errs, capsize=2.2, width=0.6,
               color=[C_MASK if i == 0 else C_ACC[i % len(C_ACC)] for i in range(len(items))],
               edgecolor="#333333", linewidth=0.5, alpha=0.9)
        ax.set_xticks(range(len(items)))
        ax.set_xticklabels(names, rotation=14, ha="right")
        ax.set_ylabel(ylab)
        ax.set_title(note, loc="right", fontsize=6.5, color="#666666")
        ax.grid(axis="y", alpha=0.55)
        ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "mask_shape_ablation.png")


def fig_curves():
    """Training curves for three configurations, seed 0."""
    series = []
    for src, tag in [("old", "seed0_naive"), ("old", "seed0_no-dyn-data"), ("old", "seed0_dyn-mask"),
                     ("ext", "main_s3_naive"), ("ext", "main_s4_dyn-mask")]:
        base = OLD if src == "old" else EXT
        p = base / tag / "history.json"
        if p.exists():
            series.append((tag, json.loads(p.read_text(encoding="utf-8"))))
    if not series:
        return
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.2))
    colors = {"naive": C_NAIVE, "no-dyn-data": C_INIT, "dyn-mask": C_MASK}
    for tag, h in series:
        it = [x["iter"] for x in h]
        ls = "-" if "seed0" in tag else "--"
        m = "dyn-mask" if "dyn-mask" in tag else ("naive" if "naive" in tag else "no-dyn-data")
        axes[0].plot(it, [x["loss"] for x in h], ls, color=colors[m], lw=1.1,
                     label=(LBL[m] if "seed0" in tag else None))
        axes[1].plot(it, [x["psnr"] for x in h], ls, color=colors[m], lw=1.1,
                     label=(LBL[m] if "seed0" in tag else None))
    axes[0].set_xlabel("Iteration")
    axes[0].set_ylabel("Training L1 loss")
    axes[0].set_yscale("log")
    axes[1].set_xlabel("Iteration")
    axes[1].set_ylabel("Training-view PSNR (dB)")
    for ax in axes:
        ax.grid(alpha=0.55)
        ax.set_axisbelow(True)
    axes[0].legend(frameon=False, fontsize=6.3)
    axes[0].set_title("Solid: seed 0　Dashed: additional seeds", fontsize=6.5, loc="right", color="#666666")
    fig.tight_layout()
    save(fig, "training_curves.png")


def fig_resource(stat):
    if not stat:
        return
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.05))
    specs = [("train_s", "Optimization time (s)"), ("render_ms", "Render time per view (ms)"),
             ("peak_mb", "Peak allocated GPU memory (MiB)")]
    for ax, (key, ylab) in zip(axes, specs):
        vals = [float(np.mean(stat[m][key])) for m in MODES if m in stat]
        errs = [float(np.std(stat[m][key], ddof=1)) if len(stat[m][key]) > 1 else 0.0 for m in MODES if m in stat]
        ax.bar(range(len(vals)), vals, yerr=errs, capsize=2.2, width=0.6,
               color=[C_NAIVE, C_INIT, C_MASK][:len(vals)], edgecolor="#333333", linewidth=0.5)
        ax.set_xticks(range(len(vals)))
        ax.set_xticklabels([LBL[m] for m in MODES if m in stat], rotation=14, ha="right")
        ax.set_ylabel(ylab)
        ax.grid(axis="y", alpha=0.55)
        ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "resource_profile.png")


def fig_qual_grid(runs):
    """3 configs x 4 held-out views tiled from per-view renders (input|render|clean|error)."""
    picks = {}
    for r in runs:
        tag = r.get("tag") or f"{r.get('seed')}_{r.get('mode')}"
        if tag in ("main_s3_naive", "main_s3_no-dyn-data", "main_s3_dyn-mask"):
            picks[r["mode"]] = r["_dir"]
        if len(picks) == 3:
            break
    if len(picks) < 3:
        for r in runs:
            tag = r.get("tag") or f"{r.get('seed')}_{r.get('mode')}"
            if tag in ("seed0_naive", "seed0_no-dyn-data", "seed0_dyn-mask"):
                picks[r["mode"]] = r["_dir"]
    if len(picks) < 3:
        return
    views = [2, 5, 8, 11]
    try:
        imgs = {m: [Image.open(picks[m] / f"view_{v:03d}.png") for v in views] for m in MODES}
    except Exception as e:
        print("skip qual grid:", e)
        return
    w, h = imgs[MODES[0]][0].size
    tile_w = w // 4          # panel: input | render | clean | |error|
    scale = 3                # nearest-neighbour upscale keeps render pixels honest

    def render_tile(im):
        return im.crop((tile_w, 0, 2 * tile_w, h))

    fig, axes = plt.subplots(3, 4, figsize=(7.0, 3.02))
    for i, m in enumerate(MODES):
        for j in range(4):
            ax = axes[i, j]
            tile = render_tile(imgs[m][j])
            ax.imshow(tile.resize((tile.size[0] * scale, tile.size[1] * scale), Image.NEAREST))
            ax.set_xticks([]), ax.set_yticks([])
            for s in ax.spines.values():
                s.set_linewidth(0.5)
                s.set_color("#999999")
            if i == 0:
                ax.set_title(f"held-out view {views[j]}", fontsize=7)
            if j == 0:
                ax.set_ylabel(LBL[m], fontsize=7)
                ax.yaxis.set_label_coords(-0.16, 0.5)
    fig.tight_layout()
    save(fig, "qualitative_grid.png")


def fig_failure(runs):
    """Zoomed ghost patches for naive vs masked, view 8."""
    picks = {}
    for r in runs:
        tag = r.get("tag") or f"{r.get('seed')}_{r.get('mode')}"
        if tag in ("main_s3_naive", "main_s3_dyn-mask"):
            picks[r["mode"]] = r["_dir"]
    if len(picks) < 2:
        return
    try:
        a = Image.open(picks["naive"] / "view_008.png")
        b = Image.open(picks["dyn-mask"] / "view_008.png")
    except Exception:
        return
    # each panel 4 tiles wide; render tile is the 2nd; error tile is the 4th
    tw = a.size[0] // 4
    def tile(im, idx):
        return im.crop((idx * tw, 0, (idx + 1) * tw, im.size[1]))
    r_naive, e_naive = tile(a, 1), tile(a, 3)
    r_mask, e_mask = tile(b, 1), tile(b, 3)
    fig, axes = plt.subplots(2, 2, figsize=(4.4, 3.0))
    for ax, im, t in [(axes[0, 0], r_naive, "All pixels: render"), (axes[0, 1], r_mask, "Masked: render"),
                      (axes[1, 0], e_naive, "All pixels: |error|"), (axes[1, 1], e_mask, "Masked: |error|")]:
        ax.imshow(im.resize((im.size[0] * 3, im.size[1] * 3), Image.NEAREST))
        ax.set_title(t, fontsize=6.8)
        ax.set_xticks([]), ax.set_yticks([])
        for s in ax.spines.values():
            s.set_linewidth(0.5)
            s.set_color("#999999")
    fig.tight_layout()
    save(fig, "failure_zoom.png")


def main():
    runs = load_runs()
    print(f"loaded {len(runs)} runs", flush=True)
    stat, main_runs = main_summary(runs)
    print("main runs:", {m: len(v["psnr"]) for m, v in stat.items()}, flush=True)
    fig_main(stat)
    fig_seed_variance(stat)
    fig_ablation(runs, "pts", "points", "Number of Gaussians", "Capacity ablation", "ablation_points.png")
    fig_ablation(runs, "iter", "iters", "Training iterations", "Optimization budget ablation", "ablation_iters.png")
    fig_noise(runs)
    fig_mask_shape(runs)
    fig_curves()
    fig_resource(stat)
    fig_qual_grid(runs)
    fig_failure(runs)
    print("FIGURES DONE", flush=True)


if __name__ == "__main__":
    main()
