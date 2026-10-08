"""Embedding client (docs/07-MODEL-RUNTIME.md). Talks to the second,
CPU-only llama-server (bge-small-en-v1.5). L2-normalises before returning,
so stored/queried vectors are unit vectors (lets sqlite-vec's L2 distance
convert to cosine via 1 - d^2/2).
"""

from __future__ import annotations

import math

import httpx

EMBED_TIMEOUT_S = 30.0


class EmbedClient:
    def __init__(self, base_url: str, timeout: float = EMBED_TIMEOUT_S) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def embed(self, text: str) -> list[float]:
        response = await self._client.post("/v1/embeddings", json={"input": text})
        response.raise_for_status()
        data = response.json()
        vector = data["data"][0]["embedding"]
        return _l2_normalize(vector)

    async def aclose(self) -> None:
        await self._client.aclose()


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


# -- process-wide singleton, set once by the FastAPI lifespan -------------

_client: EmbedClient | None = None


def init_embed_client(base_url: str) -> EmbedClient:
    global _client
    _client = EmbedClient(base_url)
    return _client


def get_embed_client() -> EmbedClient:
    if _client is None:
        raise RuntimeError("Embed client not initialized; call init_embed_client() first")
    return _client


def reset_embed_client_for_tests() -> None:
    global _client
    _client = None
