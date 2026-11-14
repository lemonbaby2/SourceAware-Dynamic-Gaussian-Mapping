import numpy as np

def split_ids(n):
    test=list(range(2,n,3))
    return [i for i in range(n) if i not in test], test

def select_frames(frames, ids):
    return [frames[i] for i in ids]

def family_log_pool(probabilities, families):
    p=np.asarray(probabilities,dtype=float)
    f=np.asarray(families)
    if p.ndim!=2 or p.shape[1]!=len(f) or not np.isfinite(p).all() or (p<0).any() or (p>1).any():
        raise ValueError('finite probabilities in [0,1] and one family per column required')
    p=np.clip(p,1e-8,1-1e-8)
    logits=np.log(p)-np.log1p(-p)
    grouped=np.stack([logits[:,f==g].mean(1) for g in np.unique(f)],axis=1)
    z=grouped.mean(1)
    return 1/(1+np.exp(-z))
