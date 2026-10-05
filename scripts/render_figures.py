"""Render the thesis diagrams (docs/figures/src/*.mmd) to PNG with Mermaid in a
headless browser, and copy the chosen UI screenshots next to them.

Mermaid is loaded from the jsDelivr CDN (a public library download; no project
data is sent). Usage: .venv\\Scripts\\python scripts\\render_figures.py
Output: docs/figures/*.png
"""
import asyncio
import json
import shutil
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "figures" / "src"
OUT = ROOT / "docs" / "figures"
MERMAID = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"

SCREENSHOTS = {
    "fig_3_7_ui_home.png": "ui_02_home.png",
    "fig_3_8_ui_subject_path.png": "ui_03_subject_tajwid.png",
    "fig_3_9_ui_topic_note.png": "ui_04_topic_note.png",
    "fig_3_10_ui_jawi_keyboard.png": "ui_08_jawi_keyboard.png",
    "fig_3_11_ui_result.png": "ui_06_result.png",
    "fig_3_12_ui_react_trace.png": "ui_07_result_trace.png",
    "fig_3_13_ui_progress.png": "ui_10_progress.png",
    "fig_3_14_ui_jawi_mode_mobile.png": "ui_12_mobile_subject_jawi.png",
}

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>body{margin:0;background:#fff;font-family:Arial,sans-serif} #d{display:inline-block;padding:16px}</style>
<script src="%s"></script></head><body><div id="d"></div>
<script>
mermaid.initialize({startOnLoad:false, theme:'default', fontFamily:'Arial', flowchart:{htmlLabels:true}});
window.draw = async (code) => {
  const {svg} = await mermaid.render('g', code);
  document.getElementById('d').innerHTML = svg;
  return true;
};
</script></body></html>""" % MERMAID


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(device_scale_factor=2, viewport={"width": 1600, "height": 1200})
        await page.set_content(PAGE, wait_until="networkidle")
        for src in sorted(SRC.glob("*.mmd")):
            await page.evaluate(f"window.draw({json.dumps(src.read_text(encoding='utf-8'))})")
            await page.wait_for_timeout(300)
            out = OUT / f"{src.stem}.png"
            await page.locator("#d").screenshot(path=out)
            print("rendered", out.name)
        await browser.close()
    shots = ROOT / "eval" / "results"
    for dest, name in SCREENSHOTS.items():
        if (shots / name).exists():
            shutil.copy(shots / name, OUT / dest)
            print("copied", dest)


asyncio.run(main())
