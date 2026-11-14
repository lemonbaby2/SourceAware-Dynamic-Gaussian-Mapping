# -*- coding: utf-8 -*-
"""Rewrite the Related Work section so that the verified bibliography is
actually load-bearing rather than decorative.

Design rules:
  * every entry in references.bib must be cited at least once (asserted at the
    end of the run, so an uncited reference can never reach the manuscript);
  * each paragraph makes a claim about what a group of papers does *and* what
    it leaves unresolved, which is what the rest of the paper then attacks;
  * no numbers are invented here.  Quantitative claims stay in Results, where
    they are injected from the experiment JSON.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEX = HERE / "latex" / "main.tex"
BIB = HERE / "latex" / "references.bib"

RELATED = r"""\section{Related Work}
\subsection{Dynamic visual SLAM and why suppression is not enough}
Feature-based visual SLAM matured through a sequence of systems that separated tracking, local mapping, and loop closing, culminating in ORB-SLAM2 and its multi-map successor ORB-SLAM3 \cite{murartal2017orbslam2,campos2021orb}. Their robustness rests on geometric verification: correspondences that survive epipolar and reprojection tests are trusted, and the rest are discarded as outliers. DROID-SLAM replaced much of this front end with learned dense recurrent optimization and demonstrated that a single differentiable update operator can serve monocular, stereo, and RGB-D input \cite{teed2021droid}. Neither design eliminates the dynamic-scene problem. A moving object can satisfy epipolar constraints locally, and a learned residual can be minimized by deforming geometry rather than by rejecting a bad observation, so the failure is silent rather than loud.

The dynamic-SLAM literature therefore adds an explicit suppression stage. DS-SLAM couples semantic segmentation with a motion-consistency check, so a region is removed only when it is both semantically movable and geometrically inconsistent \cite{yu2018dsslam}. DynaSLAM uses instance segmentation together with multi-view geometry and additionally inpaints the removed regions so that the background remains reconstructible \cite{bescos2018dynaslam}; its multi-object extension carries the same idea into tightly coupled tracking \cite{bescos2021dynaslam2}. Detect-SLAM closes the loop in the other direction, letting detection improve mapping and mapping improve detection \cite{zhong2018detectslam}. Static-point weighting takes a softer route: instead of a binary decision, each residual receives a weight derived from its geometric consistency \cite{kim2018staticweight}. DynaMoN targets fast and robust localization when most of the field of view is moving \cite{ballester2025dynamon}.

Two lessons carry over to Gaussian mapping. First, ``dynamic'' is not a semantic category. Motion evidence, geometric consistency, temporal persistence, and semantic priors answer different questions and fail on different inputs, which is exactly why practical systems combine them. Second, the combination itself is rarely audited. Weights are multiplied, scores are averaged, or thresholds are tuned, and the resulting number is used to gate a map update without any statement about what the individual channels represent. Our contribution starts at that gap: we ask what happens when the channels being combined are derived from one another.

\subsection{Neural implicit and Gaussian scene representations}
NeRF established that a continuous radiance field optimized through differentiable volume rendering can synthesize novel views of unprecedented quality \cite{mildenhall2020nerf}. Adapting that idea to SLAM required solving the cost problem: NICE-SLAM introduced a hierarchical feature grid that scales to room-sized scenes \cite{zhu2022nice}, iMAP tracked a single MLP map in real time \cite{sucar2021imap}, Point-SLAM replaced the grid with neural points \cite{sandstrom2023pointslam}, NICER-SLAM improved the underlying encoding for RGB input \cite{zhu2024nicerslam}, Co-SLAM combined coordinate and parametric encodings \cite{wang2023coslam}, and Loopy-SLAM added loop closure to dense neural mapping \cite{yunus2024loopyslam}. These systems demonstrate that a photometric objective alone can drive both geometry and camera pose, but they inherit the same weakness as photometric bundle adjustment: a moving object is a perfectly valid explanation of the pixels it covers.

3D Gaussian splatting changed the cost structure again. By representing the scene with explicit anisotropic primitives and rasterizing them through differentiable alpha compositing, it achieves real-time rendering with an editable map \cite{kerbl2023}. Gaussian Splatting SLAM showed that a single Gaussian map can serve monocular tracking and photorealistic rendering at the same time \cite{matsuki2024}. SplaTAM specialized the representation to dense RGB-D tracking and mapping \cite{keetha2024splatam}, GS-SLAM introduced an adaptive densification and pruning strategy for SLAM \cite{yan2024gsslam}, and Photo-SLAM targeted real-time localization with photorealistic mapping \cite{huang2024photoslam}.

