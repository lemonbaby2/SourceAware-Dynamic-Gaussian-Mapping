"""Known-pose synthetic mapping experiment, NOT end-to-end monocular SLAM.
Oracle depth initializes training views. Oracle masks are used only by two
explicit oracle controls. Held-out images never initialize or optimize a map.
"""
import os,sys,json,time,hashlib,platform
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from protocol import split_ids, select_frames

HERE=Path(__file__).resolve().parent
os.chdir(HERE)
import renderer_original as R
DATA=Path(r'E:\研究生学习\dy3dgs-thesis-repro\synthetic\code\data_dyn')
OUT=HERE/'heldout_results'
OUT.mkdir(exist_ok=True)
gpu=next(i for i in range(torch.cuda.device_count()) if '5060 Ti' in torch.cuda.get_device_name(i))
torch.cuda.set_device(gpu)
R.DEV=f'cuda:{gpu}'
R.DATA=str(DATA)
meta,K,frames=R.load_scene()
train_ids,test_ids=split_ids(len(frames))
train_frames=select_frames(frames,train_ids)
test_frames=select_frames(frames,test_ids)
ITERS=1200
POINTS=2500
SEEDS=[0,1,2]
MODES=['naive','no-dyn-data','dyn-mask']
manifest={'task':'known-pose synthetic static mapping with oracle depth; no SLAM accuracy measured',
 'gpu':torch.cuda.get_device_name(gpu),'torch':torch.__version__,'cuda':torch.version.cuda,
 'python':sys.version,'platform':platform.platform(),'iterations':ITERS,'points':POINTS,
 'train_ids':train_ids,'test_ids':test_ids,'seeds':SEEDS,'modes':MODES,
 'renderer_sha256':hashlib.sha256((HERE/'renderer_original.py').read_bytes()).hexdigest(),
 'data_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.glob('*')) if p.is_file()},
 'metric_note':'SSIM is the inherited box-window implementation, not claimed identical to other publications'}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
all_runs=[]
for seed in SEEDS:
 for mode in MODES:
  run=OUT/f'seed{seed}_{mode}'
  run.mkdir(exist_ok=True)
  result_file=run/'metrics.json'
  if result_file.exists():
   all_runs.append(json.loads(result_file.read_text()));continue
  print(f'START seed={seed} mode={mode} GPU={manifest["gpu"]}',flush=True)
  torch.cuda.reset_peak_memory_stats()
  torch.cuda.synchronize()
  t0=time.perf_counter()
  model,hist,used,tt=R.train(mode,train_frames,K,meta,iters=ITERS,max_points=POINTS,seed=seed,log_every=300)
  torch.cuda.synchronize()
  train_s=time.perf_counter()-t0
  assert all(train_ids[i] not in test_ids for i in used)
  rows,agg=R.evaluate(model,test_frames,K,meta)
  for row,i in zip(rows,test_ids): row['frame']=i
  clean_psnr=[]
  for j,f in enumerate(test_frames):
   with torch.no_grad(): image,_=R.rasterize(model,f['R'],f['t'],K,meta['H'],meta['W'])
   rgb=image[0].permute(1,2,0).clamp(0,1).cpu().numpy()
   clean=f['clean'].cpu().numpy()
   clean_psnr.append(R.psnr(rgb,clean))
   rows[j]['clean_background_psnr']=clean_psnr[-1]
   if seed==0:
    panels=[f['rgb'].cpu().numpy(),rgb,clean]
    Image.fromarray((np.concatenate(panels,axis=1)*255).clip(0,255).astype('uint8')).save(run/f'view_{test_ids[j]:03d}.png')
  f=test_frames[0]
  with torch.no_grad():
   for _ in range(5): R.rasterize(model,f['R'],f['t'],K,meta['H'],meta['W'])
   torch.cuda.synchronize();t1=time.perf_counter()
   for _ in range(20): R.rasterize(model,f['R'],f['t'],K,meta['H'],meta['W'])
   torch.cuda.synchronize();render_s=(time.perf_counter()-t1)/20
  result={'seed':seed,'mode':mode,'test_ids':test_ids,'train_ids':train_ids,'agg':agg,'per_frame':rows,
   'clean_background_psnr_mean':float(np.mean(clean_psnr)),'train_wall_s':train_s,
   'render_ms':render_s*1000,'peak_allocated_bytes':torch.cuda.max_memory_allocated(),
   'iterations':ITERS,'points':POINTS}
  torch.save(model.state_dict(),run/'model.pt')
  R.save_ply(model,str(run/'gaussians.ply'))
  (run/'history.json').write_text(json.dumps(hist,indent=2))
  result_file.write_text(json.dumps(result,indent=2));all_runs.append(result)
  print('DONE '+json.dumps(result['agg']),flush=True)
  del model;torch.cuda.empty_cache()
stats={}
for mode in MODES:
 rs=[r for r in all_runs if r['mode']==mode]
 stats[mode]={}
 for k in ['psnr_all_mean','psnr_static_mean','ghost_residual_mean','ssim_mean']:
  a=np.array([r['agg'][k] for r in rs]);stats[mode][k]={'mean':float(a.mean()),'std':float(a.std(ddof=1))}
 for k in ['clean_background_psnr_mean','train_wall_s','render_ms','peak_allocated_bytes']:
  a=np.array([r[k] for r in rs]);stats[mode][k]={'mean':float(a.mean()),'std':float(a.std(ddof=1))}
(OUT/'summary.json').write_text(json.dumps({'manifest':manifest,'stats':stats,'runs':all_runs},indent=2))
print('COMPLETE '+str(OUT/'summary.json'),flush=True)
