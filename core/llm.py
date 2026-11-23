from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Type

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError

from core.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            calls=self.calls + other.calls,
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "calls": self.calls,
        }


# USD per 1M tokens (input, output). Demo estimates only; override as needed.
MODEL_PRICES = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "deepseek-chat": (0.14, 0.28),
    "qwen-plus": (0.40, 1.20),
}


def estimate_cost(usage: Usage, model: str) -> float:
    inp, out = MODEL_PRICES.get(model, (0.50, 1.50))
    return (usage.prompt_tokens / 1_000_000) * inp + (usage.completion_tokens / 1_000_000) * out


def _extract_usage(msg: Any) -> Usage:
    um = getattr(msg, "usage_metadata", None) or {}
    if um:
        return Usage(
            prompt_tokens=int(um.get("input_tokens", 0) or 0),
            completion_tokens=int(um.get("output_tokens", 0) or 0),
            calls=1,
        )
    rm = getattr(msg, "response_metadata", None) or {}
    tu = rm.get("token_usage") or rm.get("usage") or {}
    return Usage(
        prompt_tokens=int(tu.get("prompt_tokens", 0) or 0),
        completion_tokens=int(tu.get("completion_tokens", 0) or 0),
        calls=1,
    )


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data


class LLMClient:
    """Small OpenAI-compatible client with strict JSON parsing and fallbacks."""

    def __init__(self, cfg: Settings = default_settings):
        self.cfg = cfg
        self.enabled = cfg.llm_ready
        self._models: dict[str, ChatOpenAI] = {}
        if not self.enabled:
            logger.warning(
                "LLM disabled: set OPENAI_API_KEY and LLM_ENABLED=true to enable generation."
            )

    def _get_model(self, model: str | None = None) -> ChatOpenAI:
        name = model or self.cfg.chat_model
        if name not in self._models:
            self._models[name] = ChatOpenAI(
                model=name,
                api_key=self.cfg.openai_api_key,
                base_url=self.cfg.openai_base_url,
                temperature=0,
                timeout=60,
                max_retries=1,
                max_tokens=self.cfg.max_tokens,
            )
        return self._models[name]

    def json(
        self,
        system: str,
        user: str,
        schema: Type[BaseModel] | None = None,
        fallback: dict[str, Any] | None = None,
        model: str | None = None,
    ) -> tuple[dict[str, Any], Usage]:
        if not self.enabled:
            return fallback or {}, Usage()

        messages = [SystemMessage(content=system), HumanMessage(content=user)]
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                msg = self._get_model(model).invoke(messages)
                data = _parse_json(str(msg.content))
                if schema is not None:
                    data = schema.model_validate(data).model_dump()
                return data, _extract_usage(msg)
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                messages = [
                    SystemMessage(
                        content=system
                        + "\n\nReturn ONLY a valid JSON object. "
                        "No markdown fences, no commentary."
                    ),
                    HumanMessage(content=user),
                ]
            except Exception as exc:  # provider/network errors: use fallback immediately
                last_error = exc
                break
        logger.warning("LLM call failed, using fallback: %s", last_error)
        return fallback or {}, Usage()
