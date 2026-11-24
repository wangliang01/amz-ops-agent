from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    data_dir: Path = ROOT / "data" / "seed"
    chroma_dir: Path = ROOT / "data" / "chroma"
    db_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("RUNS_DB_PATH", str(ROOT / "data" / "runs.sqlite"))
        )
    )
    checkpoint_db_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("CHECKPOINT_DB_PATH", str(ROOT / "data" / "checkpoints.sqlite"))
        )
    )

    llm_enabled: bool = field(default_factory=lambda: _env_bool("LLM_ENABLED", True))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", "").strip())
    openai_base_url: str = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    )
    chat_model: str = field(default_factory=lambda: os.getenv("CHAT_MODEL", "gpt-4o-mini").strip())
    cheap_model: str = field(
        default_factory=lambda: os.getenv("CHEAP_MODEL", os.getenv("CHAT_MODEL", "gpt-4o-mini")).strip()
    )

    embedding_enabled: bool = field(default_factory=lambda: _env_bool("EMBEDDING_ENABLED", True))
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small").strip()
    )

    top_k: int = field(default_factory=lambda: int(os.getenv("TOP_K", "5")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("MAX_TOKENS", "1800")))
    llm_case_delay_sec: float = field(
        default_factory=lambda: float(os.getenv("LLM_CASE_DELAY_SEC", "0"))
    )
    target_acos: float = field(default_factory=lambda: float(os.getenv("TARGET_ACOS", "0.30")))
    creative_provider: str = field(
        default_factory=lambda: os.getenv("CREATIVE_PROVIDER", "mock").strip() or "mock"
    )
    adapter_mode: str = field(
        default_factory=lambda: os.getenv("ADAPTER_MODE", "mock").strip() or "mock"
    )
    api_base_url: str = field(
        default_factory=lambda: os.getenv("API_BASE_URL", "http://localhost:8000").strip()
    )

    @property
    def llm_ready(self) -> bool:
        return self.llm_enabled and bool(self.openai_api_key)

    @property
    def embedding_ready(self) -> bool:
        return self.embedding_enabled and bool(self.openai_api_key)


settings = Settings()
