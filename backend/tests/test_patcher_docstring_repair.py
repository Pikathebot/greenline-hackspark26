"""The model often returns a one-line module docstring without its quotes (seen on #0139
in every live run). _restore_docstring_quotes puts the original line back, narrowly."""

from __future__ import annotations

import ast

from greenline.graph.nodes.patcher import _restore_docstring_quotes

OLD = '"""Thin wrapper around the vendored retry policy."""\n\nfrom x import Retry\n'


def test_restores_dropped_docstring_quotes():
    draft = "Thin wrapper around the vendored retry policy.\n\nfrom x import RetryPolicy\n"
    repaired = _restore_docstring_quotes(OLD, draft)
    assert repaired.splitlines()[0] == '"""Thin wrapper around the vendored retry policy."""'
    assert repaired.endswith("from x import RetryPolicy\n")
    ast.parse(repaired)


def test_leaves_other_first_lines_alone():
    draft = "something else entirely\nfrom x import RetryPolicy\n"
    assert _restore_docstring_quotes(OLD, draft) == draft


def test_leaves_valid_drafts_and_non_docstring_files_alone():
    assert _restore_docstring_quotes(OLD, OLD) == OLD
    assert _restore_docstring_quotes("import os\n", "os\n") == "os\n"
    assert _restore_docstring_quotes("", "x") == "x"
