"""The Critic judges a diff against the real failing check, but only for pytest failures:
for lint-only logs the prompt must stay as it was (listing ruff findings made it reject the
one-shot `ruff --fix` patch)."""

from __future__ import annotations

from greenline.graph.nodes._util import failure_evidence
from greenline.graph.nodes.critic import _user_prompt

PYTEST_LOG = (
    "F\n"
    "E       assert 103.0 == 97.0\n"
    "E        +  where 103.0 = net_after_fee(100.0, 0.03)\n"
    "FAILED tests/test_fees.py::test_net_after_fee_deducts_fee - assert 103.0 == 97.0\n"
)
RUFF_LOG = "I001 [*] Import block is un-sorted or un-formatted\nF401 [*] `json` imported but unused\n"
ATTEMPT = {"file": "ledger_core/fees.py", "diff": "-    return a\n+    return b\n"}


def _state(ci_log: str) -> dict:
    return {"verdict_cls": "regression", "rationale": "why", "ci_log": ci_log}


def test_pytest_failure_is_shown_to_the_critic():
    prompt = _user_prompt(_state(PYTEST_LOG), ATTEMPT)
    assert "Failing check before the patch:" in prompt
    assert "assert 103.0 == 97.0" in prompt
    assert "the failing check now passes" in prompt
    assert prompt.index("Failing check") < prompt.index("Diff for")


def test_lint_only_log_keeps_the_original_prompt():
    prompt = _user_prompt(_state(RUFF_LOG), ATTEMPT)
    assert "Failing check" not in prompt
    assert prompt.endswith("Deterministic checks (tests and lint) are both green. Approve or reject.")


def test_missing_ci_log_is_harmless():
    assert "Failing check" not in _user_prompt({"verdict_cls": "env"}, ATTEMPT)


def test_failure_evidence_is_bounded():
    assert len(failure_evidence("\n".join(f"E   line {i}" for i in range(50))).splitlines()) == 5
