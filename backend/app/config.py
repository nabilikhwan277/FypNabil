"""Central configuration. Override any value with an env var prefixed KAFA_,
e.g. KAFA_LLM_MODEL_ID=... or KAFA_DEVICE=cpu."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]  # FypNabil/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KAFA_", env_file=ROOT / ".env", extra="ignore")

    # Models
    llm_model_id: str = "mesolitica/Malaysian-Llama-3.2-1B-Instruct"
    embed_model_id: str = "BAAI/bge-m3"
    device: str = "auto"          # auto | cuda | cpu
    llm_dtype: str = "float16"    # float16 | bfloat16 | float32
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

    # API
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    preload_models: bool = True   # load LLM + embedder in the background at startup


@lru_cache
def get_settings() -> Settings:
    return Settings()
