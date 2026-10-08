"""docs/05-BACKEND-SPEC.md §12.3: each rail fires and stays clear on
crafted inputs, including tests/** and fix/0142 vs main."""

from __future__ import annotations

from greenline.guardrails.rails import protected_file


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
