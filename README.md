# Source-Aware Evidence Pooling for Dynamic Gaussian Mapping

面向动态场景三维高斯建图的**源感知证据池**（source-aware evidence pooling）机制研究，附完整可复现资产。

本仓库回答两个**互相独立**的问题：

| 部分 | 问题 | 数据 |
|---|---|---|
| 证据融合 | 当光流、几何、聚类等线索**派生自同一批测量**时，把它当条件独立会重复计数。族内平均再跨族合并，能否做到对"复制"精确不变？ | 潜变量压力测试，10 种子 × 10k 标定样本 × 50k 独立测试样本 |
| 动态抑制 | 动态像素抑制里，**静态初始化**和**掩码加权损失**各自贡献多少？能否互相替代？ | 已知位姿/深度/掩码的合成高斯建图场景，5 个独立 GPU run × 4 个留出视角 |

两部分的数字**不可横向比较**，各自回答不同层级的问题。

---

## 一、先说清楚这不是什么

避免误用，以下四条请先读：

1. **不是端到端 SLAM 系统。** 建图实验使用 **oracle 位姿、oracle 深度、oracle 掩膜**，属于机制级证据，不构成 SLAM 精度证据。
2. **不含 RTK / GNSS / 导航 / 轨迹输出。** 本仓库不估计轨迹、不做定位、不做路径规划。若你要做激光 SLAM 导航多传感器融合，请另建项目（LiDAR-惯性里程计 + GNSS 因子图 + 代价地图规划），不要把本项目当作其基础。
3. **不宣称 SOTA。** 没有与 Dy3DGS-SLAM 等动态 SLAM 系统做匹配协议的比较，正文明确表述为"互补而非替代"。
4. **未完成真实序列验证。** 真实掩膜预测器、单目尺度恢复、ATE/RPE、回环、端到端吞吐均未实现。正文第 II 节与讨论已逐条写明缺失项。

