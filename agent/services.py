from __future__ import annotations

from dataclasses import dataclass

from core.config import Settings, settings as default_settings
from core.llm import LLMClient
from core.store import SeedStore
from integrations import Adapters, build_adapters
from rag.retriever import Retriever


@dataclass
class Services:
    cfg: Settings
    llm: LLMClient
    store: SeedStore
    retriever: Retriever
    adapters: Adapters


def build_services(cfg: Settings | None = None) -> Services:
    cfg = cfg or default_settings
    store = SeedStore(cfg)
    return Services(
        cfg=cfg,
        llm=LLMClient(cfg),
        store=store,
        retriever=Retriever(cfg=cfg),
        adapters=build_adapters(store, cfg.adapter_mode),
    )
