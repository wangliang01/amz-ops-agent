from __future__ import annotations

import time
from typing import Any

from langchain_openai import ChatOpenAI

_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


def _status_code(exc: BaseException) -> int | None:
    for attr in ("status_code", "status", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def invoke_with_retry(model: ChatOpenAI, messages: Any) -> Any:
    """Invoke a chat model with bounded backoff for transient/rate-limit errors."""
    last_error: BaseException | None = None
    for attempt in range(4):
        try:
            return model.invoke(messages)
        except Exception as exc:
            last_error = exc
            if _status_code(exc) not in _RETRYABLE_STATUS or attempt == 3:
                raise
            time.sleep(2**attempt)
    assert last_error is not None
    raise last_error
