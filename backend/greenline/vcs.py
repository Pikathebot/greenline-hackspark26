"""Dry-run VCS integration (docs/05-BACKEND-SPEC.md §9 Reporter; D13).

Real draft PRs are a documented stretch goal only (docs/02-DECISIONS.md
D13), and the fixture repo has no GitHub remote to push `fix/<caseId>` to
-- this build implements only the dry-run path.
"""

from __future__ import annotations

import random


def open_draft_pr(title: str, body: str, branch: str, dry_run: bool = True) -> dict:
    if not dry_run:
        raise NotImplementedError(
            "Real PR creation is a stretch goal (docs/02-DECISIONS.md D13) and isn't "
            "wired up here -- the fixture repo has no GitHub remote. Set "
            "GREENLINE_DRY_RUN=true (the default)."
        )
    number = random.randint(100, 999)
    return {
        "number": number,
        "url": f"https://github.com/acme/ledger-core/pull/{number}",
        "dry_run": True,
        "branch": branch,
    }
