import os,json,sys
from pathlib import Path
os.environ['MPLBACKEND']='Agg'
HERE=Path(__file__).parent;ROOT=HERE.parent;REV=ROOT/'revision_20261114'
os.environ['MPLCONFIGDIR']=str(ROOT/'.mpl')
import numpy as np
import matplotlib.pyplot as plt
sys.path.insert(0,str(ROOT/'experiments'))
import torch
import renderer_original as R
OUT=REV/'figures';OUT.mkdir(exist_ok=True)
new=ROOT/'experiments/expanded_results';old=ROOT/'experiments/heldout_results'
configs=['naive','no-dyn-data','loss_only','dyn-mask','false_negative_20','false_positive_20']
labels=['All pixels','Init. only','Loss only','Init. + loss','20% FN','20% FP']
data={}
for c in configs:
 paths=[(old/f'seed{s}_{c}' if c in ['naive','no-dyn-data','dyn-mask'] else new/f'seed{s}_{c}')/'metrics.json' for s in range(3)]
 assert all(p.exists() for p in paths),(c,'incomplete runs')
 data[c]=[json.loads(p.read_text()) for p in paths]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':300})
summary={}
for c,rs in data.items():
 summary[c]={}
 for k in ['psnr_static_mean','ghost_residual_mean','ssim_mean']:
  a=np.array([r['agg'][k] for r in rs]);summary[c][k]={'mean':float(a.mean()),'sd':float(a.std(ddof=1)),'values':a.tolist()}
(REV/'additional_results.json').write_text(json.dumps(summary,indent=2))
fig,axs=plt.subplots(1,2,figsize=(10,3.5),layout='constrained')
for ax,k,title in zip(axs,['psnr_static_mean','ghost_residual_mean'],['Static-region PSNR (dB)','Dynamic ghost residual (L1)']):
 for i,c in enumerate(configs):
  v=summary[c][k];ax.bar(i,v['mean'],color=['#8b8b8b','#d59a40','#6399ad','#245faa','#b75645','#62936a'][i],alpha=.85)
  ax.errorbar(i,v['mean'],yerr=v['sd'],fmt='none',ecolor='black',capsize=3)
  ax.scatter(np.full(3,i)+np.array([-.1,0,.1]),v['values'],s=10,color='black')
 ax.set_xticks(range(6),labels,rotation=25,ha='right');ax.set_ylabel(title);ax.grid(axis='y',alpha=.18)
axs[0].set_ylim(24,34)
fig.savefig(OUT/'matched_interventions.png');plt.close(fig)

# Rerender the three old baseline checkpoints on the local GPU. The raw float
# arrays are saved independently of publication formatting.
gpu=next(i for i in range(torch.cuda.device_count()) if '5060 Ti' in torch.cuda.get_device_name(i))
torch.cuda.set_device(gpu);R.DEV=f'cuda:{gpu}';R.DATA=r'E:\研究生学习\dy3dgs-thesis-repro\synthetic\code\data_dyn'
meta,K,frames=R.load_scene();ids=[2,5,8,11];renders={}
for c in ['naive','no-dyn-data','dyn-mask']:
 state=torch.load(old/f'seed0_{c}/model.pt',map_location=R.DEV,weights_only=True)
 model=R.Gaussians(state['means'],torch.sigmoid(state['color_logit'])).to(R.DEV);model.load_state_dict(state)
 ims=[]
 with torch.no_grad():
  for i in ids:
   f=frames[i];im,_=R.rasterize(model,f['R'],f['t'],K,meta['H'],meta['W']);ims.append(im[0].permute(1,2,0).clamp(0,1).cpu().numpy())
 renders[c]=np.stack(ims);del model
for c in ['loss_only','false_negative_20','false_positive_20']:renders[c]=np.load(new/f'seed0_{c}/renders.npz')['rgb']
np.savez_compressed(REV/'raw_comparison_renders.npz',**renders,view_ids=ids)
show=['naive','loss_only','dyn-mask','false_negative_20','false_positive_20']
fig,axs=plt.subplots(4,7,figsize=(13,5.8),layout='constrained')
for row,i in enumerate(ids):
 images=[frames[i]['rgb'].cpu().numpy()]+[renders[c][row] for c in show]+[frames[i]['clean'].cpu().numpy()]
 for col,im in enumerate(images):
  axs[row,col].imshow(im,interpolation='nearest');axs[row,col].set_xticks([]);axs[row,col].set_yticks([])
  if row==0:axs[row,col].set_title(['Input','All pixels','Loss only','Init. + loss','20% FN','20% FP','Static target'][col],fontsize=8)
 axs[row,0].set_ylabel('View '+str(i))
fig.savefig(OUT/'new_gpu_renders.png');plt.close(fig)
fig,axs=plt.subplots(4,5,figsize=(10,6),layout='constrained')
for row,i in enumerate(ids):
 clean=frames[i]['clean'].cpu().numpy()
 for col,c in enumerate(show):
  err=np.abs(renders[c][row]-clean).mean(axis=2)
  im=axs[row,col].imshow(err,vmin=0,vmax=.15,cmap='magma',interpolation='nearest')
  axs[row,col].set_xticks([]);axs[row,col].set_yticks([])
  if row==0:axs[row,col].set_title(['All pixels','Loss only','Init. + loss','20% FN','20% FP'][col])
 axs[row,0].set_ylabel('View '+str(i))
fig.colorbar(im,ax=axs,shrink=.7,label='Mean absolute RGB error (clipped at 0.15)')
fig.savefig(OUT/'new_error_maps.png');plt.close(fig)
print(json.dumps(summary,indent=2))
