import json,urllib.request,urllib.parse,concurrent.futures,time
from pathlib import Path
OUT=Path(__file__).parent/'journal_metadata'
OUT.mkdir(exist_ok=True)
TITLES=[
('ptam2010','Parallel Tracking and Mapping on a camera phone'),
('monoslam2007','MonoSLAM: Real-Time Single Camera SLAM'),
('inverse2008','Inverse Depth Parametrization for Monocular SLAM'),
('dtam2015','Dense visual SLAM for RGB-D cameras'),
('sparse2015','Robust large-scale monocular SLAM with lazy data association'),
('surfels2017','ElasticFusion: Dense SLAM Without A Pose Graph'),
('sdf2013','Real-time 3D reconstruction at scale using voxel hashing'),
('doublefusion2018','DoubleFusion: Real-time Capture of Human Performances with Inner Body Shapes from a Single Depth Sensor'),
('dynamicfusion2015','DynamicFusion: Reconstruction and tracking of non-rigid scenes in real-time'),
('bayesdepth2021','Real-Time Dense Mapping for Self-Driving Vehicles using Fisheye Cameras'),
('sslamsurvey2022','A Survey of Simultaneous Localization and Mapping with an Envision in 6G Wireless Networks'),
('salas2015','Dense RGB-D semantic mapping with pixel-voxel neural networks'),
('relocal2015','InfiniTAM: A Framework for the Large-Scale Integration of Depth Images'),
('sceneflow2015','Scene Flow Estimation with a Piecewise Rigid Scene Model'),
('sceneflow2019','Piecewise Rigid Scene Flow'),
('deepflow2015','DeepMatching: Hierarchical Deformable Dense Matching'),
('pwc2020','Models Matter, So Does Training: An Empirical Study of CNNs for Optical Flow Estimation'),
('dis2017','Fast Optical Flow Using Dense Inverse Search'),
('bayesianfusion1997','A new approach to linear filtering and prediction problems'),
('cadena2016','Past, Present, and Future of Simultaneous Localization and Mapping: Toward the Robust-Perception Age'),
('orb2015','ORB-SLAM: A Versatile and Accurate Monocular SLAM System'),
('orb22017','ORB-SLAM2: An Open-Source SLAM System for Monocular, Stereo, and RGB-D Cameras'),
('dso2018','Direct Sparse Odometry'),
('elastic2016','ElasticFusion: Real-time dense SLAM and light source estimation'),
('vins2018','VINS-Mono: A Robust and Versatile Monocular Visual-Inertial State Estimator'),
('dynamicslam2007','Simultaneous Localization, Mapping and Moving Object Tracking'),
('dynaslam22021','DynaSLAM II: Tightly-Coupled Multi-Object Tracking and SLAM'),
('dynosam2024','DynoSAM: Open-Source Smoothing and Mapping Framework for Dynamic SLAM'),
('kimera2022','Kimera: From SLAM to Spatial Perception with 3D Dynamic Scene Graphs'),
('dense2018','Real-time large-scale dense RGB-D SLAM with volumetric fusion'),
('slamreview2019','A Review of Visual-LiDAR Fusion based Simultaneous Localization and Mapping'),
('lsd2018','Large-Scale Direct SLAM With Stereo Cameras'),
('svo2017','SVO: Semidirect Visual Odometry for Monocular and Multicamera Systems'),
('isam2012','iSAM2: Incremental smoothing and mapping using the Bayes tree'),
('gtsam2017','Factor Graphs for Robot Perception'),
('lsd2019','Direct Visual SLAM Using Sparse Depth for Camera-LiDAR System'),
('sift2004','Distinctive Image Features from Scale-Invariant Keypoints'),
('surf2008','SURF: Speeded Up Robust Features'),
('flow2014','A Database and Evaluation Methodology for Optical Flow'),
('flow2010','Large Displacement Optical Flow: Descriptor Matching in Variational Motion Estimation'),
('flowhorn1981','Determining Optical Flow'),
('epic2017','EpicFlow: Edge-Preserving Interpolation of Correspondences for Optical Flow'),
('ssim2004','Image Quality Assessment: From Error Visibility to Structural Similarity'),
('brisy2014','From image denoising to image quality assessment'),
('nerfsurvey2022','State of the Art on Neural Rendering'),
('neuralrender2022','Advances in Neural Rendering'),
('instant2022','Instant Neural Graphics Primitives with a Multiresolution Hash Encoding'),
('mip2022','Mip-NeRF 360: Unbounded Anti-Aliased Neural Radiance Fields'),
('ewasplat2002','EWA Splatting'),
('surfacesplat2001','Surface Splatting'),
('3dgs2024survey','A Survey on 3D Gaussian Splatting'),
('proper2007','Strictly Proper Scoring Rules, Prediction, and Estimation'),
('pool2013','Combining Predictive Distributions'),
('forecast2007','Probabilistic forecasts, calibration and sharpness'),
('uncertainty2021','A Review of Uncertainty Quantification in Deep Learning: Techniques, Applications and Challenges'),
('calibration2023','Calibration of Neural Networks: A Survey of the State-of-the-Art'),
('eu2016','The EuRoC micro aerial vehicle datasets'),
('kitti2013','Vision meets robotics: The KITTI dataset'),
('rgbd2013','3-D Mapping With an RGB-D Camera'),
('rgbdsurvey2020','RGB-D SLAM in Dynamic Environments: A Survey'),
('robust1964','Robust Estimation of a Location Parameter'),
('ransac1981','Random Sample Consensus: A Paradigm for Model Fitting with Applications to Image Analysis and Automated Cartography'),
]
def fetch(pair):
 key,title=pair;p=OUT/(key+'.json')
 if p.exists():return json.loads(p.read_text(encoding='utf-8'))
 time.sleep(2)
 url='https://api.crossref.org/works?'+urllib.parse.urlencode({'query.title':title,'rows':3,'filter':'type:journal-article'})
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'ManuscriptReferenceAudit/1.0'})
  data=json.load(urllib.request.urlopen(req,timeout=45))['message']['items']
  result={'key':key,'query':title,'candidates':data}
  p.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
  return result
 except Exception as e:return {'key':key,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
 for result in pool.map(fetch,TITLES):
  if 'error' in result:print(result,flush=True);continue
  c=result['candidates'][0]
  print(result['key'],c.get('title'),c.get('container-title'),c.get('type'),c.get('DOI'),flush=True)
