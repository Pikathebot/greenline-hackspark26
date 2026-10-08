"""Loads llm/prompts/*.md (docs/05-BACKEND-SPEC.md §6). Kept as plain
markdown files, not Python strings, so a prompt can be edited without a
code change."""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
