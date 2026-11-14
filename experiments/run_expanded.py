"""Additional GPU ablations; frozen split, held-out true masks for evaluation."""
import json, time, hashlib, sys
from pathlib import Path
import numpy as np
import torch
import renderer_original as R
from protocol import split_ids, select_frames

HERE=Path(__file__).resolve().parent
OUT=HERE/'expanded_results'
OUT.mkdir(exist_ok=True)
gpu=next(i for i in range(torch.cuda.device_count()) if '5060 Ti' in torch.cuda.get_device_name(i))
torch.cuda.set_device(gpu)
R.DEV=f'cuda:{gpu}'
R.DATA=r'E:\研究生学习\dy3dgs-thesis-repro\synthetic\code\data_dyn'
meta,K,frames=R.load_scene()
train_ids,test_ids=split_ids(len(frames))
tests=select_frames(frames,test_ids)
original_bp=R.backproject
manifest={'scope':'synthetic known-pose mapping; oracle depth; controlled mask perturbations',
 'gpu':torch.cuda.get_device_name(gpu),'torch':torch.__version__,'cuda':torch.version.cuda,
 'train_ids':train_ids,'test_ids':test_ids,'seeds':[0,1,2],'iterations':1200,'points':2500,
 'configs':['loss_only','false_negative_20','false_positive_20'],
 'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
for seed in [0,1,2]:
 for config in manifest['configs']:
  run=OUT/f'seed{seed}_{config}'
  run.mkdir(exist_ok=True)
  if (run/'metrics.json').exists(): continue
  train=[dict(f) for f in select_frames(frames,train_ids)]
  rng=np.random.default_rng(seed+900)
  changed,total=0,0
  for f in train:
   true=f['dyn'].clone()
   candidates=(true>=0.5) if config=='false_negative_20' else (true<0.5)
   flip=torch.as_tensor(rng.random(tuple(true.shape))<0.2,device=R.DEV)&candidates
   if config!='loss_only':
    f['dyn']=torch.where(flip,1-true,true)
    changed+=int(flip.sum());total+=int(candidates.sum())
  if config=='loss_only':
   def all_pixel_bp(*args,**kwargs):
    kwargs['exclude_dynamic']=False
    return original_bp(*args,**kwargs)
   R.backproject=all_pixel_bp
  else: R.backproject=original_bp
  print(f'START {config} seed={seed}',flush=True)
  torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();start=time.perf_counter()
  model,hist,used,_=R.train('dyn-mask',train,K,meta,iters=1200,max_points=2500,seed=seed,log_every=300)
  torch.cuda.synchronize();elapsed=time.perf_counter()-start
  rows,agg=R.evaluate(model,tests,K,meta)
  for row,index in zip(rows,test_ids):row['frame']=index
  rendered=[]
  with torch.no_grad():
   for f in tests:
    im,_=R.rasterize(model,f['R'],f['t'],K,meta['H'],meta['W'])
    rendered.append(im[0].permute(1,2,0).clamp(0,1).cpu().numpy())
  np.savez_compressed(run/'renders.npz',rgb=np.stack(rendered),view_ids=test_ids)
  torch.save(model.state_dict(),run/'model.pt')
  (run/'history.json').write_text(json.dumps(hist,indent=2))
  result={'seed':seed,'config':config,'agg':agg,'per_frame':rows,'train_wall_s':elapsed,
   'actual_error_rate':changed/max(total,1),'peak_allocated_bytes':torch.cuda.max_memory_allocated()}
  (run/'metrics.json').write_text(json.dumps(result,indent=2))
  print('DONE '+json.dumps(result),flush=True)
print('ALL_DONE',flush=True)
