"""MemoryStore (docs/05-BACKEND-SPEC.md §2; docs/02-DECISIONS.md lesson 12).
Exercises both the sqlite-vec path (available on this machine, confirmed
at B10) and the Python-cosine fallback, with synthetic unit vectors --
no embedding server needed.
"""

from __future__ import annotations

import math
import sqlite3

import pytest

from greenline.memory.store import MemoryStore


def _unit(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector]


def _vec(dim: int, hot_index: int, lean: float = 0.0) -> list[float]:
    """A unit vector mostly pointing along `hot_index`, with a little
    lean toward index 0 to produce a controllable, non-trivial similarity."""
    v = [0.0] * dim
    v[hot_index] = 1.0
    if lean and hot_index != 0:
        v[0] = lean
    return _unit(v)


@pytest.fixture(params=["vec0", "fallback"])
def store(request, monkeypatch):
    if request.param == "fallback":
        import sqlite_vec

        def _raise(*_args, **_kwargs):
            raise RuntimeError("extension loading disabled for this test")

        monkeypatch.setattr(sqlite_vec, "load", _raise)

    conn = sqlite3.connect(":memory:")
    memory_store = MemoryStore(conn)
    assert memory_store._use_vec0 is (request.param == "vec0")
    yield memory_store
    conn.close()


def test_store_and_query_round_trip(store: MemoryStore):
    v1 = _vec(384, 1)
    v2 = _vec(384, 2)
    store.store("run-1", "0142", "flaky", "settlement flakiness", v1)
    store.store("run-2", "0139", "dependency", "import rename", v2)

    results = store.query_top_k(v1, k=3)
    assert results[0]["case_id"] == "0142"
    assert results[0]["cls"] == "flaky"
    assert results[0]["summary"] == "settlement flakiness"
    assert results[0]["similarity"] == pytest.approx(1.0, abs=1e-4)


def test_similarity_ordering_best_first(store: MemoryStore):
    exact = _vec(384, 5)
    close = _vec(384, 6, lean=0.3)  # similar-ish via the shared lean axis
    far = _vec(384, 10)

    store.store("run-1", "0142", "flaky", "exact match", exact)
    store.store("run-2", "0144", "flaky", "close match", close)
    store.store("run-3", "0139", "dependency", "far match", far)

    query = _vec(384, 5)  # identical to `exact`
    results = store.query_top_k(query, k=3)
    sims = [r["similarity"] for r in results]
    assert sims == sorted(sims, reverse=True)
    assert results[0]["summary"] == "exact match"


def test_query_top_k_respects_k(store: MemoryStore):
    for i in range(5):
        store.store(f"run-{i}", f"case-{i}", "flaky", f"trace {i}", _vec(384, i))
    results = store.query_top_k(_vec(384, 0), k=2)
    assert len(results) == 2


def test_reset_clears_everything(store: MemoryStore):
    store.store("run-1", "0142", "flaky", "x", _vec(384, 1))
    assert store.query_top_k(_vec(384, 1), k=3)
    store.reset()
    assert store.query_top_k(_vec(384, 1), k=3) == []


def test_empty_store_returns_nothing(store: MemoryStore):
    assert store.query_top_k(_vec(384, 0), k=3) == []
