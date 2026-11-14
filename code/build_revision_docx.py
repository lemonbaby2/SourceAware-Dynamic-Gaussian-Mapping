import json,sys,re
from pathlib import Path
HERE=Path(__file__).parent;ROOT=HERE.parent;REV=ROOT/'revision_20261114'
sys.path.insert(0,str(HERE))
import refs_render
refs_render.BIB=REV/'latex/references.bib';refs_render.AUX=REV/'latex/main.aux'
import build_extended_docx as B
B.TEX=REV/'latex/main.tex';B.AUX=REV/'latex/main.aux';B.FIG=REV/'figures'
B.OUT=REV/'SourceAware_正文增强_GPU实测_高清图_20261114.docx'
B.CITES,B.LABELS=B.bib_maps()
B.REFS=refs_render.build_refs_struct()
for label,spec in json.loads((REV/'tables_data.json').read_text(encoding='utf-8')).items():
 B.TABLES[label]=(spec['caption'],spec['header'],spec['rows'])

def academic_table(doc,label):
 caption,headers,rows=B.TABLES[label]
 number=B.LABELS.get(label,'')
 caption=re.sub(r'^TABLE [IVX]+\.\s*','',caption)
 B.add_caption(doc,'TABLE '+str(number)+'. '+caption)
 table=doc.add_table(rows=1,cols=len(headers))
 table.alignment=B.WD_TABLE_ALIGNMENT.CENTER
 for i,text in enumerate(headers):table.rows[0].cells[i].text=text
 for row in rows:
  cells=table.add_row().cells
  for i,text in enumerate(row):cells[i].text=str(text)
 for ri,row in enumerate(table.rows):
  for ci,cell in enumerate(row.cells):
   cell.vertical_alignment=B.WD_CELL_VERTICAL_ALIGNMENT.CENTER
   p=cell.paragraphs[0];p.paragraph_format.space_after=B.Pt(2);p.paragraph_format.space_before=B.Pt(2)
   p.alignment=B.WD_ALIGN_PARAGRAPH.LEFT if ci<2 else B.WD_ALIGN_PARAGRAPH.CENTER
   for run in p.runs:B.set_font(run,size=7 if len(headers)>3 else 7.7,bold=ri==0)
   pr=cell._tc.get_or_add_tcPr();borders=B.OxmlElement('w:tcBorders')
   for side in ['top','bottom','left','right']:
    edge=B.OxmlElement('w:'+side)
    visible=(ri==0 and side in ['top','bottom']) or (ri==len(table.rows)-1 and side=='bottom')
    edge.set(B.qn('w:val'),'single' if visible else 'nil');edge.set(B.qn('w:sz'),'5');edge.set(B.qn('w:color'),'000000');borders.append(edge)
   pr.append(borders)
 table.rows[0]._tr.get_or_add_trPr().append(B.OxmlElement('w:tblHeader'))
 doc.add_paragraph().paragraph_format.space_after=B.Pt(0)
B.add_table=academic_table
original_figure=B.add_figure
def numbered_figure(doc,label,filename=None,caption=None,wide=None):
 if caption is not None:caption='Fig. '+str(B.LABELS.get(label,'?'))+'. '+caption
 return original_figure(doc,label,filename,caption,wide)
B.add_figure=numbered_figure
B.build()
from docx import Document
d=Document(str(B.OUT))
d.styles['Normal'].paragraph_format.line_spacing=1.0
for para in d.paragraphs:
 if para.paragraph_format.line_spacing is not None and isinstance(para.paragraph_format.line_spacing,float):
  para.paragraph_format.line_spacing=1.0
for table in d.tables:
 for row in table.rows[:-1]:
  for cell in row.cells:
   for para in cell.paragraphs:para.paragraph_format.keep_with_next=True
for para in d.paragraphs:
 if para.text.startswith('TABLE '):para.paragraph_format.keep_with_next=True
d.save(str(B.OUT))
