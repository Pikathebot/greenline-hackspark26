"""Flat Pydantic schemas for structured model output (docs/05-BACKEND-SPEC.md
§5). No nested BaseModel fields -- llama-server's schema-to-grammar
converter can 500 on external $refs (docs/02-DECISIONS.md lesson 4).
`extra="forbid"` so model_json_schema() emits additionalProperties: false,
matching the `strict: true` json_schema response_format.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from greenline.events.models import FailureClass


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TriageOutput(_StrictModel):
    cls: FailureClass
    rationale: str


class AnalystOutput(_StrictModel):
    cls: FailureClass
    rationale: str
    # Shown in logs only; confidence is computed from evidence (docs/05 §8).
    evidence_strength: Literal["weak", "moderate", "strong"]


class PatchOutput(_StrictModel):
    new_content: str  # the full corrected file -- the backend computes the real diff
    summary: str


class CriticOutput(_StrictModel):
    decision: Literal["approve", "reject"]
    rationale: str


class ReportOutput(_StrictModel):
    title: str
    body: str
