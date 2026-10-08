"""Backend config. Every var is prefixed GREENLINE_ except GITHUB_TOKEN
(docs/03-ARCHITECTURE.md § Config). Read from backend/.env (gitignored)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from greenline.events.models import BudgetCaps

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GREENLINE_",
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    model_url: str = "http://127.0.0.1:8080"
    embed_url: str = "http://127.0.0.1:8081"
    model: str = "qwen3-8b"
    models_dir: str = "models"
    sandbox_image: str = "greenline-sandbox:latest"
    db_path: str = "greenline.db"
    fixture_repo: str = "fixtures/ledger-core"
    demo_runs_dir: str = "demo_runs"

    max_model_calls: int = 16
    max_tool_calls: int = 16
    max_elapsed_ms: int = 180_000

    tight_model_calls: int = 4
    tight_tool_calls: int = 3
    tight_elapsed_ms: int = 60_000

    rerun_concurrency: int = 1
    dry_run: bool = True

    # Demo playback speed multiplier (1.0 = original recorded pace). Not part
    # of the frozen contract; a dev/test knob only. Tests set it high so a
    # ~30s recorded run plays back in well under a second.
    demo_speed: float = 1.0

    cors_origins: str = "http://localhost:5173"

    # B18: real GitHub test repo. Both of these plus GITHUB_TOKEN switch it on.
    github_repo: str = ""  # e.g. "Pikathebot/ledger-core"
    github_poll_s: float = 10.0

    # Not GREENLINE_-prefixed.
    github_token: str = Field(default="", alias="GITHUB_TOKEN")

    def github_enabled(self) -> bool:
        return bool(self.github_repo and self.github_token)

    def caps(self, preset: str) -> BudgetCaps:
        if preset == "tight":
            return BudgetCaps(
                model_calls=self.tight_model_calls,
                tool_calls=self.tight_tool_calls,
                elapsed_ms=self.tight_elapsed_ms,
            )
        return BudgetCaps(
            model_calls=self.max_model_calls,
            tool_calls=self.max_tool_calls,
            elapsed_ms=self.max_elapsed_ms,
        )

    def models_path(self) -> Path:
        p = Path(self.models_dir)
        return p if p.is_absolute() else BACKEND_ROOT / p

    def db_full_path(self) -> Path:
        p = Path(self.db_path)
        return p if p.is_absolute() else BACKEND_ROOT / p

    def fixture_repo_path(self) -> Path:
        p = Path(self.fixture_repo)
        return p if p.is_absolute() else BACKEND_ROOT / p

    def extra_cases_path(self) -> Path:
        return self.fixture_repo_path().parent / "extra_cases.json"

    def demo_runs_path(self) -> Path:
        p = Path(self.demo_runs_dir)
        return p if p.is_absolute() else BACKEND_ROOT / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
