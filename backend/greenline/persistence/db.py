"""SQLite persistence (docs/05-BACKEND-SPEC.md §2). One connection,
check_same_thread=False, WAL mode, idempotent CREATE TABLE IF NOT EXISTS,
no migration framework. Memory tables are added at ticket B10, not here."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    budget_preset TEXT NOT NULL,
    status TEXT NOT NULL,              -- running | complete | error
    outcome TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    model_calls INTEGER NOT NULL DEFAULT 0,
    tool_calls INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER
);

CREATE TABLE IF NOT EXISTS events (
    run_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    t INTEGER NOT NULL,
    type TEXT NOT NULL,
    payload TEXT NOT NULL,             -- JSON, verbatim wire event
    PRIMARY KEY (run_id, seq)
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- runs ----------------------------------------------------------

    def insert_run(
        self, run_id: str, case_id: str, mode: str, budget_preset: str, started_at: str
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO runs (run_id, case_id, mode, budget_preset, status, started_at) "
                "VALUES (?, ?, ?, ?, 'running', ?)",
                (run_id, case_id, mode, budget_preset, started_at),
            )
            self._conn.commit()

    def finish_run(
        self,
        run_id: str,
        status: str,
        outcome: str | None,
        ended_at: str,
        model_calls: int,
        tool_calls: int,
        duration_ms: int,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET status=?, outcome=?, ended_at=?, model_calls=?, tool_calls=?, "
                "duration_ms=? WHERE run_id=?",
                (status, outcome, ended_at, model_calls, tool_calls, duration_ms, run_id),
            )
            self._conn.commit()

    def get_run(self, run_id: str) -> sqlite3.Row | None:
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            cur = self._conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,))
            return cur.fetchone()

    def active_run(self) -> sqlite3.Row | None:
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            cur = self._conn.execute(
                "SELECT * FROM runs WHERE status='running' ORDER BY started_at DESC LIMIT 1"
            )
            return cur.fetchone()

    def last_completed_live(self, case_id: str) -> sqlite3.Row | None:
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            cur = self._conn.execute(
                "SELECT * FROM runs WHERE case_id=? AND mode='live' AND status='complete' "
                "ORDER BY ended_at DESC LIMIT 1",
                (case_id,),
            )
            return cur.fetchone()

    def runs_for_case(self, case_id: str, mode: str | None = None) -> list[sqlite3.Row]:
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            if mode is None:
                cur = self._conn.execute(
                    "SELECT * FROM runs WHERE case_id=? AND status='complete' ORDER BY ended_at",
                    (case_id,),
                )
            else:
                cur = self._conn.execute(
                    "SELECT * FROM runs WHERE case_id=? AND mode=? AND status='complete' "
                    "ORDER BY ended_at",
                    (case_id, mode),
                )
            return cur.fetchall()

    def all_completed_live_runs(self) -> list[sqlite3.Row]:
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            cur = self._conn.execute(
                "SELECT * FROM runs WHERE mode='live' AND status='complete' ORDER BY ended_at"
            )
            return cur.fetchall()

    # -- events ----------------------------------------------------------

    def insert_event(self, run_id: str, seq: int, t: int, type_: str, payload_json: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO events (run_id, seq, t, type, payload) VALUES (?, ?, ?, ?, ?)",
                (run_id, seq, t, type_, payload_json),
            )
            self._conn.commit()

    def events_for(self, run_id: str) -> list[tuple[int, str]]:
        """Returns [(seq, payload_json), ...] ordered by seq, for SSE replay."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT seq, payload FROM events WHERE run_id=? ORDER BY seq", (run_id,)
            )
            return cur.fetchall()


# -- process-wide singleton, set once by the FastAPI lifespan -------------

_db: Database | None = None


def init_db(path: Path) -> Database:
    global _db
    _db = Database(path)
    return _db


def get_db() -> Database:
    if _db is None:
        raise RuntimeError("Database not initialized; call init_db() first")
    return _db


def reset_db_for_tests() -> None:
    """Test-only: drop the singleton so a fresh init_db() can rebind it."""
    global _db
    if _db is not None:
        _db.close()
    _db = None
