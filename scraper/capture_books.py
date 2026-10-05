"""Capture KAFA textbook page images from the AnyFlip viewer.

Opens each book in a headless browser, reads the page list the viewer itself
uses, and saves each large page image the viewer would display.

For private FYP research use only. Do not redistribute the captured pages.

Usage:
    python scraper/capture_books.py            # all books
    python scraper/capture_books.py fiqh       # one book
"""
import asyncio
import base64
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "raw"

BOOKS = {
    "fiqh": "https://online.anyflip.com/jbvnw/jtya/mobile/index.html",   # Ibadah
    "jawi": "https://online.anyflip.com/dnryu/zqgg/mobile/index.html",
    "tajwid": "https://online.anyflip.com/vydoi/xohr/mobile/index.html",
}

# Runs inside the viewer page: fetch one page image (same-origin) as base64.
FETCH_JS = """async (url) => {
    const r = await fetch(url, {credentials: 'include'});
    if (!r.ok) return {ok: false, status: r.status};
    const buf = await r.arrayBuffer();
    let bin = '';
    const bytes = new Uint8Array(buf);
    for (let i = 0; i < bytes.length; i += 0x8000) {
        bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    }
    return {ok: true, type: r.headers.get('content-type'), data: btoa(bin)};
}"""


async def capture_book(browser, name: str, url: str) -> None:
    book_dir = OUT_DIR / name / "pages"
    book_dir.mkdir(parents=True, exist_ok=True)

    page = await browser.new_page(viewport={"width": 1280, "height": 900})
    await page.goto(url, wait_until="networkidle", timeout=120000)
    await page.wait_for_function("() => Array.isArray(window.fliphtml5_pages)", timeout=60000)

    title = await page.title()
    pages = await page.evaluate("() => window.fliphtml5_pages.map(p => p.n[0])")
    base = url.rsplit("/mobile/", 1)[0] + "/files/large/"
    print(f"[{name}] {title} - {len(pages)} pages")

    manifest = {"book": name, "title": title, "source": url, "pages": []}
    failed = []
    consecutive_fail = 0
    for i, fname in enumerate(pages, start=1):
        # Some books list bare hashed names (served from files/large/),
        # others list paths relative to the viewer, e.g. ../files/mobile/1.webp
        img_url = urljoin(url, fname) if "/" in fname else base + fname
        ext = Path(fname).suffix or ".webp"
        out = book_dir / f"page_{i:03d}{ext}"
        manifest["pages"].append({"page": i, "file": out.name, "url": img_url})
        if out.exists() and out.stat().st_size > 0:
            continue  # resume support
        for attempt in range(3):
            res = await page.evaluate(FETCH_JS, img_url)
            if res.get("ok"):
                out.write_bytes(base64.b64decode(res["data"]))
                consecutive_fail = 0
                break
            await page.wait_for_timeout(1500 * (attempt + 1))
        else:
            failed.append(i)
            consecutive_fail += 1
            print(f"  page {i} failed (status {res.get('status')})")
            if consecutive_fail >= 5:
                print(f"  [{name}] 5 failures in a row, stopping this book")
                break
        await page.wait_for_timeout(300)  # be polite to the server
        if i % 10 == 0:
            print(f"  {i}/{len(pages)}")

    manifest["failed"] = failed
    (OUT_DIR / name / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[{name}] done, {len(pages) - len(failed)} saved, {len(failed)} failed")
    await page.close()


async def main() -> None:
    selected = sys.argv[1:] or list(BOOKS)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for name in selected:
            await capture_book(browser, name, BOOKS[name])
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
