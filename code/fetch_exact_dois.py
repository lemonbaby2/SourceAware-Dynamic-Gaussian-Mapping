import json,time,urllib.request,urllib.parse
from pathlib import Path
OUT=Path(__file__).parent/'journal_metadata'
for key,doi in [('proper2007journal','10.1198/016214506000001437'),('forecast2007journal','10.1111/j.1467-9868.2007.00587.x'),('robust1964journal','10.1214/aoms/1177703732'),('ransac1981journal','10.1145/358669.358692')]:
 p=OUT/(key+'.json')
 if p.exists():continue
 time.sleep(3)
 try:
  req=urllib.request.Request('https://api.crossref.org/works/'+urllib.parse.quote(doi,safe=''),headers={'User-Agent':'ManuscriptAudit/1.0'})
  c=json.load(urllib.request.urlopen(req,timeout=40))['message']
  p.write_text(json.dumps({'key':key,'query':doi,'candidates':[c]},ensure_ascii=False,indent=2),encoding='utf-8')
  print(key,c.get('title'),c.get('container-title'),flush=True)
 except Exception as e:print(key,str(e),flush=True)
