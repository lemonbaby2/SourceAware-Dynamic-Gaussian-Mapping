"""Re-export the paper overview as a vector-derived high-resolution figure.

No pixels are generated or retouched: all wording, arrows and layout are
drawn directly from the paper's editable source diagram.
"""
from pathlib import Path
import os
os.environ["MPLBACKEND"] = "Agg"
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent.parent / "revision_20261114" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
fig, ax = plt.subplots(figsize=(14.3, 4.7), constrained_layout=True)
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
for x, y, w, h, label, color in boxes:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04",
                 facecolor=color, edgecolor="#374151", linewidth=1.35))
    ax.text(x + w/2, y + h/2, label, ha="center", va="center", fontsize=11)
for start, end in [((2.4, 2.95), (3.1, 2.05)), ((2.4, 1.05), (3.1, 2.0)),
                   ((5.2, 2.0), (5.9, 2.0)), ((7.7, 2.0), (8.4, 2.0)),
                   ((9.8, 2.0), (10.4, 2.0))]:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=16,
                 color="#374151", linewidth=1.4))
ax.text(4.15, 0.18, "Exact copies stay within one fixed family budget",
        ha="center", va="center", fontsize=10.5, color="#7C2D12")
fig.savefig(OUT / "method_overview.png", dpi=600, bbox_inches="tight", pad_inches=0.02)
fig.savefig(OUT / "method_overview.pdf", bbox_inches="tight", pad_inches=0.02)
fig.savefig(OUT / "method_overview.svg", bbox_inches="tight", pad_inches=0.02)
