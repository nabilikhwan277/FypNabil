"""Prompt files: the chat prompts render to one paragraph, and no prompt file is left unused."""
import re
from pathlib import Path

from backend.app import prompts

APP = Path(__file__).resolve().parents[1] / "app"


def test_chat_prompt_is_one_paragraph_with_its_parts():
    p = prompts.render_paragraph("chat", focus=" Soalan ini bertanyakan tentang niat.", anchor="\nFakta utama buku teks: X",
                                 decline="Data ini tiada dalam pangkalan data saya.")
    assert p == ("Anda ialah Bulan, pembantu belajar KAFA yang mesra untuk murid Tahun 5. "
                 "Jawab soalan murid tentang Ibadah, Jawi dan Tajwid secara ringkas (1 hingga 3 ayat sahaja), jelas dan tepat."
                 " Soalan ini bertanyakan tentang niat. "
                 "Gunakan fakta daripada petikan buku teks yang diberikan sahaja.\nFakta utama buku teks: X "
                 'Jika petikan buku teks tidak mengandungi jawapan, balas tepat: "Data ini tiada dalam pangkalan data saya." '
                 "dan tiada yang lain. "
                 "Jangan reka istilah baharu dan jangan ulang perkataan tanpa henti.")


def test_out_of_syllabus_prompt_asks_for_the_notice():
    p = prompts.render_paragraph("chat_outside", notice="Data ini tiada dalam pangkalan data saya.")
    assert 'Anda WAJIB memulakan jawapan tepat dengan: "Data ini tiada dalam pangkalan data saya." Selepas' in p
    assert "\n" not in p


def test_every_prompt_file_is_used():
    code = "\n".join(p.read_text(encoding="utf-8") for p in APP.rglob("*.py"))
    used = set(re.findall(r"""prompts\.render\w*\(\s*["'](\w+)["']""", code)) | set(re.findall(r"""render\w*\(\s*["'](\w+)["']""", code))
    files = {p.stem for p in (APP / "prompts").glob("*.txt")}
    assert files <= used, f"unused prompt files: {sorted(files - used)}"


def test_out_of_syllabus_prompt_does_not_allow_an_unchecked_general_knowledge_answer():
    p = prompts.render_paragraph("chat_outside", notice="Data ini tiada dalam pangkalan data saya.")
    assert "boleh membantu memberi jawapan" not in p
    assert "jangan jawab soalan tersebut" in p and "guru" in p
