"""Synthetic evidence replication stress test; not a real motion detector."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar
from protocol import family_log_pool
OUT=Path(__file__).resolve().parent/'fusion_results'
OUT.mkdir(exist_ok=True)
def sigmoid(x):return 1/(1+np.exp(-np.clip(x,-40,40)))
def nll(y,p):
 p=np.clip(p,1e-8,1-1e-8)
 return float(-np.mean(y*np.log(p)+(1-y)*np.log1p(-p)))
def metrics(y,p):
 b=p>=.5;tp=np.sum(b&(y==1));fp=np.sum(b&(y==0));fn=np.sum(~b&(y==1))
 ece=0.
 for lo in np.arange(0,1,.1):
  m=(p>=lo)&(p<lo+.1)
  if m.any():ece+=m.mean()*abs(p[m].mean()-y[m].mean())
 return {'nll':nll(y,p),'brier':float(np.mean((p-y)**2)),'ece10':float(ece),'f1':float(2*tp/max(2*tp+fp+fn,1))}
rows=[]
for seed in range(10):
 rng=np.random.default_rng(seed)
 z=rng.normal(-1,1.8,60000);y=rng.binomial(1,sigmoid(z))
 motion=z+rng.normal(0,.9,len(z));geometry=z+rng.normal(0,.9,len(z))
 calibration=np.arange(10000);test=np.arange(10000,60000)
 base=(motion+geometry)/2
 opt=minimize_scalar(lambda t:nll(y[calibration],sigmoid(base[calibration]/t)),bounds=(.2,5),method='bounded')
 temperature=float(opt.x)
 for copies in [1,2,4,8]:
  # Calibrate once using two unique families; keep temperature fixed during stress.
  p_family=sigmoid(base[test]/temperature)
  p_product=sigmoid((copies*motion[test]+geometry[test])/(2*temperature))
  p_channel_mean=sigmoid((copies*motion[test]+geometry[test])/((copies+1)*temperature))
  for name,p in [('fixed_product',p_product),('channel_mean',p_channel_mean),('family_pool',p_family)]:
   rows.append({'seed':seed,'motion_copies':copies,'method':name,'temperature':temperature,**metrics(y[test],p)})
summary=[]
for copies in [1,2,4,8]:
 for method in ['fixed_product','channel_mean','family_pool']:
  rs=[r for r in rows if r['motion_copies']==copies and r['method']==method]
  row={'copies':copies,'method':method}
  for key in ['nll','brier','ece10','f1']:
   a=np.array([r[key] for r in rs]);row[key]={'mean':float(a.mean()),'std':float(a.std(ddof=1))}
  summary.append(row)
(OUT/'results.json').write_text(json.dumps({'protocol':'logistic latent-variable simulation, 10000 calibration and 50000 test samples per seed, 10 seeds; exact replicated motion evidence; not image-based motion segmentation','rows':rows,'summary':summary},indent=2))
for r in summary:print(r,flush=True)
