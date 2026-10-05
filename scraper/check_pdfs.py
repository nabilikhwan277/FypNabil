"""Check whether each textbook PDF has a real text layer or is image-only,
and report the resolution of the embedded page images."""
from pathlib import Path

import pymupdf as fitz

PDF_DIR = Path(__file__).resolve().parent.parent / "text book"

for pdf in sorted(PDF_DIR.glob("*.pdf")):
    doc = fitz.open(pdf)
    text_pages, total_chars = 0, 0
    for page in doc:
        t = page.get_text().strip()
        if t:
            text_pages += 1
            total_chars += len(t)
    p = doc[10]
    imgs = p.get_images(full=True)
    dims = [(im[2], im[3]) for im in imgs]  # width, height of embedded images
    print(f"== {pdf.name}")
    print(f"   pages={len(doc)} text_pages={text_pages} chars={total_chars}")
    print(f"   page 11 size(pt)={tuple(round(x) for x in p.rect[2:])} embedded images={dims}")
