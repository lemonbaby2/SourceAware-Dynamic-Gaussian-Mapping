import json,re
from pathlib import Path
HERE=Path(__file__).parent;ROOT=HERE.parent;REV=ROOT/'revision_20261114'
summary=json.loads((REV/'additional_results.json').read_text())
p=REV/'latex/main.tex';tex=p.read_text(encoding='utf-8')
def ms(c,k,d=3):
 v=summary[c][k];return f"{v['mean']:.{d}f}\\pm{v['sd']:.{d}f}"
rows=[]
configs=['naive','no-dyn-data','loss_only','dyn-mask','false_negative_20','false_positive_20']
labels=['All pixels','Initialization only','Loss only','Initialization + loss','20\\% false negatives','20\\% false positives']
for c,label in zip(configs,labels):
 rows.append(label+' & $'+ms(c,'psnr_static_mean')+'$ & $'+ms(c,'ghost_residual_mean',4)+'$ \\\\')
block=r'''
\subsection{Separating initialization from loss masking}
The original three configurations leave one causal question unresolved: whether loss masking alone recovers the benefit without static-only initialization. We add this fourth configuration with seeds 0, 1, and 2. All observations can initialize the map, while the loss uses the oracle static-validity mask. The training split, 2,500 primitives, 1,200 iterations, and four held-out views match the other configurations. Table~\ref{tab:newruns} and Fig.~\ref{fig:newruns} compare the common three-seed subset; the five-seed main table remains a separate summary.

Loss-only masking reaches $LOSSPSNR$ dB and a ghost residual of $LOSSGHOST$. Initialization plus loss masking reaches $FULLPSNR$ dB and $FULLGHOST$, respectively. The combined intervention improves static-region fidelity over loss masking alone, but their ghost residuals are close. Thus loss masking accounts for much of the transient-suppression effect in this scene, while initialization filtering supplies an additional static-fidelity benefit. These measurements do not support a claim that both stages are necessary to minimize every metric.

\begin{table}[t]
\centering\scriptsize
\caption{Matched three-seed intervention and fixed mask-error tests. Mean and sample SD; evaluated with uncorrupted held-out masks.}
\label{tab:newruns}
\begin{tabular}{lcc}\toprule
Configuration & Static PSNR & Ghost L1 \\
\midrule
ROWS
\bottomrule\end{tabular}
\end{table}

\begin{figure*}[t]
\centering\includegraphics[width=.94\textwidth]{matched_interventions.png}
\caption{Matched-seed intervention and mask-error results. Points are individual runs and bars show means with sample SD. The three-seed comparison uses identical training budgets and held-out views.}
\label{fig:newruns}
\end{figure*}

\subsection{Fixed false-negative and false-positive masks}
The earlier label-flip sweep resamples random corruption during optimization and leaves initialization clean. We additionally test fixed masks shared by initialization and loss. A false-negative trial changes 20\% of dynamic pixels to static, independently per training frame. A false-positive trial changes 20\% of static pixels to dynamic. These are class-conditional rates: because the classes occupy different image areas, they are not equal fractions of all pixels. The sampled masks are held fixed for all iterations in a run; ground-truth held-out masks are retained for evaluation.

False-negative corruption yields $FNPSNR$ dB with ghost residual $FNGHOST$, and false-positive corruption yields $FPPSNR$ dB with residual $FPGHOST$. This directly measures two distinct mechanisms: leaked dynamic observations can contaminate the map, whereas discarded static observations reduce support. The outcome remains conditional on independent pixel errors and a small synthetic scene. Spatially coherent segmentation failures, incorrect poses, and real image noise are not reproduced by this test.

\begin{figure*}[t]
\centering\includegraphics[width=.98\textwidth]{new_gpu_renders.png}
\caption{GPU-rendered held-out comparisons for seed 0. Every declared held-out view is shown. Columns use the same camera and native $160\times120$ arrays; nearest-neighbor enlargement is used for display. The clean target excludes the moving object.}
\label{fig:newrenders}
\end{figure*}

\begin{figure*}[t]
\centering\includegraphics[width=.94\textwidth]{new_error_maps.png}
\caption{Per-pixel mean absolute RGB error against the static target for the same held-out views and seed. All panels share the color scale, clipped at 0.15 for visibility. Clipping applies only to the plotted color range; reported metrics use the unclipped arrays.}
\label{fig:newerrors}
\end{figure*}

\subsection{Reading the rendered comparisons}
Figures~\ref{fig:newrenders} and~\ref{fig:newerrors} connect aggregate values to the underlying pixels. The input column contains the moving foreground, whereas the static target defines the persistent-map objective. A renderer that accurately reproduces the foreground can therefore have a lower dynamic-input error and a higher ghost residual at the same time. This is why whole-image fidelity to the observed frame is insufficient for assessing static-map contamination.

All four held-out views are displayed in their declared order. The error maps use one color scale so that an apparent improvement cannot result from independently rescaling each panel. The visualizations are produced from saved float arrays; the artifact additionally retains the original model checkpoints and newly rendered baseline arrays. The native resolution limits the fine geometry that can be assessed, and enlargement adds no spatial information. The figure should therefore be read as a comparison of contamination patterns and static support, not as evidence of high-resolution reconstruction quality.

The individual run points also matter. With only three seeds, a small difference in the mean ghost residual should not be treated as a general ranking. The stable result is the separation between unmasked training and loss-masked configurations; the residual distinction among well-masked configurations is much smaller. Reporting both individual runs and per-view panels exposes this scale difference and avoids interpreting every visible bar separation as a meaningful system advantage.
'''
for token,c,k,d in [('LOSSPSNR','loss_only','psnr_static_mean',3),('LOSSGHOST','loss_only','ghost_residual_mean',4),('FULLPSNR','dyn-mask','psnr_static_mean',3),('FULLGHOST','dyn-mask','ghost_residual_mean',4),('FNPSNR','false_negative_20','psnr_static_mean',3),('FNGHOST','false_negative_20','ghost_residual_mean',4),('FPPSNR','false_positive_20','psnr_static_mean',3),('FPGHOST','false_positive_20','ghost_residual_mean',4)]:block=block.replace(token,ms(c,k,d))
block=block.replace('ROWS','\n'.join(rows))
tex=tex.replace(r'\section{Discussion}',block+'\n'+r'\section{Discussion}')
tex=tex.replace('the masked optimization loss is necessary to obtain the largest and most consistent reduction in transient artifacts','loss masking supplies most of the observed transient suppression, while initialization filtering further improves static-region fidelity')
tex=tex.replace('The combined masked configuration at three training budgets.','The combined masked configuration at two additional training budgets.')
tex=tex.replace('A capacity, optimization-budget, and mask-quality ablation matrix shows that the gain survives implementation choices and degrades gracefully as mask labels are corrupted.','Additional capacity and budget sweeps characterize the combined configuration, and matched three-seed tests isolate loss-only masking and fixed false-negative and false-positive mask errors.')
# A reference to the source-provenance limitation stays in the method, rather
# than repeating an editorial checklist throughout the Introduction.
tex=tex.replace('We release per-seed','We retain per-seed')
p.write_text(tex,encoding='utf-8')
tables=json.loads((HERE/'tables_data.json').read_text(encoding='utf-8'))
abl=tables['tab:ablation']['rows']
tables['tab:ablation']['rows']=[r for r in abl if not any('soft' in str(x).lower() for x in r)]
for r in tables['tab:ablation']['rows']:
 for i,v in enumerate(r):
  if isinstance(v,str):r[i]=v.replace('dilated +2 px','static expanded 2 px').replace('eroded -2 px','static contracted 2 px')
 if str(r[-1])=='1':
  for i,v in enumerate(r):
   if isinstance(v,str) and '±' in v:r[i]=v.split('±')[0]
tables['tab:newruns']={'caption':'Matched three-seed intervention and fixed mask-error tests. Mean ± sample SD; evaluated with uncorrupted held-out masks.','header':['Configuration','Static PSNR','Ghost L1'],'rows':[[label.replace('\\%','%'),ms(c,'psnr_static_mean').replace('\\pm','±'),ms(c,'ghost_residual_mean',4).replace('\\pm','±')] for c,label in zip(configs,labels)]}
(REV/'tables_data.json').write_text(json.dumps(tables,ensure_ascii=False,indent=2),encoding='utf-8')
print('Integrated new results and corrected tables')
