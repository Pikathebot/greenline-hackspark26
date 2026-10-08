"""B5: run_case.py <case_id> [--ci-only] [--reruns N] [--ruff-fix]

Exercises the real sandbox against a real case branch and prints the
actual reason for red/green. A case that fails for the wrong reason
silently invalidates its demo beat (docs/06-FIXTURE-REPO-SPEC.md), so this
checks the REASON, not just red/green.

Run from backend/: .venv\\Scripts\\python.exe scripts\\run_case.py 0142 --ci-only
                    .venv\\Scripts\\python.exe scripts\\run_case.py 0142 --reruns 10
"""

from __future__ import annotations

import argparse
import sys

from greenline.config import get_settings
from greenline.graph.cases import CASE_CONFIGS, reload_extra_cases
from greenline.graph.nodes._util import first_failing_line
from greenline.sandbox.runner import SandboxRunner


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id")
    parser.add_argument("--ci-only", action="store_true", help="run_ci once, print the reason")
    parser.add_argument(
        "--reruns", type=int, default=0, help="run_test N times (reproducer-style)"
    )
    parser.add_argument("--ruff-fix", action="store_true", help="run ruff_fix, print the result")
    args = parser.parse_args()

    reload_extra_cases(get_settings().extra_cases_path())
    if args.case_id not in CASE_CONFIGS:
        print(f"Unknown case {args.case_id!r}. Known: {', '.join(CASE_CONFIGS)}", file=sys.stderr)
        sys.exit(1)

    config = CASE_CONFIGS[args.case_id]
    settings = get_settings()
    runner = SandboxRunner(settings.fixture_repo_path(), settings.sandbox_image)

    did_anything = False

    if args.ci_only or (not args.reruns and not args.ruff_fix):
        did_anything = True
        result = runner.run_ci(config.branch)
        status = "PASS" if result.passed else "FAIL"
        print(f"[{args.case_id}] run_ci: {status} (exit={result.exit_code}, {result.duration_ms}ms)")
        print(f"  reason: {first_failing_line(result.stdout + result.stderr)}")

    if args.reruns:
        did_anything = True
        if config.failing_test_nodeid is None:
            print(f"[{args.case_id}] has no failing_test_nodeid (lint case) -- nothing to rerun")
        else:
            passed = failed = 0
            for n in range(1, args.reruns + 1):
                result = runner.run_test(config.branch, config.failing_test_nodeid)
                passed += int(result.passed)
                failed += int(not result.passed)
                print(
                    f"  rerun {n}/{args.reruns}: "
                    f"{'PASS' if result.passed else 'FAIL'} ({result.duration_ms}ms)"
                )
            print(f"[{args.case_id}] {passed} pass / {failed} fail across {args.reruns} reruns")

    if args.ruff_fix:
        did_anything = True
        if config.patch_target is None:
            print(f"[{args.case_id}] has no patch_target -- nothing to fix")
        else:
            result = runner.ruff_fix(config.branch, config.patch_target)
            print(f"[{args.case_id}] ruff_fix {config.patch_target}:")
            print(result.stdout)

    if not did_anything:
        parser.print_help()


if __name__ == "__main__":
    main()
