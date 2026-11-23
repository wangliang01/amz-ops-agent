from __future__ import annotations

from dataclasses import dataclass

from core.config import Settings, settings as default_settings
from core.llm import LLMClient
from core.store import SeedStore
from rag.retriever import Retriever


@dataclass
class Services:
    cfg: Settings
    llm: LLMClient
    store: SeedStore
    retriever: Retriever


def build_services(cfg: Settings | None = None) -> Services:
    cfg = cfg or default_settings
    return Services(
        cfg=cfg,
        llm=LLMClient(cfg),
        store=SeedStore(cfg),
        retriever=Retriever(cfg=cfg),
    )
