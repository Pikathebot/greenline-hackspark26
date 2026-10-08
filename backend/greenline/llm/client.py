"""LLM client (docs/05-BACKEND-SPEC.md §5, docs/07-MODEL-RUNTIME.md).

One global asyncio.Lock around the HTTP call (one GPU, one queue). Retries
up to 3x on transport/JSON/validation errors, 120s timeout per attempt.
After 3 failures, raises ModelUnavailable -- the run manager turns that
into an `error` event. Budget accounting (record_model_call) happens in the
CALLING node, not here, because this client is shared and run-agnostic.
"""

from __future__ import annotations

import asyncio
import json
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

MAX_ATTEMPTS = 3
REQUEST_TIMEOUT_S = 120.0


class ModelUnavailable(Exception):
    """Raised after MAX_ATTEMPTS failed calls to the model server."""


class LLMClient:
    def __init__(self, base_url: str, timeout: float = REQUEST_TIMEOUT_S) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self._lock = asyncio.Lock()

    async def complete(self, system: str, user: str, schema: type[T], temperature: float) -> T:
        payload = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                    "strict": True,
                },
            },
        }

        last_exc: Exception | None = None
        for _ in range(MAX_ATTEMPTS):
            try:
                async with self._lock:
                    response = await self._client.post("/v1/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return schema.model_validate(parsed)
            except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError, ValidationError) as exc:
                last_exc = exc
                continue

        raise ModelUnavailable(
            f"{schema.__name__} call failed after {MAX_ATTEMPTS} attempts: {last_exc}"
        ) from last_exc

    async def aclose(self) -> None:
        await self._client.aclose()


# -- process-wide singleton, set once by the FastAPI lifespan -------------

_client: LLMClient | None = None


def init_llm_client(base_url: str) -> LLMClient:
    global _client
    _client = LLMClient(base_url)
    return _client


def get_llm_client() -> LLMClient:
    if _client is None:
        raise RuntimeError("LLM client not initialized; call init_llm_client() first")
    return _client


def reset_llm_client_for_tests() -> None:
    global _client
    _client = None
