# -*- coding: utf-8 -*-
"""Export a .docx to PDF through Word and report the page count.

Works on a temporary copy so the delivered file is never touched.
Useful for eyeballing the final layout before handing the document over.
"""
import shutil
import sys
import tempfile
import uuid
from pathlib import Path


def export(docx_path: Path, pdf_path: Path | None = None) -> Path:
    import pythoncom
    import win32com.client as win32

    pdf_path = pdf_path or docx_path.with_suffix(".qa.pdf")
    pythoncom.CoInitialize()
    created = False
    try:
        try:
            app = win32.GetActiveObject("Word.Application")
        except Exception:
            app = win32.DispatchEx("Word.Application")
            created = True
        try:
            for d in list(app.Documents):
                if d.Name.startswith("_pdfprobe_"):
                    d.Close(SaveChanges=False)
        except Exception:
            pass
        tmp = Path(tempfile.gettempdir()) / (
            "_pdfprobe_" + uuid.uuid4().hex[:8] + "_" + docx_path.name)
        shutil.copy2(docx_path, tmp)
        docs = app.Documents
        doc = docs.Open(FileName=str(tmp), ReadOnly=True, AddToRecentFiles=False)
        pages = doc.ComputeStatistics(2)
        doc.ExportAsFixedFormat(OutputFileName=str(pdf_path),
                                ExportFormat=17, OpenAfterExport=False)
        doc.Close(SaveChanges=False)
        try:
            tmp.unlink()
        except OSError:
            pass
        print(f"{docx_path.name}: {pages} pages -> {pdf_path}")
        return pdf_path
    finally:
        if created:
            try:
                app.Quit(False)
            except Exception:
                pass
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    export(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else None)
