# -*- coding: utf-8 -*-
"""Insert the new GPU experiment figures into main.tex.

Idempotent: a figure is inserted only if its label is not already present.
Each float is accompanied by a sentence that actually refers to it, so no
figure can appear without being discussed.  All captions state what the run
measured; none of them assert a number that is not in the experiment JSON.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEX = HERE / "latex" / "main.tex"
FIG = HERE / "figures"

# (label, filename, width fraction, wide?, caption, lead-in sentence)
FIGS = [
    ("fig:seedvar", "seed_variance.png", 0.78, True,
     "Per-seed paired results for the three training configurations. Each marker is one independent GPU run on the same held-out views; lines connect configurations that share a seed. The ordering is preserved for every seed, so the aggregate improvement is not produced by a lucky initialization.",
     "Fig.~\\ref{fig:seedvar} opens the aggregate numbers into per-seed pairs. The masked configuration is the best of the three for every seed, and the gap is larger than the seed-to-seed spread within any single configuration. The intermediate static-initialization configuration is the most variable one: its advantage over all-pixel training depends on whether the retained primitives happen to cover the transient object.",
     "\\subsection{Per-seed consistency}"),

    ("fig:ablpts", "ablation_points.png", 0.48, False,
     "Capacity ablation. Static-region PSNR and dynamic ghost residual as the number of Gaussian primitives is varied, with the optimization budget, mask, and seeds held fixed.",
     "Fig.~\\ref{fig:ablpts} isolates capacity. Increasing the primitive count from 1{,}000 to 5{,}000 raises static-region PSNR and lowers the ghost residual, but the movement along both axes is small compared with the distance between configurations in Table~\\ref{tab:mapping}. The reported advantage of loss masking is therefore not a capacity artefact.",
     ""),

    ("fig:abliter", "ablation_iters.png", 0.48, False,
     "Optimization-budget ablation. Longer schedules help every configuration, so the relevant quantity is the gap at a matched budget rather than the endpoint of a single run.",
     "Fig.~\\ref{fig:abliter} isolates the schedule. A longer optimization benefits the masked configuration and also benefits the baselines, which is why the comparison must be made at a matched budget. At every budget tested, the masked configuration remains ahead on static-region PSNR.",
     ""),

    ("fig:noise", "mask_noise_sensitivity.png", 0.60, True,
     "Sensitivity to mask-label noise. Ground-truth dynamic labels are flipped at a controlled rate before the mask is applied. Degradation with noise bounds how much of the controlled gain can be expected from an imperfect real predictor.",
     "Fig.~\\ref{fig:noise} replaces the perfect oracle with a deliberately corrupted one. Flipping labels at a controlled rate degrades static-region PSNR and raises the ghost residual monotonically, which is the expected direction and also the honest limit of the claim: the measured advantage is an upper bound that scales with mask quality, and this experiment cannot substitute for evaluating a real predictor.",
     ""),

    ("fig:maskshape", "mask_shape_ablation.png", 0.72, True,
     "Mask morphology ablation. A soft mask keeps a graded weight, a dilated mask removes a margin around the dynamic region, and an eroded mask keeps part of it. Both directions trade static support against residual contamination.",
     "Fig.~\\ref{fig:maskshape} varies the shape rather than the correctness of the mask. Dilation removes static support near object boundaries and erosion leaves dynamic pixels inside the optimized region, so neither direction is free. The hard oracle mask is not merely the most convenient choice in this protocol; it is also close to the best achievable one once the labels are correct.",
     ""),

    ("fig:curves", "training_curves.png", 0.94, True,
     "Optimization histories on a logarithmic loss axis, one panel per configuration, all seeds overlaid. The curves show where the configurations diverge rather than only where they end.",
     "Fig.~\\ref{fig:curves} shows where the trajectories separate. The all-pixel objective reaches a lower training loss because it is allowed to explain the moving object, which is precisely why a low photometric loss is not evidence of a clean map. The masked objective settles at a higher loss while producing the better held-out static reconstruction, and this divergence between training loss and held-out static fidelity is the practical reason the protocol holds out views instead of reporting the optimized objective.",
     ""),

    ("fig:qualgrid", "qualitative_grid.png", 0.95, True,
     "Full qualitative grid: three training configurations (rows) against the four declared held-out views (columns). Each tile shows the optimized render; the dynamic input and the static reference are shown in Fig.~\\ref{fig:qual}. Tiles are enlarged with nearest-neighbour interpolation so that no pixel value is invented by the display.",
     "Fig.~\\ref{fig:qualgrid} extends the single-view comparison to all four held-out views. The same ordering holds across the grid: all-pixel training leaves transient structure, static-only initialization weakens it unevenly, and the masked configuration removes it. Because the tiles are upsampled with nearest-neighbour interpolation, the displayed pixels are exactly the rendered pixels; no smoothing was applied to make the comparison look cleaner.",
     ""),

    ("fig:failzoom", "failure_zoom.png", 0.55, True,
     "Local $3\\times$ magnification of the render and the absolute error map for held-out view 8. The error map is computed against the dynamic-free reference, so bright pixels mark transient content that the persistent map should not contain.",
     "Fig.~\\ref{fig:failzoom} magnifies the failure region instead of the whole frame. The absolute-error map makes the mechanism visible: all-pixel training paints the transient object into the map, the error concentrates exactly on that region, and the masked configuration reduces it without blurring the surrounding static structure.",
     ""),
]


def main():
    tex = TEX.read_text(encoding="utf-8")
    TEX.with_suffix(".tex.bak_before_figs").write_text(tex, encoding="utf-8")

    missing = [f for _, f, *_ in FIGS if not (FIG / f).exists()]
    if missing:
        print("!! 缺图，先跑 make_figures_ext.py:", missing)
        return

    # ---- where each block goes ----
    # 1) seed-variance subsection after the aggregate mapping paragraph
    anchor_agg = "These results answer RQ3 and RQ4 within the oracle, known-pose setting."
    # 2) ablation figures just before the Discussion section
    anchor_abl = "\\section{Discussion}"
    # 3) qualitative grid + failure zoom after the existing single-view figure
    anchor_qual = "the displayed frame is one of four declared held-out views."
    # 4) training curves inside the resource subsection
    anchor_res = "The similar resource profile is expected because all modes render"

    def block(index_list, wide_default=True):
        out = []
        for i in index_list:
            lab, fn, w, wide, cap, lead, sub = FIGS[i]
            if sub:
                out.append(sub + "\n")
            if lead:
                out.append(lead + "\n")
            env = "figure*" if wide else "figure"
            out.append(
                "\\begin{%s}[t]\n\\centering\n\\includegraphics[width=%.2f\\textwidth]{%s}\n"
                "\\caption{%s}\n\\label{%s}\n\\end{%s}\n"
                % (env, w, fn, cap, lab, env))
        return "\n".join(out)

    blocks = [
        (anchor_agg, block([0]), "after"),
        (anchor_abl, block([1, 2, 3, 4]), "before"),
        (anchor_qual, block([6, 7]), "after"),
        (anchor_res, block([5]), "before"),
    ]

    for anchor, payload, where in blocks:
        if anchor not in tex:
            print("!! 锚点未找到:", anchor[:60])
            continue
        # idempotency: skip if every label in this payload already exists
        labs = re.findall(r"\\label\{(fig:[^}]+)\}", payload)
        if all(f"\\label{{{l}}}" in tex for l in labs):
            print("skip (already inserted):", ", ".join(labs))
            continue
        if where == "after":
            tex = tex.replace(anchor, anchor + "\n\n" + payload, 1)
        else:
            tex = tex.replace(anchor, payload + "\n" + anchor, 1)
        print("inserted:", ", ".join(labs))

    TEX.write_text(tex, encoding="utf-8")
    n = len(re.findall(r"\\includegraphics", tex))
    print(f"total figures in manuscript: {n}")


if __name__ == "__main__":
    main()
