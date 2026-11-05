"""End-to-end UI walkthrough with the real backend + models (dev check).

Requires: backend on :8000 and `npm run dev` on :5173.
Flow: login -> subject map -> Tajwid path -> topic (read note) -> practice L1
(answer) -> celebration dialog -> result -> AI trace -> round summary ->
Jawi practice with on-screen keyboard -> quick-answer buttons / word chips ->
progress -> Jawi script mode (desktop + mobile). Screenshots go to eval/results/ui_*.png
(set KAFA_SHOTS_DIR to write them somewhere else).

Usage: .venv\\Scripts\\python scripts\\e2e_ui.py
"""
import asyncio
import os
import re
import time
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright, expect

OUT = Path(os.environ.get("KAFA_SHOTS_DIR") or Path(__file__).resolve().parent.parent / "eval" / "results")
BASE = "http://localhost:5173"


async def shot(page, name, full=True):
    await page.wait_for_timeout(400)
    await page.screenshot(path=OUT / f"ui_{name}.png", full_page=full)
    print("  screenshot", name)


async def wait_ready(page):
    """Wait until the backend reports models loaded (warm-up)."""
    t0 = time.time()
    while time.time() - t0 < 240:
        h = await page.evaluate("fetch('/api/health').then(r => r.json())")
        if h["warm_up"] in ("ready", "error", "idle"):
            print("  models:", h["warm_up"], f"after {time.time() - t0:.0f}s")
            return
        await page.wait_for_timeout(2000)