The explicit map cuts both ways for dynamic scenes. It makes contamination visible, because a wrongly retained observation becomes a persistent floating blob or a duplicated surface that a human can point at. It also makes contamination durable, because primitives added during one badly gated keyframe continue to be rasterized in every later view. In an implicit map the same error is smeared across the field and can be partially forgotten during continued optimization; in a Gaussian map it is a discrete object that must be actively removed. This asymmetry is the reason dynamic Gaussian SLAM is not merely dynamic neural SLAM with a different renderer.

\subsection{Dynamic Gaussian and dynamic neural mapping}
The most direct response is to add dynamic handling to the Gaussian pipeline. DG-SLAM combines dynamic masks with hybrid pose optimization and reports robustness where purely photometric tracking drifts \cite{xu2024dg}. WildGS-SLAM estimates per-pixel uncertainty from strong visual features and uses it to down-weight non-static residuals in monocular settings \cite{zheng2025wildgs}. GARAD-SLAM propagates anti-dynamic labels between the tracking and mapping stages in a real-time pipeline \cite{li2025garad}. Dy3DGS-SLAM fuses probabilistic optical-flow and depth evidence, adds scale-related constraints, and maps dynamic Gaussians explicitly \cite{li2025dy3dgs}.

A parallel line keeps the neural implicit renderer and attacks dynamics there. RoDyn-SLAM adds a dynamic-radiance formulation to dense RGB-D SLAM \cite{jiang2024rodynslam}. NID-SLAM handles dynamic environments with an implicit representation and an explicit dynamic treatment \cite{li2024nidslam}. DDN-SLAM pursues real-time dense dynamic neural implicit SLAM \cite{yuan2024ddnslam}.

The dynamic-scene representation literature supplies the modelling vocabulary these systems borrow. D-NeRF conditions a radiance field on time \cite{pumarola2021dnerf}, Deformable 3D Gaussians learn a deformation field over a canonical set of primitives \cite{yang2024deformable}, and 4D Gaussian Splatting extends the primitive set with a temporal component for real-time dynamic rendering \cite{wu20244dgs}. These methods are designed to \emph{represent} motion faithfully. A SLAM system has the opposite objective at the map level: it must represent the static scene while \emph{refusing} to represent motion. Reusing a deformation model without that distinction reproduces the moving object perfectly and thereby pollutes the map, which is why our experiment measures a dynamic ghost residual alongside static-region fidelity.

Among these, Dy3DGS-SLAM is the closest prior work and the honest comparison point. It already proposes probabilistic optical-flow/depth mask fusion, scale-related constraints, and dynamic Gaussian mapping. We therefore do not claim those components. What we examine is narrower and, we argue, prior to them: whether the probabilistic fusion itself is statistically well posed when several of its input channels are derived from the same measurement.

\subsection{The perception modules that produce the channels}
Every channel in a dynamic-mask pipeline comes from a network, and each network brings its own failure mode. Optical flow is estimated by FlowNet \cite{dosovitskiy2015flownet}, refined by all-pairs correlation volumes in RAFT \cite{teed2020raft}, and made transformer-based in FlowFormer \cite{huang2022flowformer}. Flow magnitude is therefore not a motion measurement; it is a measurement of image displacement that mixes camera motion, object motion, and estimation error. A flow residual after rigid compensation inherits the errors of the pose, the depth, and the occlusion reasoning used to compute it.

Depth is equally layered. UniDepth targets universal monocular metric depth and conditions on camera information \cite{piccinelli2024unidepth}, while Depth Anything V2 provides strong relative-depth representations \cite{yang2024depth}. A depth-inconsistency channel computed from either model inherits the model's behaviour under the exact conditions a dynamic scene creates: unfamiliar object scale, motion blur, and thin structures.

Semantics is the third source. Mask R-CNN supplies instance masks \cite{he2017maskrcnn}, DeepLab supplies dense semantic labels \cite{chen2018deeplab}, and Segment Anything supplies class-agnostic masks that can be prompted \cite{kirillov2023sam}. A clustering embedding computed on top of flow features is a fourth, and it is the clearest case of a channel that is a deterministic function of another channel: if the embedding is a transformation of the flow field, then a probability computed from the embedding cannot be independent evidence about motion in addition to the probability computed from the flow field itself.

This is the concrete situation our formulation addresses. Three channels named ``flow'', ``flow residual'', and ``flow cluster'' look like three experts. Statistically they are one expert counted three times.

