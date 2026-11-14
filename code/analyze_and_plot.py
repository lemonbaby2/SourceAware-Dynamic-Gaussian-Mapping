from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
FIG = OUT / "figures"
HELD = ROOT / "experiments" / "heldout_results"
FUSION = ROOT / "experiments" / "fusion_results" / "results.json"
MODES = ["naive", "no-dyn-data", "dyn-mask"]
LABELS = {
    "naive": "All pixels",
    "no-dyn-data": "Static init.",
    "dyn-mask": "Static init. + masked loss",
}
COLORS = {"naive": "#6B7280", "no-dyn-data": "#D97706", "dyn-mask": "#1D4ED8"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def mean_sd(values):
    a = np.asarray(values, dtype=float)
    return {"mean": float(a.mean()), "sd": float(a.std(ddof=1)) if len(a) > 1 else 0.0}


def style():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "figure.dpi": 160,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
        }
    )


def load_mapping():
    records = []
    for seed in [0, 1, 2]:
        for mode in MODES:
            m = read_json(HELD / f"seed{seed}_{mode}" / "metrics.json")
            records.append(m)
    return records


def mapping_summary(records):
    metrics = [
        "psnr_all_mean",
        "psnr_static_mean",
        "ghost_residual_mean",
        "ssim_mean",
        "clean_background_psnr_mean",
        "train_wall_s",
        "render_ms",
        "peak_allocated_bytes",
    ]
    result = {}
    for mode in MODES:
        rows = [r for r in records if r["mode"] == mode]
        result[mode] = {}
        for metric in metrics:
            vals = [r.get("agg", {}).get(metric, r.get(metric)) for r in rows]
            result[mode][metric] = mean_sd(vals)
        result[mode]["seeds"] = [
            {
                "seed": r["seed"],
                "psnr_static": r["agg"]["psnr_static_mean"],
                "ghost_residual": r["agg"]["ghost_residual_mean"],
                "ssim": r["agg"]["ssim_mean"],
                "train_wall_s": r["train_wall_s"],
                "render_ms": r["render_ms"],
            }
            for r in rows
        ]
    base = {r["seed"]: r for r in records if r["mode"] == "naive"}
    full = {r["seed"]: r for r in records if r["mode"] == "dyn-mask"}
    deltas = {
        "static_psnr_db": [full[s]["agg"]["psnr_static_mean"] - base[s]["agg"]["psnr_static_mean"] for s in base],
        "ghost_l1": [full[s]["agg"]["ghost_residual_mean"] - base[s]["agg"]["ghost_residual_mean"] for s in base],
        "ghost_ratio": [base[s]["agg"]["ghost_residual_mean"] / full[s]["agg"]["ghost_residual_mean"] for s in base],
    }
    result["paired_full_vs_all"] = {k: {**mean_sd(v), "values": v} for k, v in deltas.items()}
    per_view = {}
    for frame in [2, 5, 8, 11]:
        per_view[str(frame)] = {}
        for mode in MODES:
            values = []
            for r in records:
                if r["mode"] == mode:
                    values.append(next(x for x in r["per_frame"] if x["frame"] == frame))
            per_view[str(frame)][mode] = {
                key: mean_sd([v[key] for v in values])
                for key in ["psnr_static", "ghost_residual", "clean_background_psnr", "ssim"]
            }
    result["per_view"] = per_view
    return result


def plot_mapping(summary):
    fig, axes = plt.subplots(1, 3, figsize=(7.15, 2.25))
    specs = [
        ("psnr_static_mean", "Static-region PSNR (dB)"),
        ("ghost_residual_mean", "Dynamic ghost residual (L1)"),
        ("ssim_mean", "Held-out SSIM"),
    ]
    for ax, (metric, ylabel) in zip(axes, specs):
        means = [summary[m][metric]["mean"] for m in MODES]
        sds = [summary[m][metric]["sd"] for m in MODES]
        ax.bar(range(3), means, yerr=sds, capsize=3, color=[COLORS[m] for m in MODES], width=0.7)
        ax.set_xticks(range(3), ["All", "Init", "Init+mask"])
        ax.set_ylabel(ylabel)
    fig.tight_layout(w_pad=1.1)
    fig.savefig(FIG / "mapping_summary.png")
    plt.close(fig)


def plot_per_view(summary):
    frames = [2, 5, 8, 11]
    x = np.arange(len(frames))
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.35))
    for mode in MODES:
        p = summary["per_view"]
        means = [p[str(f)][mode]["psnr_static"]["mean"] for f in frames]
        sds = [p[str(f)][mode]["psnr_static"]["sd"] for f in frames]
        axes[0].errorbar(x, means, yerr=sds, marker="o", capsize=2, label=LABELS[mode], color=COLORS[mode])
        means = [p[str(f)][mode]["ghost_residual"]["mean"] for f in frames]
        sds = [p[str(f)][mode]["ghost_residual"]["sd"] for f in frames]
        axes[1].errorbar(x, means, yerr=sds, marker="o", capsize=2, label=LABELS[mode], color=COLORS[mode])
    for ax in axes:
        ax.set_xticks(x, [str(f) for f in frames])
        ax.set_xlabel("Held-out view index")
    axes[0].set_ylabel("Static-region PSNR (dB)")
    axes[1].set_ylabel("Dynamic ghost residual (L1)")
    axes[1].legend(frameon=False, fontsize=7, loc="upper left")
    fig.tight_layout(w_pad=1.2)
    fig.savefig(FIG / "per_view_results.png")
    plt.close(fig)


