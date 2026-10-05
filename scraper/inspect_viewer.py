"""Quick probe of the AnyFlip viewer: what loads, page count, DOM layout."""
import asyncio
import json
import sys

from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://online.anyflip.com/jbvnw/jtya/mobile/index.html"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        images = []
        page.on(
            "response",
            lambda r: images.append((r.status, r.url, r.headers.get("content-type", "")))
            if r.request.resource_type == "image"
            else None,
        )
        await page.goto(URL, wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(4000)

        title = await page.title()
        info = await page.evaluate(
            """() => {
                const g = {};
                for (const k of ['bookConfig','fliphtml5_pages','totalPageCount','pageCount']) {
                    try { if (window[k] !== undefined) g[k] = typeof window[k] === 'object' ? Object.keys(window[k]).slice(0,40) : window[k]; } catch(e) {}
                }
                try { g.pagesLen = window.fliphtml5_pages ? window.fliphtml5_pages.length : null; } catch(e) {}
                try { g.firstPage = window.fliphtml5_pages ? window.fliphtml5_pages[0] : null; } catch(e) {}
                try { g.totalPageCount = window.bookConfig ? window.bookConfig.totalPageCount : null; } catch(e) {}
                const imgs = [...document.querySelectorAll('img')].slice(0,20).map(i => [i.src.slice(0,160), i.naturalWidth, i.naturalHeight, i.className]);
                const canv = document.querySelectorAll('canvas').length;
                return {g, imgs, canv};
            }"""
        )
        print("TITLE:", title)
        print(json.dumps(info, indent=1, ensure_ascii=False)[:4000])
        print("IMAGE RESPONSES:")
        for s, u, ct in images[:40]:
            print(s, ct, u[:180])
        await page.screenshot(path="scraper/_probe.png")
        await browser.close()


asyncio.run(main())