\subsection{Probability pooling and the provenance question}
Combining distributions from several sources is a classical problem. Logarithmic pooling and its extensions define families of combination rules with known properties, and the choice among them encodes assumptions about dependence and about how much each source should be trusted \cite{decarvalho2023pool}. Evidence theory offers an alternative calculus in which belief and plausibility are separate quantities and combination is explicitly non-idempotent \cite{shafer1976evidence}. That non-idempotence is precisely the property that makes replication dangerous in our setting, and it is why we treat the family structure as a constraint on the pool rather than as a modelling detail.

Our rule is deliberately modest as a contribution to pooling theory. It is not claimed as a new general theorem about expert aggregation. It is a provenance constraint for engineering pipelines in which several channels can be deterministic or near-deterministic transformations of a common measurement: average within a family first, then combine across families with a fixed budget. The consequence we prove is exact invariance under replication inside a family, which is exactly the property the naive product lacks.

\subsection{Calibration and uncertainty in learned predictors}
A sigmoid output is not a probability. Guo et al. showed that modern deep networks are systematically overconfident and that simple post-hoc temperature scaling recovers much of the lost calibration \cite{guo2017calibration}. Deep ensembles provide a practical route to predictive uncertainty \cite{lakshminarayanan2017ensembles}, and the aleatoric/epistemic decomposition clarifies which part of an uncertainty estimate can be reduced with more data \cite{kendall2017uncertainties}. Ovadia et al. then showed that the gap between confidence and correctness widens under distribution shift \cite{ovadia2019trust}, which is precisely the regime a dynamic scene creates when an object class or motion pattern was absent from whatever data the calibration was fitted on. Surveys of confidence calibration in deep classification document how sensitive these conclusions are to class balance and to the evaluation protocol \cite{dong2025calsurvey}.

We report negative log likelihood, the Brier score, expected calibration error, and F1 together for this reason. F1 measures whether a decision threshold separates the classes; it says nothing about whether the number being thresholded is a probability. A fusion rule can improve discrimination while making calibration worse, and our stress test is constructed so that this divergence is visible rather than averaged away.

\subsection{Benchmarks and evaluation metrics}
Evaluation practice in this area is well established. The TUM RGB-D benchmark supplies synchronized colour, depth, and ground-truth trajectories with explicit dynamic sequences \cite{sturm2012tum}, and Replica provides photorealistic synthetic indoor scenes with perfect geometry \cite{straub2019replica}. Image fidelity is conventionally reported with SSIM \cite{wang2004ssim} and, when perceptual rather than pixel agreement matters, LPIPS \cite{zhang2018lpips}.

Our protocol uses a synthetic scene precisely because the benchmark question and the mechanism question are different. On a real dynamic benchmark, a difference in static-region PSNR can be attributed to mask quality, pose accuracy, depth scale, densification heuristics, or the loss itself; the attribution is what a benchmark cannot give. Conversely, a controlled synthetic study cannot establish real-sequence robustness, and we do not claim that it does. Section~\ref{sec:boundary} states which claims each experiment supports and which it does not, and Section~\ref{sec:required} lists what an end-to-end evaluation would have to add.

"""


def main():
    tex = TEX.read_text(encoding="utf-8")
    TEX.with_suffix(".tex.bak_before_related").write_text(tex, encoding="utf-8")

    pat = r"\\section\{Related Work\}.*?(?=\\section\{Problem Formulation)"
    if not re.search(pat, tex, flags=re.S):
        raise SystemExit("!! 未找到 Related Work 区块，先检查 main.tex 结构")
    tex = re.sub(pat, lambda _m: RELATED, tex, flags=re.S)
    TEX.write_text(tex, encoding="utf-8")
    print("Related Work rewritten:", len(RELATED), "chars inserted")

    # ---- coverage audit: no entry may be dead weight ----
    keys = re.findall(r"@\w+\{([^,]+),", BIB.read_text(encoding="utf-8"))
    cited = set()
    for grp in re.findall(r"\\cite\{([^}]+)\}", tex):
        cited |= {k.strip() for k in grp.split(",")}
    dead = [k for k in keys if k not in cited]
    print(f"bib entries: {len(keys)} | cited: {len(set(keys) & cited)} | uncited: {len(dead)}")
    if dead:
        print("  未引用:", ", ".join(dead))
    print(f"total distinct citation keys in manuscript: {len(cited)}")


if __name__ == "__main__":
    main()
