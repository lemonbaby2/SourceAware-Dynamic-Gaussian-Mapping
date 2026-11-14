from pathlib import Path
import json,re,shutil,zipfile
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent.parent/'revision_20261114'
for start in range(0,20,4):
 canvas=Image.new('RGB',(1000,1400),'#999999')
 files=sorted((R/'qa_word_final').glob('page-*.png'))
 for i,f in enumerate(files[start:start+4]):
  im=Image.open(f).convert('RGB');im.thumbnail((490,675));x=i%2*500;y=i//2*700
  canvas.paste(im,(x,y+22));ImageDraw.Draw(canvas).text((x+8,y+3),str(start+i+1),fill='black')
 canvas.save(R/f'final_contact_{start//4+1}.jpg')
shutil.copy2(R/'latex/main.pdf',R/'SourceAware_正文增强_GPU实测_20261114.pdf')
notes='''# 2026-11-14 修订交付

Word 20 页；LaTeX PDF 19 页，均含参考文献。扩充 Introduction，明确 4 项贡献；正文 16 张图，附录仅一节简短复现说明。

84 篇参考文献全部被正文引用，其中 45 篇为期刊论文，包括 TRO、TPAMI、IJRR、IJCV、TOG 等；其余为会议、预印本或专著，不混称“顶刊”。新增 34 篇期刊记录的 DOI 元数据见 added_reference_audit.json；期刊层次应按学校认可目录判断。

本轮新增 9 次 RTX 5060 Ti GPU 实验：仅损失掩码、固定假阴性、固定假阳性各 3 个种子。保留 metrics.json、history.json、model.pt、renders.npz。新图使用全部四个留出视角；误差图统一色标，显示裁剪不影响计算指标。没有修掉残影、合成实验结果或篡改数值。

数据路径：../experiments/expanded_results/。绘图脚本：../extended/plot_new_runs.py；实验脚本：../experiments/run_expanded.py。新增结果统计见 additional_results.json。旧版“软掩码”与硬掩码在二值输入下相同，已取消独立消融解释；修正形态学方向、非单调噪声响应和只有联合配置接受预算扫描的表述。

真实性边界：当前是已知位姿、深度与真值掩码下的合成场景机制研究，不是完成了真实序列端到端 SLAM 的投稿定稿。源证据池与映射实验分别验证两个机制，尚未组成并验证完整新系统。不能声称已超过 Dy3DGS-SLAM，不能报告不存在的 ATE/RPE。真实数据、估计掩码、跟踪与闭环以及匹配协议的基线比较仍待实现与验证。

当前 IEEE 双栏长稿满足用户 16–20 页阅读稿要求，不代表自动满足 ICCV、NeurIPS、ICLR、AAAI 或 IJCAI 的当届正文页数和模板要求；提交前须按选定会议年度规则压缩和换模板。尚未向任何会议或期刊投稿。

当前稿按双盲评审保留“Anonymous Authors”。正式投稿时应根据目标会议的匿名规则保留或替换作者、单位、邮箱、基金与代码链接；这些身份信息不能凭空补写。

LaTeX 编译：在 latex 目录执行 pdflatex main.tex、bibtex main、pdflatex main.tex、pdflatex main.tex。依赖标准 IEEEtran、amsmath、graphicx 等 TeX Live 包。

原稿及既有批注审核文件未覆盖，位于上级目录。请以本目录为本轮修订结果，避免混用旧版页数或统计说明。
'''
(R/'交付说明.md').write_text(notes,encoding='utf-8')
with zipfile.ZipFile(R/'LaTeX_SourceAware_20261114.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in ['latex/main.tex','latex/references.bib','latex/main.bbl','交付说明.md','verification_report.json','additional_results.json','added_reference_audit.json']:
  z.write(R/name,name)
 t=(R/'latex/main.tex').read_text(encoding='utf-8')
 for n in set(re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',t)):
  f=(R/'latex'/n).resolve()
  if not f.exists():f=(R/'figures'/Path(n).name).resolve()
  if not f.exists():raise FileNotFoundError(n)
  z.write(f,'figures/'+f.name)
print('PACKAGED')
