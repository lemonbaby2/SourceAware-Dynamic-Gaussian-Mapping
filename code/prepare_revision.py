"""Build an isolated revision from audited sources and preserved prior outputs."""
import json,re,shutil,html,unicodedata
from pathlib import Path
HERE=Path(__file__).parent
ROOT=HERE.parent
REV=ROOT/'revision_20261114'
(REV/'latex').mkdir(parents=True,exist_ok=True)
(REV/'figures').mkdir(exist_ok=True)
for p in (HERE/'figures').glob('*.png'):shutil.copy2(p,REV/'figures'/p.name)

GROUPS={
'estimation': ['cadena2016','orb2015','monoslam2007','inverse2008','dso2018','vins2018','svo2017','isam2012'],
'dynamic': ['dynamicslam2007','dynosam2024','kimera2022','doublefusion2018'],
'dense': ['elastic2016','dense2018','rgbd2013','sdf2013'],
'render': ['nerfsurvey2022','neuralrender2022','instant2022','ewasplat2002'],
'flow': ['sift2004','flow2014','flow2010','sceneflow2019','deepflow2015','pwc2020'],
'probability': ['proper2007journal','forecast2007journal','pool2013','uncertainty2021','robust1964journal','ransac1981journal'],
'datasets': ['eu2016','kitti2013'],
}
def esc(s):
 s=html.unescape(re.sub('<[^>]+>','',str(s)))
 s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode()
 return s.replace('&',r'\&').replace('%',r'\%').replace('_',r'\_')
bib=(HERE/'latex/references.bib').read_text(encoding='utf-8')
audit=[]
for group,keys in GROUPS.items():
 for key in keys:
  p=HERE/'journal_metadata'/f'{key}.json'
  if not p.exists():raise RuntimeError(f'Missing audited reference {key}')
  c=json.loads(p.read_text(encoding='utf-8'))['candidates'][0]
  assert c['type']=='journal-article',(key,c['type'])
  doi=c['DOI'];title=c['title'][0];venue=c['container-title'][0]
  assert doi.lower() not in bib.lower(),('duplicate DOI',key)
  authors=' and '.join(esc(a.get('given','')+' '+a.get('family','')) for a in c.get('author',[]))
  year=c.get('published-print',c.get('published',c['issued']))['date-parts'][0][0]
  fields={'author':authors,'title':'{'+esc(title)+'}','journal':esc(venue),'year':str(year),'doi':doi,
   'volume':c.get('volume',''),'number':c.get('issue',''),'pages':c.get('page','')}
  bib+='\n@article{'+key+',\n'+',\n'.join('  '+k+' = {'+str(v)+'}' for k,v in fields.items() if v)+'\n}\n'
  audit.append({'key':key,'title':title,'venue':venue,'year':year,'doi':doi,'source':'https://api.crossref.org/works/'+doi})