> 与本账号另一个仓库 [`dy3dgs-thesis-repro`](https://github.com/lemonbaby2/dy3dgs-thesis-repro) 的区别：那个是**学位论文**《动态环境下视觉语言模型辅助三维高斯语义建图与机器人目标导航》的复现资产，含公开数据集（NeRF Synthetic / D-NeRF / Tanks & Temples）的官方 3DGS、4DGS 复现；**本仓库是另一篇论文**，聚焦统计层面的证据重复计数与动态抑制的因子分解，两边的数字不可混用。

---

## 二、核心结果

### 证据复制压力测试（10 种子）

把同一条运动证据复制 8 次，三种融合方式的表现：

| 融合方式 | NLL（1 份 → 8 份） | ECE₁₀（1 份 → 8 份） | 判读 |
|---|---|---|---|
| 固定通道乘积 | 0.479±0.002 → **1.045±0.021** | 0.0148±0.0019 → **0.1787±0.0020** | 凭空产生过度自信 |
| 通道平均 | 0.479 → 0.493±0.002 | 0.0148 → 0.0232±0.0031 | 部分缓解 |
| **源家族池** | **0.479 → 0.479（不变）** | **0.0148 → 0.0148（不变）** | 对族内复制精确不变 |

结论：复制**不带来新信息**，只有家族池在数学上保持了这一点。这个性质由 Proposition 1 给出，压力测试是对它的实证检验。

### 动态抑制因子分解（5 个 GPU run × 4 留出视角）

| 配置 | 静态区 PSNR (dB) | 动态残影 L1 | SSIM |
|---|---|---|---|
| 全部像素训练（naive） | 27.67 ± 0.52 | 0.0433 ± 0.0089 | 0.8878 ± 0.0024 |
| 仅静态初始化 | 29.46 ± 0.44 | 0.0242 ± 0.0086 | 0.8984 ± 0.0015 |
| **静态初始化 + 掩码加权损失** | **31.70 ± 0.23** | **0.0057 ± 0.0002** | **0.9069 ± 0.0005** |

相对全像素训练：**+4.03 ± 0.73 dB**，残影降至 **1/7.5**，5 个种子方向一致。

配套消融：容量（1k→5k 基元）、预算（600→2400 迭代）、掩膜标签噪声（5/10/20%）、掩膜形态（soft/膨胀/腐蚀），以及匹配三种子实验单独隔离"仅损失掩码""固定假阴性 20%""固定假阳性 20%"。详见 `paper/additional_results.json`。

> 注意：掩膜标签噪声在本场景退化很浅（<0.15 dB），我们不把它解释为"方法鲁棒"，正文措辞为"对逐像素散点噪声不敏感，但这不等于对真实预测器鲁棒——真实掩膜的错误是成片而非散点"。

---

## 三、目录

```
├── paper/
│   ├── latex/              定稿 LaTeX 源（IEEEtran）+ 84 条已核验参考文献 + 编译好的 PDF
│   ├── figures/            论文用图（16 张，300 dpi）
│   ├── manuscript.pdf      定稿 PDF（19 页，IEEE 双栏）
│   ├── additional_results.json      新增 9 次 GPU 实验的统计
│   └── added_reference_audit.json   34 篇新增期刊文献的 DOI 元数据核验记录
├── code/                   数据 → 表格 → 图 → 文档的生成脚本
├── experiments/            全部实验产物（metrics / history / renders / 逐视角图）
├── figures/                结果图
└── README.md
```

`code/` 里几个关键脚本：

| 脚本 | 作用 |
|---|---|
| `table_rows.py` | 所有结果表的唯一数据源，同时供 LaTeX 与 Word，避免正文与表格漂移 |
| `make_bib.py` | 从核验记录生成 `references.bib`，逐条走 Crossref / arXiv 回查 |
| `refs_render.py` | 参考文献渲染，返回"文本 + 链接"分段结构（DOI / arXiv 自动识别） |
| `verify_final.py` | 25 项验收：文献数、引用覆盖、图数、锚点数、悬空锚点、转义残留、页数、摘要数值一致性 |
| `plot_new_runs.py` | 从 `experiments/expanded_results/` 出新增实验的图 |

---

## 四、复现

### 编译论文

```bash
cd paper/latex
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

依赖标准 TeX Live（IEEEtran、amsmath、graphicx、booktabs 等）。`main.bbl` 已随仓库提供，也可直接上传 arXiv（arXiv 不跑 bibtex，必须带 `.bbl` 而非 `.bib`）。

### 复现表格与图

```bash
cd code
python table_rows.py        # experiments/ → tables_data.json + LaTeX 表格片段
python plot_new_runs.py     # experiments/expanded_results/ → 新增实验图
python verify_final.py      # 验收（需要先按上面的结构生成产物）
```

数据全部来自 `experiments/`，`metrics.json` 是唯一数值来源，正文数字与表格由脚本注入，不手抄。

> 环境说明：出图脚本需要 matplotlib（作者的 conda 环境为 `D:/Anaconda/python.exe`）；`build_extended_docx.py` 依赖 Windows 上的 `MML2OMML.XSL`（Office 自带）把 LaTeX 公式转成 Word 公式，非 Windows 环境请直接用 `paper/latex` 出 PDF。

---

## 五、硬件与真实性边界

- 建图实验与新增消融：单卡 **RTX 5060 Ti 16 GB**，约 107 s/run（2500 iter，5000 基元），峰值显存约 25 MB 量级之外的主机内存占用不在统计范围。
- 每个 run 保留 `metrics.json`、`history.json`、`model.pt`、逐视角渲染图，可逐帧核对。
- 图做过统一排版（Times 8 pt、300 dpi、固定色板、误差棒、局部放大），**放大一律最近邻，不引入新像素**；原始渲染全部留档。
- 参考文献 84 篇全部被正文引用；其中 45 篇为期刊论文，其余为会议、预印本或专著，**不混称"顶刊"**。期刊层次应按各校认可目录判断。

---

## 六、许可与引用

- 代码（`code/`）：MIT，见 `LICENSE`
- 论文源、数据、图表、指标：CC BY 4.0
- 引用格式见 `CITATION.cff`

## 七、状态

尚未向任何期刊或会议投稿。若你看到本仓库被某处声称"已发表"，那不是我们说的。
