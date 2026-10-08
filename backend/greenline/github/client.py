"""Thin synchronous GitHub REST client (host-side only; the sandbox has no network).

Async callers wrap these in asyncio.to_thread, like the sandbox runner.
`transport` lets tests inject an httpx.MockTransport.
"""

from __future__ import annotations

import re

import httpx

API = "https://api.github.com"
_TS = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ?", re.MULTILINE)
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def clean_log(raw: str, tail: int = 200) -> str:
    """Drop Actions' per-line timestamps and colour codes; keep the last `tail` lines."""
    text = _ANSI.sub("", _TS.sub("", raw))
    return "\n".join(text.splitlines()[-tail:])


class GitHubClient:
    def __init__(self, repo: str, token: str, transport: httpx.BaseTransport | None = None) -> None:
        self.repo = repo
        self._http = httpx.Client(
            base_url=API,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20,
            follow_redirects=True,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def failed_runs(self) -> list[dict]:
        resp = self._http.get(
            f"/repos/{self.repo}/actions/runs", params={"status": "failure", "per_page": 10}
        )
        resp.raise_for_status()
        return resp.json().get("workflow_runs", [])

    def failed_job_log(self, run_id: int) -> str:
        resp = self._http.get(f"/repos/{self.repo}/actions/runs/{run_id}/jobs")
        resp.raise_for_status()
        jobs = [j for j in resp.json().get("jobs", []) if j.get("conclusion") == "failure"]
        if not jobs:
            return ""
        log = self._http.get(f"/repos/{self.repo}/actions/jobs/{jobs[0]['id']}/logs")
        log.raise_for_status()
        return clean_log(log.text)

    def create_draft_pr(self, head: str, base: str, title: str, body: str) -> dict:
        resp = self._http.post(
            f"/repos/{self.repo}/pulls",
            json={"title": title, "body": body, "head": head, "base": base, "draft": True},
        )
        resp.raise_for_status()
        data = resp.json()
        return {"number": data["number"], "url": data["html_url"]}
