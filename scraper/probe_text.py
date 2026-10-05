"""Open a page in a real browser and print how much readable text it has."""
import asyncio
import sys

from playwright.async_api import async_playwright


async def main(urls):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/129.0 Safari/537.36"
        )
        for url in urls:
            page = await ctx.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
                text = await page.inner_text("body")
                print(f"== {url}\n   title={await page.title()!r} chars={len(text)}")
                print("   " + text[:1500].replace("\n", " | "))
            except Exception as e:
                print(f"== {url} ERROR {e}")
            await page.close()
        await browser.close()


asyncio.run(main(sys.argv[1:]))
