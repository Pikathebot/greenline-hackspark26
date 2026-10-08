"""docs/05-BACKEND-SPEC.md §12.3: each rail fires and stays clear on
crafted inputs, including tests/** and fix/0142 vs main."""

from __future__ import annotations

from greenline.guardrails.rails import diff_within_cap, is_main_or_master, protected_file


def test_fires_on_tests_directory():
    assert protected_file(["tests/test_settlement.py"]) is True
    assert protected_file(["tests/test_payout.py"]) is True


def test_fires_on_nested_migrations():
    assert protected_file(["ledger_core/migrations/0001.py"]) is True


def test_fires_on_top_level_migrations():
    assert protected_file(["migrations/0001.py"]) is True


def test_fires_on_secret_in_name():
    assert protected_file(["ledger_core/my_secret_key.py"]) is True
    assert protected_file(["SECRETS.env"]) is True


def test_fires_on_github_workflows():
    assert protected_file([".github/workflows/ci.yml"]) is True


def test_stays_clear_on_ordinary_source_files():
    assert protected_file(["ledger_core/routes.py"]) is False
    assert protected_file(["ledger_core/http_client.py"]) is False
    assert protected_file(["ledger_core/vendor/http_util.py"]) is False


def test_fires_if_any_path_in_the_list_matches():
    assert protected_file(["ledger_core/routes.py", "tests/test_rollup.py"]) is True


def test_empty_list_stays_clear():
    assert protected_file([]) is False


def _diff_with_lines(n: int) -> str:
    header = "--- a/x\n+++ b/x\n"
    body = "\n".join(f"+line{i}" for i in range(n))
    return header + body


def test_diff_within_cap_at_exactly_80_lines():
    assert diff_within_cap(_diff_with_lines(80)) is True


def test_diff_within_cap_fires_over_80_lines():
    assert diff_within_cap(_diff_with_lines(81)) is False


def test_diff_within_cap_ignores_file_headers():
    # Only +/- content lines count, not the unified diff's own --- / +++.
    diff = "--- a/x\n+++ b/x\n" + "\n".join(f"+line{i}" for i in range(5))
    assert diff_within_cap(diff, max_lines=5) is True


def test_is_main_or_master_fires_on_main_and_master():
    assert is_main_or_master("main") is True
    assert is_main_or_master("master") is True


def test_is_main_or_master_stays_clear_on_fix_branch():
    assert is_main_or_master("fix/0142") is False
    assert is_main_or_master("fix/0139") is False