def plot_resources(summary):
    fig, axes = plt.subplots(1, 3, figsize=(7.15, 2.15))
    specs = [
        ("train_wall_s", "Training time (s)"),
        ("render_ms", "Render time (ms/frame)"),
        ("peak_allocated_bytes", "Peak allocated GPU memory (GiB)"),
    ]
    for ax, (metric, ylabel) in zip(axes, specs):
        scale = 1024**3 if metric == "peak_allocated_bytes" else 1
        means = [summary[m][metric]["mean"] / scale for m in MODES]
        sds = [summary[m][metric]["sd"] / scale for m in MODES]
        ax.bar(range(3), means, yerr=sds, capsize=3, color=[COLORS[m] for m in MODES], width=0.7)
        ax.set_xticks(range(3), ["All", "Init", "Init+mask"])
        ax.set_ylabel(ylabel)
    fig.tight_layout(w_pad=1.0)
    fig.savefig(FIG / "resource_profile.png")
    plt.close(fig)


def fusion_summary():
    data = read_json(FUSION)
    return data["protocol"], data["rows"], data["summary"]


def plot_fusion(summary):
    methods = ["fixed_product", "channel_mean", "family_pool"]
    labels = {"fixed_product": "Channel product", "channel_mean": "Channel mean", "family_pool": "Family pool"}
    colors = {"fixed_product": "#B91C1C", "channel_mean": "#D97706", "family_pool": "#1D4ED8"}
    copies = [1, 2, 4, 8]
    fig, axes = plt.subplots(2, 2, figsize=(7.15, 4.15))
    for ax, metric, ylabel in zip(axes.ravel(), ["nll", "ece10", "brier", "f1"], ["Negative log likelihood", "ECE (10 bins)", "Brier score", "F1"]):
        for method in methods:
            vals = [next(r for r in summary if r["copies"] == c and r["method"] == method) for c in copies]
            ax.errorbar(copies, [r[metric]["mean"] for r in vals], yerr=[r[metric]["std"] for r in vals], marker="o", capsize=2, color=colors[method], label=labels[method])
        ax.set_xscale("log", base=2)
        ax.set_xticks(copies, copies)
        ax.set_xlabel("Exact copies of the motion channel")
        ax.set_ylabel(ylabel)
    axes[0, 0].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fusion_stress_extended.png")
    plt.close(fig)


def make_qualitative():
    frame = 8
    panels = []
    for mode in MODES:
        img = Image.open(HELD / f"seed0_{mode}" / f"view_{frame:03d}.png").convert("RGB")
        w, h = img.size
        panels.append((mode, [img.crop((i * w // 3, 0, (i + 1) * w // 3, h)) for i in range(3)]))
    cell_w, cell_h = panels[0][1][0].size
    top, left = 48, 150
    canvas = Image.new("RGB", (left + 3 * cell_w, top + 3 * cell_h), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for j, title in enumerate(["Dynamic observation", "Gaussian render", "Static ground truth"]):
        draw.text((left + j * cell_w + 5, 16), title, fill="black", font=font)
    for i, (mode, crops) in enumerate(panels):
        draw.text((8, top + i * cell_h + cell_h // 2 - 5), LABELS[mode], fill="black", font=font)
        for j, crop in enumerate(crops):
            canvas.paste(crop, (left + j * cell_w, top + i * cell_h))
    canvas.save(FIG / "qualitative_view8.png", dpi=(300, 300))


def method_diagram():
    fig, ax = plt.subplots(figsize=(7.15, 2.4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis("off")
    boxes = [
        (0.3, 2.5, 2.1, 0.9, "Motion family\nflow + derived clusters", "#DBEAFE"),
        (0.3, 0.6, 2.1, 0.9, "Geometry family\ndepth inconsistency", "#DCFCE7"),
        (3.1, 1.55, 2.1, 0.9, "Within-family\nmean calibrated logits", "#FEF3C7"),
        (5.9, 1.55, 1.8, 0.9, "Across-family\nweighted pool", "#EDE9FE"),
        (8.4, 1.55, 1.4, 0.9, "Dynamic\nprobability", "#FCE7F3"),
        (10.4, 1.55, 1.3, 0.9, "Static-only\nmap update", "#E5E7EB"),
    ]
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    for x, y, w, h, text, color in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04", facecolor=color, edgecolor="#374151", linewidth=0.8))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8)
    arrows = [((2.4, 2.95), (3.1, 2.05)), ((2.4, 1.05), (3.1, 2.0)), ((5.2, 2.0), (5.9, 2.0)), ((7.7, 2.0), (8.4, 2.0)), ((9.8, 2.0), (10.4, 2.0))]
    for a, b in arrows:
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10, color="#374151", linewidth=0.9))
    ax.text(4.15, 0.18, "Exact copies stay within one fixed family budget", ha="center", va="center", fontsize=8, color="#7C2D12")
    fig.tight_layout()
    fig.savefig(FIG / "method_overview.png")
    plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    style()
    records = load_mapping()
    mapping = mapping_summary(records)
    protocol, rows, fusion = fusion_summary()
    plot_mapping(mapping)
    plot_per_view(mapping)
    plot_resources(mapping)
    plot_fusion(fusion)
    make_qualitative()
    method_diagram()
    payload = {
        "mapping_runs": len(records),
        "mapping": mapping,
        "fusion_protocol": protocol,
        "fusion_rows": len(rows),
        "fusion_summary": fusion,
        "figures": sorted(p.name for p in FIG.glob("*.png")),
    }
    (OUT / "analysis_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"mapping_runs": len(records), "fusion_rows": len(rows), "figures": payload["figures"]}, indent=2))


if __name__ == "__main__":
    main()
