# B18: real GitHub test repo — push red → Greenline auto-triages → real draft PR → Actions green

## Context
Today Greenline's "CI" is a stand-in: cases are pre-detected, the fixture repo `backend/fixtures/ledger-core`
is local-only, CI = pytest+ruff in the Docker sandbox, PRs are simulated (D13). The jury Q&A answer ("next is a
GitHub Actions trigger", docs/13) can become a live demo. Decisions taken with the user:
- Throwaway repo **`Pikathebot/ledger-core`, public**, with a GitHub Actions CI workflow.
- **Auto-triage:** Greenline polls GitHub; a red Actions run on a non-main branch becomes a case and a live run
  starts by itself; the open UI switches to it.
- **Real draft PR** on `reported`: push `fix/<id>` and open a draft PR **into the broken branch** (never
  main); Actions then runs on the PR and goes green.
- Auth: a **fine-grained PAT** scoped to that repo only (Contents RW, Pull requests RW, Actions read), pasted
  by the user into `backend\.env` as `GITHUB_TOKEN=` (gitignored; Claude never handles it).

Constraints: work on branch `feat/github-actions` (main is past G3 freeze; D-section of 02-DECISIONS allows
real PRs only after G3 and only on a throwaway repo). Everything is opt-in: with `GREENLINE_GITHUB_REPO`
unset, behaviour is exactly today's (DRY_RUN stays default true). Contract frozen: no change to
`events/models.py` / `frontend/src/contract`. Hard rule 7: never push main/master — enforced in code.
Sandbox unchanged (network off): all GitHub traffic is host-side. Builds on B17
(`extra_cases.json`, `reload_extra_cases`, `add_case.parse_failing_nodeid`). Commits start `B18:`.
Step 0: copy this plan to `docs/plans/B18-github-ci.md`.

## Design

### 1. The test repo (one-time script `backend/scripts/setup_github_repo.py`)
- Requires a seeded fixture repo. Adds `.github/workflows/ci.yml` to its `main` (commit): on `push` (all
  branches) and `pull_request`; ubuntu-latest, Python 3.12, `pip install pytest ruff`, then the same commands as
  `SandboxRunner.run_ci` (`pytest -q`, `ruff check .`, both run, fail if either fails).
- `gh repo create Pikathebot/ledger-core --public` if missing (uses the user's existing `gh` login, run by the
  user or with their OK), `git remote add origin https://github.com/Pikathebot/ledger-core.git`, push `main`
  only. The six built-in case branches are NOT pushed (keeps the repo's Actions page clean; they keep running
  locally as today).
- Idempotent; prints next steps (create the PAT, set env). `seed_repo.py --force` wipes the remote link →
  re-run this script.

### 2. Settings (`backend/greenline/config.py`)
`github_repo: str = ""` (env `GREENLINE_GITHUB_REPO`, e.g. `Pikathebot/ledger-core`), `github_poll_s: float = 10`.
Existing `github_token` (`GITHUB_TOKEN`). Feature on iff `github_repo` and `github_token` are set. Confirm the
settings class reads `backend/.env` (else document setting env vars in the uvicorn window / start.ps1).

### 3. GitHub client `backend/greenline/github/client.py` (httpx, host-side)
Thin async wrapper, base `https://api.github.com`, `Authorization: Bearer <token>`:
`failed_runs()` (`GET /repos/{r}/actions/runs?status=failure&per_page=10`), `failed_job_log(run_id)` (jobs list
→ first failed job → `GET /actions/jobs/{id}/logs`, follow redirect, keep last ~200 lines),
`create_draft_pr(head, base, title, body)` (`POST /pulls`, `draft: true`). No retries beyond one; errors logged.

### 4. Poller `backend/greenline/github/watch.py` (started in `main.py` lifespan when enabled; cancelled on shutdown)
Every `github_poll_s`:
- For each failed run with `head_branch` not in (`main`, `master`) and `fix/*` excluded, and run id not seen
  (seen ids kept in memory + skip runs older than backend start, so restarts don't replay history):
  - `git fetch origin <branch>:<branch>` in the fixture repo (host-side subprocess, `-c core.autocrlf=false`).
  - Case id: `7` + 3 digits from a counter persisted in `extra_cases.json` (7001, 7002 …: never collides with
    built-ins or B17's 0150/0151).
  - Entry via B17 shape: branch, title = head commit message first line, `failingTestNodeid` from
    `parse_failing_nodeid(log)` (move it from `scripts/add_case.py` to `greenline/graph/nodes/_util.py`, script
    imports it), `patchTarget` = first non-`tests/` file in `git diff --name-only main...<branch>`,
    `fallbackCiLog` = failing lines of the REAL Actions log, `ciRunUrl` = the run's `html_url` (extend
    `reload_extra_cases` to use an optional `ciRunUrl`), `cls` = `[cls:<class>]` tag in the commit message,
    default `regression` (ground truth is display-only; extras are off the scoreboard).
  - Save, `reload_extra_cases`, then `run_manager.start_run(id, "live", "normal")`. If a run is already active,
    queue it and start when idle (check each tick). Log every step (`logging`), never crash the loop.
- Rule 4 holds: config is only branch / nodeid / target / fallback log, derived from the real repo.

### 5. Real draft PR (`backend/greenline/vcs.py` + Patcher/Reporter)
- Patcher: when an attempt passes, also keep its `new_content` in the in-memory attempt dict
  (`state["patch_attempts"]`, not an event — contract untouched).
- Reporter (`graph/nodes/reporter.py:139`): pass `case_id`, case branch, target file and approved content to
  `open_draft_pr`.
- `open_draft_pr(..., dry_run)`: dry-run path unchanged. Real path (only if `dry_run=False` AND github
  configured, else fall back to dry-run with a warn log):
  1. Refuse unless head starts with `fix/` and base is not `main`/`master` (raise → Reporter's existing
     try/fallback). 2. Host-side in the fixture repo, without touching the working tree: `git worktree add`
     a temp dir at the case branch, create `fix/<id>`, write the file, commit, `git push origin fix/<id>`,
     remove the worktree. 3. `create_draft_pr(head=fix/<id>, base=<case branch>)`. Return the real number/url,
     `dry_run: False`.
  The UI already renders `prUrl` and the `dry_run` flag from the `report` event — the link becomes real.
- Activation: `GREENLINE_DRY_RUN=false` set only on the demo laptop, together with `GREENLINE_GITHUB_REPO`.
  The real path is used only when the case branch exists on origin (`git ls-remote --heads origin <branch>`),
  i.e. only for GitHub-detected cases. Built-in and B17 cases (local-only branches) stay dry-run, so the
  existing demo is unchanged even with DRY_RUN=false.

### 6. Frontend (small; Person A's area)
`frontend/src/app/bootstrap.ts`: every ~5 s, `useCaseStore.getState().refresh()` and, if no run is attached,
`api.activeRun()` → `selectCase` + `attach` (same code as the existing re-attach block; extract a helper). So
an auto-started run appears without F5. Unit test in the existing bootstrap/runReset test style.

### 7. Tests (`backend/tests/test_github_watch.py`, no network)
Fake GitHub client + temp git repos (bare "origin" + clone): failed run on `feature/x` → entry written with
id 7001, nodeid from a sample Actions log, `ciRunUrl` set, run started via a fake run manager; `main` and
`fix/*` runs ignored; same run id not processed twice; `open_draft_pr` real path refuses base `main` and
head not `fix/`, pushes `fix/7001` to the bare origin and calls `create_draft_pr` with base = case branch.

### 8. Runbook (end of `docs/plans/B18-github-ci.md`)
Setup once: `setup_github_repo.py`; create PAT (repo-only); `backend\.env`:
`GITHUB_TOKEN=…`, `GREENLINE_GITHUB_REPO=Pikathebot/ledger-core`, `GREENLINE_DRY_RUN=false`; restart backend.
On stage: clone/open `ledger-core`, `git switch -c fee-bug`, break `ledger_core/...` (or apply
`spare_cases/0150-fee-sign.diff`), `git commit`, `git push -u origin fee-bug` → Actions red (~30–60 s) →
Greenline picks it up within 10 s and runs → draft PR link in the Artifact pane → open it: Actions green on
the PR. Fallback if venue internet fails: unset the env vars, use B17 live add.

## Verification (run, not assumed)
1. `pytest` (backend) and `npx vitest run` + `npm run build` (frontend) green.
2. Feature off (no env): `run_batch.py --cases all --times 1 --mode demo` prints the six B15 outcomes.
3. Real end-to-end on this laptop: push a branch with the fee-sign bug to `Pikathebot/ledger-core`; Actions
   goes red; within one poll the UI (no F5) shows case 7001 and a live run; outcome `reported`; the PR link is
   a real draft PR with base = the bug branch; Actions on the PR is green. Screenshot it.
4. Nothing was pushed to `main` of either repo except the one-time workflow commit on ledger-core `main`
   (`git log origin/main` on ledger-core shows only seed + workflow commits).
5. Pushing a branch whose CI is green creates no case.
