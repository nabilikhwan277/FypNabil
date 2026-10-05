"""Screenshot the running frontend in Rumi and Jawi mode (dev check).
Requires `npm run dev` (5173) and the backend (8000) to be running.
Usage: .venv\\Scripts\\python scripts\\screenshot_ui.py
"""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

OUT = Path(__file__).resolve().parent.parent / "eval" / "results"


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1100, "height": 700})
        errors: list[str] = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        await page.goto("http://localhost:5173/", wait_until="networkidle")
        await page.wait_for_selector("[role=status]", timeout=10000)
        await page.screenshot(path=OUT / "ui_home_rumi.png")
        await page.get_by_role("button", name="جاوي").click()
        await page.wait_for_timeout(800)
        await page.screenshot(path=OUT / "ui_home_jawi.png")
        status = await page.inner_text("[role=status]")
        direction = await page.evaluate("document.documentElement.dir")
        print("status pill:", status.strip())
        print("html dir after toggle:", direction)
        print("console errors:", errors or "none")
        await browser.close()


asyncio.run(main())
