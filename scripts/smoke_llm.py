"""Phase 2 smoke test: load the LLM and embedder, ask Rumi + Jawi prompts,
report latency and VRAM. Downloads models on first run (~2.5 GB + ~2.3 GB).

Usage (from FypNabil/):  .venv\\Scripts\\python scripts\\smoke_llm.py
Writes results to eval/results/smoke_llm.json
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402

from backend.app.embeddings import embed, get_embedder  # noqa: E402
from backend.app.llm import get_llm  # noqa: E402

PROMPTS = [
    ("rumi_fact", "Berapakah kadar harakat bacaan Mad Asli? Jawab dalam satu ayat pendek."),
    ("rumi_explain", "Terangkan secara ringkas apakah solat sunat dhuha kepada murid Tahun 5."),
    ("jawi_reply", "جاوب دالم توليسن جاوي: اڤاكه مقصود وقف؟"),
    ("json_judge",
     "Anda pemeriksa jawapan. Kriteria: 'Menyatakan kadar dua harakat'. "
     "Jawapan murid: 'dua harakat'. Balas JSON sahaja: {\"met\": \"ya|separa|tidak\", \"reason\": \"...\"}"),
    # Same questions, but grounded with a textbook passage (what RAG will supply).
    ("rumi_fact_grounded",
     "Nota buku teks: \"Kadar panjang bacaan Mad Asli ialah dua harakat.\"\n"
     "Berdasarkan nota di atas SAHAJA, jawab: Berapakah kadar harakat bacaan Mad Asli? Jawab dalam satu ayat pendek."),
    ("json_judge_grounded",
     "Anda pemeriksa jawapan murid Tahun 5.\n"
     "Nota buku teks: \"Kadar panjang bacaan Mad Asli ialah dua harakat.\"\n"
     "Soalan: Berapakah kadar harakat bacaan Mad Asli?\n"
     "Jawapan rujukan: dua harakat\n"
     "Kriteria: Menyatakan kadar dua harakat\n"
     "Jawapan murid: \"2 harakat\"\n"
     "Adakah jawapan murid memenuhi kriteria? Balas JSON sahaja, tanpa teks lain: "
     "{\"met\": \"ya\" atau \"separa\" atau \"tidak\", \"reason\": \"sebab ringkas\"}"),
    ("json_judge_grounded_wrong",
     "Anda pemeriksa jawapan murid Tahun 5.\n"
     "Nota buku teks: \"Kadar panjang bacaan Mad Asli ialah dua harakat.\"\n"
     "Soalan: Berapakah kadar harakat bacaan Mad Asli?\n"
     "Jawapan rujukan: dua harakat\n"
     "Kriteria: Menyatakan kadar dua harakat\n"
     "Jawapan murid: \"enam harakat\"\n"
     "Adakah jawapan murid memenuhi kriteria? Balas JSON sahaja, tanpa teks lain: "
     "{\"met\": \"ya\" atau \"separa\" atau \"tidak\", \"reason\": \"sebab ringkas\"}"),
]


def vram_gb() -> float:
    return round(torch.cuda.max_memory_allocated() / 1024**3, 2) if torch.cuda.is_available() else 0.0


def main() -> None:
    results = {"cuda": torch.cuda.is_available()}

    t0 = time.perf_counter()
    llm = get_llm()
    results["llm_load_s"] = round(time.perf_counter() - t0, 1)
    results["llm_device"] = llm.device
    results["vram_after_llm_gb"] = vram_gb()
    print(f"LLM loaded on {llm.device} in {results['llm_load_s']}s, VRAM {results['vram_after_llm_gb']} GB")

    llm.generate([{"role": "user", "content": "Salam"}], max_new_tokens=5)  # warm-up

    results["prompts"] = []
    for name, prompt in PROMPTS:
        g = llm.generate([{"role": "user", "content": prompt}], max_new_tokens=150)
        tps = round(g.new_tokens / (g.latency_ms / 1000), 1) if g.latency_ms else 0
        results["prompts"].append({"name": name, "prompt": prompt, "reply": g.text,
                                   "latency_ms": g.latency_ms, "new_tokens": g.new_tokens,
                                   "tokens_per_s": tps})
        print(f"\n[{name}] {g.latency_ms} ms, {g.new_tokens} tok ({tps} tok/s)\n  Q: {prompt}\n  A: {g.text}")

    t0 = time.perf_counter()
    get_embedder()
    results["embed_load_s"] = round(time.perf_counter() - t0, 1)
    pairs = [("Mad Asli dibaca dua harakat.", "Kadar Mad Asli ialah 2 harakat."),
             ("Mad Asli dibaca dua harakat.", "Solat dhuha didirikan pada waktu pagi."),
             ("اڤاكه مقصود وقف؟", "Waqaf ialah memberhentikan bacaan.")]
    sims = []
    for a, b in pairs:
        va, vb = embed([a, b])
        sims.append({"a": a, "b": b, "cosine": round(sum(x * y for x, y in zip(va, vb)), 3)})
    results["similarity"] = sims
    results["vram_peak_gb"] = vram_gb()
    print(f"\nEmbedder loaded in {results['embed_load_s']}s. Similarities:")
    for s in sims:
        print(f"  {s['cosine']:.3f}  {s['a']}  <->  {s['b']}")
    print(f"\nPeak VRAM: {results['vram_peak_gb']} GB")

    out = ROOT / "eval" / "results" / "smoke_llm.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