(REV/'latex/references.bib').write_text(bib,encoding='utf-8')
(REV/'added_reference_audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding='utf-8')

tex=(HERE/'latex/main.tex').read_text(encoding='utf-8')
# Fix the scope of the invariance guarantee; individual duplicate insertion is
# not invariant for a family with heterogeneous channels.
tex=tex.replace('when a channel inside a family is duplicated','when every channel in a family is replicated equally')
tex=tex.replace('exactly invariant to replication within a family','exactly invariant to uniform replication of all channels within a family')
tex=tex.replace('The guarantee holds for any number of copies and does not require the duplicated channel to be accurate.','The guarantee covers equal replication of the complete family; duplicating only one member of a heterogeneous family changes its mean and is outside this guarantee.')
tex=tex.replace('A sigmoid output is not a probability.','A sigmoid output lies in the probability range, but its calibration must be established empirically.')
tex=tex.replace('ten equal-frequency bins','ten equal-width bins')
tex=tex.replace('Runs are independent processes with different random seeds','Runs use different random seeds and freshly initialized models')
tex=tex.replace('Section~\\ref{sec:required} lists the protocol','The validation discussion lists the protocol')
tex=tex.replace('Section~\\ref{sec:required} lists what an end-to-end evaluation would have to add.','The validation discussion identifies the additional end-to-end evidence required.')
# General claims that overreach the actual implementation.
tex=tex.replace('Gaussian systems add a failure channel that classical methods do not have:', 'In Gaussian mapping, this contamination has a visible representation:')
tex=tex.replace('It examines a narrower statistical assumption that silently affects all of the systems above.','It examines a statistical failure mode that can arise when a pipeline multiplies evidence derived from shared measurements.')
tex=tex.replace('The multiplication is usually justified by a conditional-independence assumption that is never tested.','Multiplication requires an explicit model of dependence; the assumption becomes questionable when channels share measurements.')
tex=tex.replace('A typical dynamic-mask front end constructs several channels from the same measurements.','A dynamic-mask front end can construct several channels from the same measurements.')
tex=tex.replace('are routinely concatenated and multiplied','may be concatenated or combined through a product rule')

lit=r'''
\subsection{Connections to estimation and representation}
The long-term SLAM objective includes consistent geometry, reliable localization, and operation under changing observations \cite{cadena2016}. MonoSLAM and ORB-SLAM illustrate early probabilistic and feature-based routes to camera tracking \cite{monoslam2007,orb2015}, while inverse-depth parameterization addresses the conditioning of monocular structure estimation \cite{inverse2008}. Direct Sparse Odometry and SVO use photometric information with different choices about feature selection and optimization \cite{dso2018,svo2017}. These alternatives matter here because a map-quality improvement does not determine how a particular tracker will respond to discarded pixels. VINS-Mono further changes the information available by introducing inertial measurements \cite{vins2018}; comparing such a system against a vision-only mapper requires explicit sensor accounting. Incremental smoothing in iSAM2 provides another reminder that a complete SLAM claim includes estimation machinery beyond the renderer \cite{isam2012}.

Mapping and moving-object tracking have long been studied jointly \cite{dynamicslam2007}. DynoSAM makes dynamic smoothing and mapping explicit \cite{dynosam2024}, while Kimera represents spatial and semantic relationships through dynamic scene graphs \cite{kimera2022}. Consequently, suppression is one choice for a persistent static map, not the universal objective of dynamic SLAM. DoubleFusion instead reconstructs human shape and motion \cite{doublefusion2018}. Our clean-background metric is appropriate for the suppression objective; a dynamic reconstruction task would require a different target and should reward correctly reconstructed moving objects.

Dense RGB-D reconstruction supplies alternative choices for persistent geometry. ElasticFusion uses a dense map and estimates illumination \cite{elastic2016}; volumetric fusion and RGB-D mapping connect local observations to larger reconstructions \cite{dense2018,rgbd2013}. Voxel hashing addresses the allocation of volumetric storage \cite{sdf2013}. The present Gaussian experiment fixes its primitive budget, so its ablations cannot establish superiority over these adaptive representations. They isolate the consequences of masking under one stated allocation policy.

Neural rendering surveys describe a broad space of representations and image-formation models \cite{nerfsurvey2022,neuralrender2022}. Instant neural graphics primitives demonstrate the efficiency of multiresolution hash encoding \cite{instant2022}; EWA splatting provides a foundation for projecting and filtering splat primitives \cite{ewasplat2002}. These connections motivate separating representation, rasterization, and inference in an experimental comparison. A change in GPU renderer or filtering can alter apparent quality even when the dynamic decision rule is unchanged.

\subsection{Measurement uncertainty and evaluation}
SIFT illustrates that a descriptor is a transformation of image measurements \cite{sift2004}; introducing additional descriptors does not by itself create an independent sensor. Optical-flow evaluation requires attention to discontinuities, motion magnitude, and occlusion \cite{flow2014}. Large-displacement flow and DeepMatching address difficult correspondences \cite{flow2010,deepflow2015}, while empirical studies of learned flow show the importance of model and training choices \cite{pwc2020}. Piecewise rigid scene flow introduces geometric structure into motion estimation \cite{sceneflow2019}. A residual or clustering channel constructed downstream of these measurements inherits both their information and their errors. Provenance should therefore be recorded as part of the inference specification.

Proper scoring rules formalize the distinction between an accurate probability forecast and a correct thresholded decision \cite{proper2007journal}. Calibration and sharpness describe complementary qualities of a predictive distribution \cite{forecast2007journal}, and predictive-distribution combination has a broader statistical literature than the particular family mean used here \cite{pool2013}. Uncertainty quantification also includes model and data uncertainty that a provenance constraint alone cannot resolve \cite{uncertainty2021}. Robust estimation and random sample consensus offer complementary mechanisms for limiting the influence of inconsistent observations \cite{robust1964journal,ransac1981journal}. Our pool constrains how a measurement is counted; it does not replace robust geometric estimation or establish that the measurement is correct.

Dataset choice further determines the meaning of a result. EuRoC contains visual-inertial observations with a specific acquisition setup \cite{eu2016}, whereas KITTI targets driving scenarios \cite{kitti2013}. Their trajectories, motion patterns, and sensing configurations differ from our rendered scene. They are relevant evaluation contexts for future systems, but none of their published scores is imported into the present result tables.
'''
tex=tex.replace(r'\section{Problem Formulation and Claim Boundary}',lit+'\n'+r'\section{Problem Formulation and Claim Boundary}')
# Remove repetitive audit appendices; release full tables as machine-readable data.
tex=tex.split(r'\appendices')[0]+r'''
\appendices
\section{Reproducibility Details}
All mapping runs use the fixed eight-view training split and four held-out views specified in the experimental protocol. The artifact retains per-run metrics, random seeds, optimization histories, model parameters, and original rendered outputs. The main experiment has five seeds per configuration. Capacity, budget, and label-flip sweeps have two seeds per setting; morphology checks have one run and therefore provide no estimate of run-to-run variation. Additional intervention and class-conditional mask-error tests use three matched seeds. Mean and sample standard deviation are reported where at least two runs are available; a one-run result is reported without a standard deviation.

Figures use the stored output arrays, shared axes, and common error-map limits. Crops are identified in their captions. Enlarged renderings use nearest-neighbor display; no image synthesis or content retouching is applied. Image panels retain the original synthetic-scene resolution of $160\times120$. The release contains the numeric arrays needed to reproduce plots independently of document formatting.

\bibliographystyle{IEEEtran}
\bibliography{references}
\end{document}
'''
# The redundant full tables formerly appeared only in appendices.
tex=tex.replace('Appendix~A','the released full results').replace('Appendix~B','the released full results')
tex=tex.replace('and mask morphology (soft versus hard, dilated versus eroded)','and class-conditional mask errors')
tex=tex.replace('the mask morphology (soft versus hard, dilated versus eroded)','class-conditional mask errors')
tex=tex.replace('Because all-pixel training also benefits from a longer schedule, the comparison that matters is the gap between configurations at a matched budget, and that gap is preserved.','Only the combined masked configuration was run in this budget sweep. It establishes sensitivity within that configuration; it does not establish a matched-budget gap against the other configurations.')
tex=tex.replace('A longer optimization benefits the masked configuration and also benefits the baselines, which is why the comparison must be made at a matched budget. At every budget tested, the masked configuration remains ahead on static-region PSNR.','The budget sweep evaluates only the combined masked configuration. Its improvement with additional iterations is a within-configuration result; baseline comparisons at 600 and 2,400 iterations remain unmeasured.')
tex=tex.replace('Longer schedules help every configuration, so the relevant quantity is the gap at a matched budget rather than the endpoint of a single run.','The combined masked configuration at three training budgets. The other configurations were not evaluated at the two additional budgets.')
tex=tex.replace('Flipping labels at a controlled rate degrades static-region PSNR and raises the ghost residual monotonically, which is the expected direction and also the honest limit of the claim: the measured advantage is an upper bound that scales with mask quality, and this experiment cannot substitute for evaluating a real predictor.','The observed static-region PSNR is 31.59, 31.61, and 31.55 dB at 5, 10, and 20 percent label-flip rates. This response is small and non-monotone. Noise is resampled during optimization and affects the loss mask while initialization retains oracle labels. It therefore measures stochastic loss-mask corruption, rather than a fixed erroneous segmentation front end.')
tex=re.sub(r'\\textbf\{Mask morphology\.\}.*?(?=\\begin\{table\})',r'\\textbf{Morphology audit.} The implementation applies max pooling to the static-validity mask. Positive dilation expands static support, equivalently eroding the excluded dynamic region; negative dilation contracts static support. The nominal soft mask equals the hard mask for binary labels and is not treated as a distinct soft-mask experiment.\n\n',tex,flags=re.S)
tex=re.sub(r'Fig\.~\\ref\{fig:maskshape\}.*?\\end\{figure\*\}', '',tex,flags=re.S)
tex=re.sub(r'Morphology & soft weight.*?\\\\\n','',tex)
tex=tex.replace('Morphology & dilated +2 px','Static support & expanded 2 px').replace('Morphology & eroded -2 px','Static support & contracted 2 px')
tex=tex.replace('31.24$\\pm$0.00','31.24').replace('0.0066$\\pm$0.0000','0.0066').replace('31.20$\\pm$0.00','31.20').replace('0.0065$\\pm$0.0000','0.0065')
# Remove an editorial checklist from scientific contributions and consolidate to four.
tex=tex.replace('The contributions are fivefold.','We make four contributions:')
tex=re.sub(r'\\item \\textbf\{A reporting discipline.*?(?=\\end\{enumerate\})','',tex,flags=re.S)
tex=tex.replace('a single Gaussian map can serve monocular tracking and photorealistic rendering at the same time','a Gaussian map can support monocular tracking and photorealistic rendering')
tex=tex.replace('In an implicit map the same error is smeared across the field and can be partially forgotten during continued optimization; in a Gaussian map it is a discrete object that must be actively removed. This asymmetry is the reason dynamic Gaussian SLAM is not merely dynamic neural SLAM with a different renderer.','Both implicit and explicit maps can retain transient content. The form of that content depends on representation and optimization, so the present experiment evaluates the Gaussian case directly.')
tex=tex.replace('A SLAM system has the opposite objective at the map level: it must represent the static scene while \\emph{refusing} to represent motion.','A static-background mapper instead seeks a persistent reconstruction after excluding moving observations.')
(REV/'latex/main.tex').write_text(tex,encoding='utf-8')
print('PREPARED',len(audit),'added journal references',len(re.findall(r'^@',bib,re.M)),'total')
