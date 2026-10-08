"""Memory store (docs/05-BACKEND-SPEC.md §2, §9; docs/02-DECISIONS.md
lesson 12). Tries sqlite-vec's vec0 virtual table first (L2 distance,
converted to cosine via `1 - d^2/2` since vectors are unit-normalised);
falls back to a plain BLOB-free table + Python cosine if extension
loading isn't available on this Python build -- it's only a few dozen
vectors, so the fallback's O(n) scan is fine.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384
SIMILARITY_THRESHOLD = 0.82
TOP_K = 3


class MemoryStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = threading.Lock()
        self._use_vec0 = self._try_load_sqlite_vec()
        self._create_tables()

    def _try_load_sqlite_vec(self) -> bool:
        try:
            import sqlite_vec

            self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            self._conn.enable_load_extension(False)
            return True
        except Exception as exc:
            logger.warning(
                "sqlite-vec extension unavailable (%s); falling back to a plain "
                "table + Python cosine similarity",
                exc,
            )
            return False

    def _create_tables(self) -> None:
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS memory_traces ("
                "trace_id TEXT PRIMARY KEY, run_id TEXT, case_id TEXT, cls TEXT, "
                "summary TEXT, vec_rowid INTEGER)"
            )
            if self._use_vec0:
                self._conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors "
                    f"USING vec0(embedding float[{EMBEDDING_DIM}])"
                )
            else:
                self._conn.execute(
                    "CREATE TABLE IF NOT EXISTS memory_vectors_fallback "
                    "(rowid INTEGER PRIMARY KEY, embedding TEXT)"
                )
            self._conn.commit()

    def store(self, run_id: str, case_id: str, cls: str, summary: str, embedding: list[float]) -> str:
        with self._lock:
            if self._use_vec0:
                import sqlite_vec

                cur = self._conn.execute(
                    "INSERT INTO memory_vectors (embedding) VALUES (?)",
                    (sqlite_vec.serialize_float32(embedding),),
                )
            else:
                cur = self._conn.execute(
                    "INSERT INTO memory_vectors_fallback (embedding) VALUES (?)",
                    (json.dumps(embedding),),
                )
            vec_rowid = cur.lastrowid

            trace_id = uuid.uuid4().hex
            self._conn.execute(
                "INSERT INTO memory_traces (trace_id, run_id, case_id, cls, summary, vec_rowid) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (trace_id, run_id, case_id, cls, summary, vec_rowid),
            )
            self._conn.commit()
            return trace_id

    def query_top_k(self, embedding: list[float], k: int = TOP_K) -> list[dict]:
        """Up to k nearest traces, best first:
        [{trace_id, run_id, case_id, cls, summary, similarity}, ...]."""
        with self._lock:
            if self._use_vec0:
                import sqlite_vec

                rows = self._conn.execute(
                    "SELECT rowid, distance FROM memory_vectors WHERE embedding MATCH ? "
                    "AND k = ? ORDER BY distance",
                    (sqlite_vec.serialize_float32(embedding), k),
                ).fetchall()
                candidates = [(rowid, 1 - (distance**2) / 2) for rowid, distance in rows]
            else:
                all_rows = self._conn.execute(
                    "SELECT rowid, embedding FROM memory_vectors_fallback"
                ).fetchall()
                scored = []
                for rowid, embedding_json in all_rows:
                    vec = json.loads(embedding_json)
                    # Both are already unit-normalised, so the dot product IS cosine.
                    similarity = sum(a * b for a, b in zip(embedding, vec, strict=True))
                    scored.append((rowid, similarity))
                scored.sort(key=lambda pair: pair[1], reverse=True)
                candidates = scored[:k]

            results = []
            for vec_rowid, similarity in candidates:
                row = self._conn.execute(
                    "SELECT trace_id, run_id, case_id, cls, summary FROM memory_traces "
                    "WHERE vec_rowid = ?",
                    (vec_rowid,),
                ).fetchone()
                if row is None:
                    continue
                trace_id, run_id, case_id, cls, summary = row
                results.append(
                    {
                        "trace_id": trace_id,
                        "run_id": run_id,
                        "case_id": case_id,
                        "cls": cls,
                        "summary": summary,
                        "similarity": similarity,
                    }
                )
            return results

    def reset(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM memory_traces")
            if self._use_vec0:
                self._conn.execute("DELETE FROM memory_vectors")
            else:
                self._conn.execute("DELETE FROM memory_vectors_fallback")
            self._conn.commit()


# -- process-wide singleton, set once by the FastAPI lifespan -------------

_store: MemoryStore | None = None


def init_memory_store(conn: sqlite3.Connection) -> MemoryStore:
    global _store
    _store = MemoryStore(conn)
    return _store


def get_memory_store() -> MemoryStore:
    if _store is None:
        raise RuntimeError("Memory store not initialized; call init_memory_store() first")
    return _store


def reset_memory_store_for_tests() -> None:
    global _store
    _store = None
