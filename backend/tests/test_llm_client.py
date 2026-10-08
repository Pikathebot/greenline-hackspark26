"""B6 acceptance (docs/07-MODEL-RUNTIME.md § Structured output / Smoke test):
send TriageOutput for the 0139 CI log 20 times. Must parse 20/20, average
under 3s.

Needs the real llama-server (and Docker, to fetch a real CI log from the
fixture repo) -- excluded from the default `pytest` run. Run explicitly:
    .venv\\Scripts\\python.exe -m pytest -m slow tests\\test_llm_client.py -v
"""

from __future__ import annotations

import time

import pytest

from greenline.config import get_settings
from greenline.graph.cases import CASE_CONFIGS
from greenline.llm.client import LLMClient
from greenline.llm.schemas import TriageOutput
from greenline.sandbox.runner import SandboxRunner

pytestmark = pytest.mark.slow

TRIAGE_SYSTEM = (
    "You are the Triage agent in Greenline, an agentic CI triage system for a "
    "Python repo (pytest + ruff). Classify the failing CI log into exactly one "
    "of five classes: flaky (intermittent, timing/order dependent), dependency "
    "(import/symbol error tied to a version/pin), env (missing environment "
    "configuration), lint (static analysis fails, tests pass), or regression "
    "(deterministic failure from a logic change). Respond with the class and a "
    "1-2 sentence rationale citing specific log lines."
)


@pytest.fixture(scope="module")
def ci_log() -> str:
    settings = get_settings()
    runner = SandboxRunner(settings.fixture_repo_path(), settings.sandbox_image)
    config = CASE_CONFIGS["0139"]
    result = runner.run_ci(config.branch)
    assert not result.passed  # 0139 is deterministically red
    return (result.stdout + result.stderr)[-2000:]  # last ~60 lines' worth


@pytest.fixture(scope="module")
def client() -> LLMClient:
    settings = get_settings()
    return LLMClient(settings.model_url)


async def test_triage_output_round_trips_20_of_20_under_3s_average(client, ci_log):
    durations = []
    for _ in range(20):
        started = time.monotonic()
        result = await client.complete(
            TRIAGE_SYSTEM, f"CI log:\n{ci_log}\n\nClassify this failure.", TriageOutput, 0.3
        )
        durations.append(time.monotonic() - started)
        assert isinstance(result, TriageOutput)
        assert result.cls in ("flaky", "dependency", "env", "lint", "regression")
        assert result.rationale

    average = sum(durations) / len(durations)
    print(f"\nTriageOutput: 20/20 parsed, average {average:.2f}s, max {max(durations):.2f}s")
    assert average < 3.0, f"average {average:.2f}s exceeds the 3s target"
