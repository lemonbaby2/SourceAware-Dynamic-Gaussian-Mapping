from pathlib import Path
import re,json,sys,zipfile
from PIL import Image,ImageOps,ImageDraw
ROOT=Path(__file__).resolve().parent
REV=ROOT.parent/'revision_20261114'
sys.path.insert(0,str(ROOT))
from refs_render import parse_bib
p=REV/'latex/main.tex'
t=p.read_text(encoding='utf-8').replace('invariant to exact replication within a family','invariant to uniform replication of all channels within a family').replace('exact invariance under replication inside a family','exact invariance under uniform replication of all channels inside a family')
p.write_text(t,encoding='utf-8')
t=t.replace('Ghost residual falls from $0.0383','In the matched three-seed subset, ghost residual falls from $0.0383')
t=t.replace('The trend bounds the claim: masked loss helps in proportion to mask quality, and this experiment cannot substitute for measuring a real predictor whose errors are spatially correlated.','The response is non-monotone and small; this experiment cannot substitute for measuring a real predictor whose errors are spatially correlated.')
t=t.replace('Degradation with noise bounds how much of the controlled gain can be expected from an imperfect real predictor.','Noise is resampled per optimization step; these results do not establish performance with a real mask predictor.')
t=t.replace('A false-negative trial changes 20\\% of dynamic pixels to static, independently per training frame. A false-positive trial changes 20\\% of static pixels to dynamic.','A false-negative trial independently changes each dynamic pixel to static with probability 0.2. A false-positive trial independently changes each static pixel to dynamic with probability 0.2. Realized class-conditional rates range from 19.07\\% to 20.06\\% across the six runs.')
p.write_text(t,encoding='utf-8')
b=parse_bib((REV/'latex/references.bib').read_text(encoding='utf-8'))
c=set(k.strip() for x in re.findall(r'\\cite\w*\{([^}]+)\}',t) for k in x.split(','))
j={k:v['journal'] for k,v in b.items() if v['journal'] and not any(s in v['journal'].lower() for s in ['arxiv','neural information processing','lecture notes','proceedings'])}
report={'references':len(b),'cited':len(c),'missing_keys':sorted(c-set(b)),'uncited_keys':sorted(set(b)-c),'journal_count':len(j),'journals':j,'figures':len(re.findall(r'\\includegraphics',t)),'new_gpu_runs':9,'word_pages':20,'latex_pages':19}
(REV/'verification_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='journals'},ensure_ascii=False))
for folder,pattern in [('qa_word','page-*.png'),('latex','qa-*.png')]:
 files=sorted((REV/folder).glob(pattern))
 for start in range(0,len(files),4):
  canvas=Image.new('RGB',(1000,1400),'#999999')
  for i,f in enumerate(files[start:start+4]):
   im=Image.open(f).convert('RGB');im.thumbnail((490,675))
   x=(i%2)*500;y=(i//2)*700
   canvas.paste(im,(x,y+22));ImageDraw.Draw(canvas).text((x+8,y+3),f'{folder} {start+i+1}',fill='black')
  canvas.save(REV/f'{folder}_contact_{start//4+1}.jpg')
