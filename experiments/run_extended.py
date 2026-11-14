# -*- coding: utf-8 -*-
"""扩展实验：主实验补种子 + 超参/掩码消融。

复用 renderer_original.py（其 sha256 已写入原 manifest，本脚本不修改它），
仅新增参数化 train_ext 以支持：
  - 高斯点数 / 迭代数 消融
  - 掩码噪声（模拟掩码预测误差）
  - 软掩码 vs 硬掩码
  - 掩码膨胀/腐蚀

全部在本机 GPU 实跑；输出含 metrics/history/三联渲染图/PLY。
"""
import os, sys, json, time, math, hashlib, traceback
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
sys.path.insert(0, str(HERE))

import renderer_original as R
from protocol import split_ids, select_frames

DATA = Path(r"E:\研究生学习\dy3dgs-thesis-repro\synthetic\code\data_dyn")
OUT = HERE / "extended2"
OUT.mkdir(exist_ok=True)

gpu = next(i for i in range(torch.cuda.device_count()) if "5060 Ti" in torch.cuda.get_device_name(i))
torch.cuda.set_device(gpu)
R.DEV = f"cuda:{gpu}"
R.DATA = str(DATA)


def make_mask(f, mask_mode="hard", mask_noise=0.0, mask_dilate=0, rng=None):
    """返回 (1,1,H,W) 的训练权重掩码：1=参与损失，0=被剔除。"""
    dyn = f["dyn"]
    if mask_mode == "soft":
        m = (1.0 - dyn).clamp(0, 1)
    else:
        m = (dyn < 0.5).float()
    if mask_dilate:
        k = abs(mask_dilate) * 2 + 1
        x = m[None, None]
        if mask_dilate > 0:
            m = F.max_pool2d(x, k, 1, mask_dilate)[0, 0]
        else:
            m = -F.max_pool2d(-x, k, 1, -mask_dilate)[0, 0]
    if mask_noise > 0 and rng is not None:
        flip = torch.from_numpy((rng.random(tuple(m.shape)) < mask_noise)).to(m.device)
        m = torch.where(flip, 1.0 - m, m)
    return m.unsqueeze(0).unsqueeze(0)


def train_ext(mode, frames, K, meta, iters=1200, max_points=2500, seed=0, log_every=300,
              mask_mode="hard", mask_noise=0.0, mask_dilate=0):
    H, W = meta["H"], meta["W"]
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)

    exclude_dyn_init = mode != "naive"
    if mode == "no-dyn-data":
        use_frames = [i for i, f in enumerate(frames) if f["dyn"].mean() < 0.005]
    else:
        use_frames = list(range(len(frames)))
    if len(use_frames) < 4:
        use_frames = list(range(len(frames)))

    pts, cols = R.backproject([frames[i] for i in use_frames], K, max_points,
                              exclude_dynamic=exclude_dyn_init, rng=rng)
    model = R.Gaussians(pts, cols, scale_init=0.05).to(R.DEV)
    opt = torch.optim.Adam(model.params_lr(), eps=1e-15)

    lr_init, lr_final = 1.6e-4, 1.6e-6
    hist, t0 = [], time.time()
    for it in range(1, iters + 1):
        frac = min(it / max(iters, 1), 1.0)
        opt.param_groups[0]["lr"] = lr_init * ((lr_final / lr_init) ** frac)
        fi = int(rng.integers(0, len(use_frames)))
        f = frames[use_frames[fi]]
        img, _ = R.rasterize(model, f["R"], f["t"], K, H, W)
        gt = f["rgb"].permute(2, 0, 1).unsqueeze(0)

        if mode == "dyn-mask":
            m = make_mask(f, mask_mode, mask_noise, mask_dilate, rng)
            loss = (torch.abs(img - gt) * m).sum() / (m.sum() * 3 + 1e-6)
        else:
            loss = torch.abs(img - gt).mean()

        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_([p for g in opt.param_groups for p in g["params"]], 1.0)
        opt.step()
        with torch.no_grad():
            model.log_scales.data.clamp_(math.log(0.005), math.log(1.2))
            model.logit_opac.data.clamp_(-6.0, 6.0)

        if it % log_every == 0 or it == 1:
            with torch.no_grad():
                img_v, _ = R.rasterize(model, f["R"], f["t"], K, H, W)
            hist.append({"iter": it, "loss": float(loss.item()),
                         "psnr": R.psnr(img_v.clamp(0, 1), gt.clamp(0, 1)),
                         "n_gauss": int(model.means.shape[0])})
            print(f"  [{mode}|{mask_mode}|n={mask_noise}|d={mask_dilate}|s={seed}] "
                  f"it {it:5d}/{iters} loss {loss.item():.4f} psnr {hist[-1]['psnr']:6.2f} "
                  f"{time.time()-t0:6.1f}s", flush=True)

    return model, hist, use_frames, time.time() - t0


