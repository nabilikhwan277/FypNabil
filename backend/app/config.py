"""Central configuration. Override any value with an env var prefixed KAFA_,
e.g. KAFA_LLM_MODEL_ID=... or KAFA_DEVICE=cpu."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]  # FypNabil/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KAFA_", env_file=ROOT / ".env", extra="ignore")

    # Models
    # Local LLM (chat + experiment model M5). Qwen3-4B-Instruct-2507, 4-bit (~2.8 GB VRAM);
    # the earlier Qwen2.5-3B (unsloth/Qwen2.5-3B-Instruct-bnb-4bit) also works here.
    llm_model_id: str = "unsloth/Qwen3-4B-Instruct-2507-bnb-4bit"
    # False = never load Qwen on this laptop; it runs on Google Colab instead
    # (notebooks/qwen_colab_server.ipynb, link pasted on the 📊 Penilaian page).
    local_llm: bool = True
    embed_model_id: str = "BAAI/bge-m3"
    device: str = "auto"          # auto | cuda | cpu
    llm_dtype: str = "float16"    # float16 | bfloat16 | float32
    llm_load_in_4bit: bool = True # Automatically uses 4-bit quantization on CUDA
    hf_cache_dir: Path = ROOT / "models"

    # Generation defaults (temperature 0 = greedy, for consistent grading)
    max_new_tokens_judge: int = 80
    max_new_tokens_feedback: int = 250
    # LLM-written encouragement line. Off by default: in the Phase 4 demo the 1B
    # model produced odd or looping sentences; templates are safer for children.
    llm_encouragement: bool = False

    # Data / storage
    knowledge_dir: Path = ROOT / "data" / "knowledge"
    questions_dir: Path = ROOT / "data" / "questions"
    chroma_dir: Path = ROOT / "storage" / "chroma"
    sqlite_path: Path = ROOT / "storage" / "kafa.db"

    # API language models (OpenRouter). The key lives in .env (git-ignored).
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_budget_usd: float = 4.0           # hard stop for API spending (all experiments together)
    llm_timeout_s: float = 120.0
    llm_cache_dir: Path = ROOT / "storage" / "llm_cache"     # same prompt + model is never paid twice
    llm_log_path: Path = ROOT / "storage" / "llm_calls.jsonl"

    # Retrieval: cross-encoder for RAG type R2 (runs on CPU so it never competes for the 6 GB GPU)
    reranker_model_id: str = "BAAI/bge-reranker-v2-m3"
    reranker_device: str = "cpu"

    # Live marker used by /api/answers: "b2" (rules + similarity, local, free) or an experiment
    # configuration such as "proposed:luna:R2:A2:on". Falls back to b2 if the API fails.
    scorer: str = "b2"
    # Show the Admin link in the pupils' sidebar. Turn off for pupil sessions.
    researcher_mode: bool = True
    # Password for the admin pages (evaluation, system setup, books & syllabus). Empty = admin sign-in is off.
    admin_password: str = ""
    # Uploaded books, their page images and drafts (git-ignored)
    books_dir: Path = ROOT / "storage" / "books"

    # API
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    preload_models: bool = True   # load LLM + embedder in the background at startup


@lru_cache
def get_settings() -> Settings:
    return Settings()
