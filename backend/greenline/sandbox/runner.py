"""Sandbox runner (docs/05-BACKEND-SPEC.md §7).

Fresh container per run, never reused, always removed in `finally` (retry
once, log, never raise). Docker via the Python SDK, never shell. Methods are
synchronous; nodes call them via asyncio.to_thread.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import docker

logger = logging.getLogger(__name__)

CONTAINER_TIMEOUT_S = 30


@dataclass
class TestResult:
    __test__ = False  # not a pytest test class, despite the name

    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    command: str


_SENTINEL_RE = re.compile(r"__(PYTEST|RUFF)_EXIT_(-?\d+)__")


class SandboxRunner:
    def __init__(self, fixture_repo: Path, image: str = "greenline-sandbox:latest") -> None:
        self.fixture_repo = fixture_repo
        self.image = image
        self._client = docker.from_env()

    # -- construction kwargs: asserted at run start for no_creds/egress_off --

    @staticmethod
    def construction_kwargs() -> dict:
        return {
            "network_disabled": True,
            "environment": {},
            "mem_limit": "1g",
            "pids_limit": 256,
            "nano_cpus": 1_000_000_000,
            "working_dir": "/work",
        }

    # -- host-side git helpers (no container) -----------------------------

    def read_file(self, branch: str, path: str) -> str:
        result = subprocess.run(
            ["git", "show", f"{branch}:{path}"],
            cwd=self.fixture_repo,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise FileNotFoundError(f"{branch}:{path} -- {result.stderr.strip()}")
        return result.stdout

    def breaking_diff(self, branch: str) -> str:
        result = subprocess.run(
            ["git", "diff", f"main...{branch}"],
            cwd=self.fixture_repo,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git diff main...{branch} failed: {result.stderr.strip()}")
        return result.stdout

    # -- scratch checkout: git archive, no .git inside --------------------

    def _checkout_scratch(self, branch: str) -> Path:
        scratch = Path(tempfile.mkdtemp(prefix="greenline-sandbox-"))
        archive = subprocess.run(
            ["git", "archive", branch], cwd=self.fixture_repo, capture_output=True
        )
        if archive.returncode != 0:
            shutil.rmtree(scratch, ignore_errors=True)
            raise RuntimeError(f"git archive {branch} failed: {archive.stderr.decode()}")
        tar_path = scratch / "archive.tar"
        tar_path.write_bytes(archive.stdout)
        with tarfile.open(tar_path) as tar:
            tar.extractall(scratch, filter="data")
        tar_path.unlink()
        return scratch

    def _overwrite(self, scratch: Path, path: str, content: str) -> None:
        target = scratch / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")

    # -- container execution ----------------------------------------------

    def _run_in_container(self, scratch: Path, command: list[str]) -> TestResult:
        started = time.monotonic()
        container = self._client.containers.run(
            self.image,
            command,
            detach=True,
            volumes={str(scratch): {"bind": "/work", "mode": "rw"}},
            **self.construction_kwargs(),
        )
        try:
            try:
                wait_result = container.wait(timeout=CONTAINER_TIMEOUT_S)
                exit_code = wait_result.get("StatusCode", -1)
            except Exception:
                try:
                    container.kill()
                except Exception:
                    pass
                exit_code = -1
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
        finally:
            for attempt in range(2):
                try:
                    container.remove(force=True)
                    break
                except Exception as exc:
                    if attempt == 1:
                        logger.warning("failed to remove container %s: %s", container.id, exc)

        duration_ms = int((time.monotonic() - started) * 1000)
        return TestResult(
            passed=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            command=" ".join(command),
        )

    # -- public API (docs/05 §7 table) -------------------------------------

    def run_ci(self, branch: str) -> TestResult:
        """pytest -q then ruff check ., output concatenated, exit = first non-zero."""
        scratch = self._checkout_scratch(branch)
        try:
            command = [
                "sh",
                "-c",
                "pytest -q; ec1=$?; ruff check .; ec2=$?; "
                "if [ $ec1 -ne 0 ]; then exit $ec1; else exit $ec2; fi",
            ]
            return self._run_in_container(scratch, command)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def run_test(self, branch: str, nodeid: str) -> TestResult:
        scratch = self._checkout_scratch(branch)
        try:
            command = ["python", "-m", "pytest", "-q", nodeid, "-p", "no:cacheprovider"]
            return self._run_in_container(scratch, command)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def ruff_fix(self, branch: str, path: str) -> TestResult:
        """ruff check --fix <path>, then print the file content."""
        scratch = self._checkout_scratch(branch)
        try:
            command = ["sh", "-c", f"ruff check --fix {path} >/dev/null 2>&1; cat {path}"]
            return self._run_in_container(scratch, command)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def run_patched(self, branch: str, path: str, content: str) -> dict:
        """Same as run_ci but with `path` overwritten first. Returns
        {tests_passed, lint_passed, output}: both results separately, unlike
        run_ci's single collapsed exit code."""
        scratch = self._checkout_scratch(branch)
        try:
            self._overwrite(scratch, path, content)
            command = [
                "sh",
                "-c",
                'pytest -q; echo "__PYTEST_EXIT_$?__"; '
                'ruff check .; echo "__RUFF_EXIT_$?__"',
            ]
            result = self._run_in_container(scratch, command)
            return _parse_patched_result(result)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)


def _parse_patched_result(result: TestResult) -> dict:
    exits = {"PYTEST": -1, "RUFF": -1}
    for match in _SENTINEL_RE.finditer(result.stdout):
        exits[match.group(1)] = int(match.group(2))
    output = _SENTINEL_RE.sub("", result.stdout).rstrip() + result.stderr
    return {
        "tests_passed": exits["PYTEST"] == 0,
        "lint_passed": exits["RUFF"] == 0,
        "output": output,
    }
