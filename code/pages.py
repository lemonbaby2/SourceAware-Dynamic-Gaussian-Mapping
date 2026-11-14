# -*- coding: utf-8 -*-
"""Report the Word page count of a .docx.

Word is reached through COM on a temporary *copy*, so the delivered file is
never locked or modified.  If Word was already running, the existing instance
is reused and left open; only an instance created here is quit.
"""
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

WD_STAT_PAGES = 2


def page_count(docx_path: Path) -> int:
    import pythoncom
    import win32com.client as win32

    pythoncom.CoInitialize()
    created = False
    try:
        try:
            app = win32.GetActiveObject("Word.Application")
        except Exception:
            app = win32.DispatchEx("Word.Application")
            created = True
        # clean up any stale probe document left by an interrupted run
        try:
            for d in list(app.Documents):
                if d.Name.startswith("_pagecheck_"):
                    d.Close(SaveChanges=False)
        except Exception:
            pass
        tmp = Path(tempfile.gettempdir()) / (
            "_pagecheck_" + uuid.uuid4().hex[:8] + "_" + docx_path.name)
        shutil.copy2(docx_path, tmp)
        docs = app.Documents
        doc = docs.Open(FileName=str(tmp), ReadOnly=True, AddToRecentFiles=False)
        pages = doc.ComputeStatistics(WD_STAT_PAGES)
        words = doc.ComputeStatistics(0)
        doc.Close(SaveChanges=False)
        try:
            tmp.unlink()
        except OSError:
            pass
        return pages, words
    finally:
        if created:
            try:
                app.Quit(False)
            except Exception:
                pass
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    p = Path(sys.argv[1])
    pages, words = page_count(p)
    print(f"{p.name}: {pages} pages, {words} words")