async def close_celebration(page, name=None, timeout=4000):
    """The 'Hebat!' dialog opens ~1 s after a result that earns a badge, level or rank.
    Screenshot it (viewport only: it is a fixed overlay) and close it. Returns True if it opened."""
    dlg = page.get_by_role("dialog")
    try:
        await dlg.wait_for(state="visible", timeout=timeout)
    except PlaywrightTimeoutError:
        return False
    await page.wait_for_timeout(900)  # let the pop-in and confetti play
    print("  dialog:", " ".join((await dlg.inner_text()).split()))
    if name:
        await shot(page, name, full=False)
    await dlg.get_by_role("button", name="Teruskan").click()
    await expect(dlg).to_be_hidden()
    return True


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    bad: list[str] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1100, "height": 900})
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("response", lambda r: bad.append(f"{r.status} {r.url}") if r.status >= 500 else None)

        await page.goto(BASE + "/", wait_until="networkidle")
        await expect(page).to_have_url(BASE + "/login")
        await wait_ready(page)
        await page.get_by_label("Nama").fill("Aisyah E2E")
        await page.get_by_label("Kelas").fill("5 Bestari")
        await page.locator("label", has_text="Avatar 🐼").click()
        await expect(page.get_by_label("Avatar 🐼")).to_be_checked()
        await shot(page, "01_login")
        await page.get_by_role("button", name="Mula!").click()

        await expect(page.get_by_role("heading", name="Pilih subjek")).to_be_visible()
        await shot(page, "02_home")

        # the subject card (topic rows on the dashboard also name their subject; the sidebar has a link too)
        await page.locator("main").get_by_role("link", name=re.compile(r"^Tajwid")).click()
        await expect(page.get_by_role("heading", name="Tajwid", exact=True)).to_be_visible()
        await shot(page, "03_subject_tajwid")

        await page.get_by_role("link", name="Mad Badal").first.click()  # the topic card; the weak-topic list may name it too
        await expect(page.get_by_role("heading", name="Mad Badal", exact=True)).to_be_visible()
        await expect(page.locator("#note-panel")).to_contain_text("Pengertian")  # the lesson note is open on the topic page
        await shot(page, "04_topic_note")

        # Tahap 1 practice: answer correctly if it is the "kadar" question
        await page.get_by_role("link", name="Mula Latihan").first.click()
        await page.wait_for_url("**/latihan/**")
        await expect(page.get_by_text("Soalan 1/")).to_be_visible()  # the topic page has h2 headings too: wait for the question
        heading = page.locator("main h2").first
        practice_url = page.url
        q_text = await heading.inner_text()
        print("  question:", q_text)
        await shot(page, "05_practice_question")
        radios = page.get_by_role("radio")
        if await radios.count():  # Tahap 1 questions are often multiple choice
            right = radios.filter(has_text="Dua harakat")
            await (right if await right.count() else radios).first.click()
        else:
            await page.get_by_label("Jawapan kamu").fill("Dua harakat" if "kadar" in q_text.lower() else "saya tidak pasti")
        await page.get_by_role("button", name="Semak Jawapan").click()
        # the result's "Jawapan betul" section (the marking text may say "Jawapan betul: C" too)
        await expect(page.get_by_role("heading", name="Jawapan betul")).to_be_visible(timeout=120_000)
        # A pupil's first answer earns the "Langkah Pertama" badge; on later runs the
        # test pupil already has it, so the dialog only opens for a rank or level.
        if not await close_celebration(page, "06b_celebration", timeout=10_000):
            print("  (no celebration dialog: the test pupil already has the first badge)")
        await shot(page, "06_result")
        await page.get_by_text("Bagaimana AI berfikir").click()
        await expect(page.get_by_text("Thought 5:")).to_be_visible()
        await shot(page, "07_result_trace")

        # Stop the round early -> round summary
        await page.get_by_role("button", name="Berhenti").click()
        await expect(page.locator("#summary-title")).to_be_visible()
        await shot(page, "07b_round_summary")

        # Jawi subject: spelling with the on-screen keyboard (best effort: some questions are multiple choice)
        keyboard = page.get_by_role("group", name="Papan kekunci Jawi")
        for _ in range(8):
            await page.goto(BASE + "/latihan/jawi_b3_pinjaman_inggeris/1", wait_until="networkidle")
            await expect(page.get_by_text("Soalan 1/")).to_be_visible()
            if await keyboard.count():
                break
        if await keyboard.count():
            for ch in "بس":
                await page.get_by_role("button", name=f"Huruf {ch}", exact=True).click()
            typed = await page.get_by_label("Jawapan kamu").input_value()
            print("  keyboard typed:", repr(typed))
            assert typed == "بس", typed
            await shot(page, "08_jawi_keyboard")
            await page.get_by_role("button", name="Semak Jawapan").click()
            await expect(page.get_by_role("heading", name="Jawapan betul")).to_be_visible(timeout=120_000)
            await close_celebration(page)
            await shot(page, "09_jawi_result")
        else:
            print("  (no written Jawi question drawn)")

        # Quick answers (best effort: questions are picked at random)
        for _ in range(10):
            await page.goto(BASE + "/latihan/fiqh_b2_batal_puasa/1", wait_until="networkidle")
            await expect(page.locator("h2").first).to_be_visible()
            if await page.get_by_role("group", name="Pilih jawapan:").count():
                await page.get_by_role("button", name="Betul", exact=True).click()
                await expect(page.get_by_label("Jawapan kamu")).to_have_value("Betul")
                await shot(page, "05b_true_false")
                break
        else:
            print("  (no Betul/Salah question drawn)")
        for _ in range(12):
            await page.goto(BASE + "/latihan/fiqh_b1_solat_rawatib/1", wait_until="networkidle")
            await expect(page.locator("h2").first).to_be_visible()
            chips = page.get_by_role("group", name="Tekan perkataan untuk menjawab:")
            if await chips.count():
                await chips.get_by_role("button").first.click()
                print("  chips answer:", await page.get_by_label("Jawapan kamu").input_value())
                await shot(page, "05c_word_chips")
                break
        else:
            print("  (no fill-in-the-blank question drawn)")

        await page.get_by_role("link", name="Kemajuan Saya").click()
        await expect(page.get_by_text("Mata XP")).to_be_visible()
        await shot(page, "10_progress")

        await page.get_by_role("button", name="جاوي").click()
        await page.get_by_role("link", name="اوتاما").click()
        await expect(page.get_by_role("heading", name="ڤيليه سوبجيق")).to_be_visible()
        await shot(page, "11_home_jawi")
        await page.goto(practice_url, wait_until="networkidle")
        await expect(page.locator("h2").first).to_be_visible()
        await shot(page, "11b_practice_jawi")

        # Mobile layout (still in Jawi mode). Viewport shots, so the fixed bottom
        # tab bar sits at the bottom instead of mid-page.
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.goto(BASE + "/subjek/fiqh", wait_until="networkidle")
        await expect(page.get_by_role("navigation").last).to_be_visible()
        await shot(page, "12_mobile_subject_jawi", full=False)
        await page.goto(BASE + "/", wait_until="networkidle")
        await expect(page.get_by_role("heading", name="ڤيليه سوبجيق")).to_be_visible()
        await shot(page, "13_mobile_home_jawi", full=False)

        await browser.close()
    print("console errors:", errors or "none")
    print("server errors:", bad or "none")


asyncio.run(main())