def main():
    meta, K, frames = R.load_scene()
    train_ids, test_ids = split_ids(len(frames))
    train_frames = select_frames(frames, train_ids)
    test_frames = select_frames(frames, test_ids)
    print(f"scene {meta['W']}x{meta['H']} frames={len(frames)} train={train_ids} test={test_ids}", flush=True)
    print(f"GPU {torch.cuda.get_device_name(gpu)} torch {torch.__version__}", flush=True)

    jobs = []
    # 1) 主实验补种子 3,4（seed0-2 已由 run_holdout.py 完成）
    for seed in (3, 4):
        for mode in ("naive", "no-dyn-data", "dyn-mask"):
            jobs.append(dict(tag=f"main_s{seed}_{mode}", seed=seed, mode=mode))
    # 2) 高斯点数消融
    for seed in (0, 1):
        for pts in (1000, 5000):
            jobs.append(dict(tag=f"pts{pts}_s{seed}", seed=seed, mode="dyn-mask", points=pts))
    # 3) 迭代数消融
    for seed in (0, 1):
        for it in (600, 2400):
            jobs.append(dict(tag=f"iter{it}_s{seed}", seed=seed, mode="dyn-mask", iters=it))
    # 4) 掩码噪声敏感度
    for seed in (0, 1):
        for nz in (0.05, 0.10, 0.20):
            jobs.append(dict(tag=f"noise{int(round(nz*100))}_s{seed}", seed=seed,
                             mode="dyn-mask", mask_noise=nz))
    # 5) 软掩码
    for seed in (0, 1):
        jobs.append(dict(tag=f"soft_s{seed}", seed=seed, mode="dyn-mask", mask_mode="soft"))
    # 6) 掩码膨胀/腐蚀
    for dl in (2, -2):
        jobs.append(dict(tag=f"dilate{dl}_s0", seed=0, mode="dyn-mask", mask_dilate=dl))

    print(f"JOBS {len(jobs)}", flush=True)
    results = []
    for job in jobs:
        run = OUT / job["tag"]
        run.mkdir(exist_ok=True)
        mf = run / "metrics.json"
        if mf.exists():
            results.append(json.loads(mf.read_text(encoding="utf-8")))
            print(f"SKIP {job['tag']}", flush=True)
            continue
        iters = job.get("iters", 1200)
        points = job.get("points", 2500)
        try:
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            model, hist, used, tt = train_ext(
                job["mode"], train_frames, K, meta,
                iters=iters, max_points=points, seed=job["seed"],
                mask_mode=job.get("mask_mode", "hard"),
                mask_noise=job.get("mask_noise", 0.0),
                mask_dilate=job.get("mask_dilate", 0))
            torch.cuda.synchronize()
            train_s = time.perf_counter() - t0
            assert all(train_ids[i] not in test_ids for i in used)

            rows, agg = R.evaluate(model, test_frames, K, meta)
            for row, i in zip(rows, test_ids):
                row["frame"] = i

            clean_psnr = []
            for j, f in enumerate(test_frames):
                with torch.no_grad():
                    image, _ = R.rasterize(model, f["R"], f["t"], K, meta["H"], meta["W"])
                rgb = image[0].permute(1, 2, 0).clamp(0, 1).cpu().numpy()
                clean = f["clean"].cpu().numpy()
                clean_psnr.append(R.psnr(rgb, clean))
                rows[j]["clean_background_psnr"] = clean_psnr[-1]
                panels = [f["rgb"].cpu().numpy(), rgb, clean,
                          np.abs(rgb - clean).mean(2, keepdims=True).repeat(3, 2)]
                Image.fromarray((np.concatenate(panels, axis=1) * 255).clip(0, 255).astype("uint8")).save(
                    run / f"view_{test_ids[j]:03d}.png")

            f = test_frames[0]
            with torch.no_grad():
                for _ in range(5):
                    R.rasterize(model, f["R"], f["t"], K, meta["H"], meta["W"])
                torch.cuda.synchronize()
                t1 = time.perf_counter()
                for _ in range(20):
                    R.rasterize(model, f["R"], f["t"], K, meta["H"], meta["W"])
                torch.cuda.synchronize()
                render_s = (time.perf_counter() - t1) / 20

            result = {"tag": job["tag"], **{k: v for k, v in job.items() if k != "tag"},
                      "iters": iters, "points": points, "test_ids": test_ids,
                      "train_ids": train_ids, "agg": agg, "per_frame": rows,
                      "clean_background_psnr_mean": float(np.mean(clean_psnr)),
                      "train_wall_s": train_s, "render_ms": render_s * 1000,
                      "peak_allocated_bytes": torch.cuda.max_memory_allocated()}
            torch.save(model.state_dict(), run / "model.pt")
            R.save_ply(model, str(run / "gaussians.ply"))
            (run / "history.json").write_text(json.dumps(hist, indent=2), encoding="utf-8")
            mf.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            results.append(result)
            print(f"DONE {job['tag']} psnr_static={agg['psnr_static_mean']:.3f} "
                  f"ghost={agg['ghost_residual_mean']:.4f} {train_s:.1f}s", flush=True)
            del model
            torch.cuda.empty_cache()
        except Exception as e:
            print(f"FAIL {job['tag']}: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
            torch.cuda.empty_cache()

    (OUT / "summary_ext.json").write_text(
        json.dumps({"gpu": torch.cuda.get_device_name(gpu), "torch": torch.__version__,
                    "data": str(DATA), "runs": results}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    print(f"COMPLETE {OUT/'summary_ext.json'}  runs={len(results)}", flush=True)


if __name__ == "__main__":
    main()
