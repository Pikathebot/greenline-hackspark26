# B17: add a failure case live (jury ask) + a pre-staged spare case

## Context
If the jury says "add a new case and show it", we currently can't: the six cases are hard-coded in
`backend/greenline/graph/cases.py` (+ `scripts/seed_repo.py`), so adding one means editing Python,
reseeding and restarting uvicorn. Goal:
- **Option 1, live add:** break something in the fixture repo (or apply a diff), run one command, press
  F5, the new case is in the UI and runs live through the real graph. No restart, no code edit.
- **Option 2, spare case:** a pre-written, pre-rehearsed defect (#0150, fee sign bug, regression) added
  through the same command, plus a recording as fallback.

Constraints: hard rule 4 (case config = branch, failing test node id, patch target, fallback CI log only;
nothing about outcomes in graph code). The scoreboard/deck numbers (112 runs, six cases) must not move.
Contract is frozen: no change to `FailureCase`/`events/models.py`; `cls` must be one of the existing
`FailureClass` values. User agreed: implemented from this laptop (Person A), user gives Person B a heads-up
before we touch `backend/` files.

Step 0: copy this plan to `docs/plans/B17-live-case.md` (repo convention). Commits start with `B17:`.

## Design
Extra cases live in a runtime JSON file `backend/fixtures/extra_cases.json` (gitignored), merged into the
existing dicts **in place** on demand. The graph already only reads `state["config"]`
(`graph/run.py:187`) and the reproducer uses `triage_cls`, so no graph change is needed. The UI already
builds the list from `GET /api/cases` (`frontend/src/state/caseStore.ts`), refreshed on load and after
each run, so F5 shows the new case. No frontend change.

### 1. `backend/greenline/graph/cases.py`
- After `FAILURE_CASES`: `BUILTIN_CASE_IDS: tuple[str, ...] = tuple(FAILURE_CASES)`.
- `reload_extra_cases(path: Path) -> list[str]`: drop every non-builtin key from `CASE_CONFIGS` and
  `FAILURE_CASES`, then (if the file exists) load a JSON list of
  `{id, branch, title, cls, failingTestNodeid, patchTarget, fallbackCiLog, beat, detectedAt}`.
  Skip (with a log warning) entries whose id is builtin or not `^\d{4}$`. Build `CaseConfig` +
  `FailureCase(repo="acme/ledger-core", ci_run_url=f"https://ci.example/acme/ledger-core/runs/{int(id)}")`.
  Mutate the dicts in place (other modules import them by name). Return loaded ids.
- `load/save_extra_case_entries(path)` small helpers shared with the script (write with `newline="\n"`).

### 2. `backend/greenline/config.py`
Add `extra_cases_path()` next to `fixture_repo_path()`: `fixture_repo_path().parent / "extra_cases.json"`.
Add `backend/fixtures/extra_cases.json` to root `.gitignore`.

### 3. `backend/greenline/api/cases.py`
Call `reload_extra_cases(settings.extra_cases_path())` at the top of `list_cases` and `start_run`.

### 4. Keep numbers stable: `backend/greenline/api/scoreboard.py`, `demo/export.py`, `scripts/run_batch.py`
- `compute_scoreboard` (line 91): filter `runs` to `row["case_id"] in BUILTIN_CASE_IDS`; the `perCase` loop
  (line 149) iterates `BUILTIN_CASE_IDS`.
- `export_all`: iterate `BUILTIN_CASE_IDS`. `scripts/export_demo_runs.py`: add `--case <id>` that calls
  `reload_extra_cases` then `export_case` (for the 0150 recording).
- `run_batch.py`: call `reload_extra_cases` at start; `--cases all` stays `BUILTIN_CASE_IDS` (the B15
  acceptance must still print six outcomes). `run_case.py`: call `reload_extra_cases` before the lookup.

### 5. New `backend/scripts/add_case.py` (argparse subcommands, run from `backend\`)
Uses `get_settings().fixture_repo_path()`, `SandboxRunner.run_ci(branch)` (as `run_case.py` does) and
`first_failing_line` from `greenline/graph/nodes/_util.py`. Git via `subprocess` with
`-c core.autocrlf=false`.
- `new <id> --slug <s>`: refuse builtin/existing id or a dirty fixture tree; `git checkout main`,
  `git checkout -b case/<id>-<slug>`; print the folder to edit (`backend\fixtures\ledger-core`).
- `finish <id> --title "..." --cls <class> [--beat "..."]`: must be on `case/<id>-*`; `git add -A`,
  commit `case <id>: <title>`; `run_ci`. If it **passes**, print "CI is green, nothing to triage" and
  leave the branch checked out (exit 1). Else derive:
  - `failingTestNodeid`: first output line starting `FAILED ` or `ERROR `, the token after it with any
    ` - ...` suffix stripped; `None` if no pytest failure (ruff-only = lint).
  - `patchTarget`: first file in `git diff --name-only main...HEAD` not under `tests/`; `None` if only
    tests changed.
  - `fallbackCiLog`: up to the first two failing lines. `detectedAt`: now, UTC ISO.
  `git checkout main`, upsert the JSON entry, print the derived config and "Added #<id>. Press F5."
- `from-patch <id> --slug <s> --patch <file> --title --cls [--beat]`: `new` + `git apply` + `finish`.
- `list`, `remove <id>` (drop JSON entry + `git branch -D`).
Put the nodeid parser in a function so it can be unit-tested.

### 6. Spare case #0150 (option 2)
- `backend/scripts/spare_cases/0150-fee-sign.diff`, **generated with git** (not hand-written): on a
  temp branch from `main` add
  - `ledger_core/fees.py`: docstring `"""Payout fees."""`, `net_after_fee(amount, rate)` returning
    `round(amount * (1 + rate), 2)` (bug: should be `1 - rate`), with docstring "Amount the merchant
    receives after the processing fee."
  - `tests/test_fees.py`: `test_net_after_fee_deducts_fee` asserting `net_after_fee(100.0, 0.03) == 97.0`.
  Ruff-clean, LF endings; `git diff main` into the file, delete the temp branch.
- `backend/scripts/add_spare_case.ps1`: one line wrapping
  `add_case.py from-patch 0150 --slug fee-sign --patch scripts\spare_cases\0150-fee-sign.diff --title "test_net_after_fee_deducts_fee" --cls regression --beat "Added live: new case, real triage"`.
- Rehearse: 3 live runs of 0150 (expect `reported`), then `export_demo_runs.py --case 0150` →
  commit `backend/demo_runs/0150.json` as the RECORDED fallback. Afterwards `add_case.py remove 0150`
  so the UI shows six cases until the jury asks. (Those live runs don't touch the scoreboard: step 4.)

### 7. Tests: `backend/tests/test_extra_cases.py`
reload adds a case from a tmp JSON, a second reload with the entry removed drops it, builtin id is
rejected, builtins untouched; nodeid parser on `FAILED tests/x.py::t - AssertionError`,
`ERROR tests/x.py - ImportError`, and ruff-only output (→ None); scoreboard ignores runs of a non-builtin
case (use the existing scoreboard test fixtures/pattern).

### 8. Stage runbook (section at the end of `docs/plans/B17-live-case.md`)
- Jury invents a bug: `python scripts\add_case.py new 0151 --slug <x>` → edit a file in
  `backend\fixtures\ledger-core` in VS Code with them → `python scripts\add_case.py finish 0151 --title
  ... --cls ...` → F5 → click #0151 → Run live.
- Safe path: `.\scripts\add_spare_case.ps1` → F5 → run #0150 live; if live fails, switch to RECORDED.
- Note: `seed_repo.py --force` wipes extra branches; re-run the add command afterwards.

## Verification (run, not assumed)
1. `pytest` in `backend\` all green (existing + new).
2. Note `GET /api/scoreboard` sampleSize, then `.\scripts\add_spare_case.ps1`; `GET /api/cases` returns 7
   with #0150, without restarting uvicorn.
3. `run_batch.py --cases 0150 --times 1` → `reported`; `GET /api/scoreboard` sampleSize unchanged.
4. Jury flow: `add_case.py new 0151 --slug window`, change `end` comparison in `ledger_core/rollup.py`
   to `<=`, `finish 0151 --title test_reconcile_window_boundary --cls regression`; printed config has
   nodeid `tests/test_rollup.py::test_reconcile_window_boundary` and target `ledger_core/rollup.py`.
   F5 in the UI shows #0151; run it live in the browser to `done`. Then `remove 0151`.
5. `run_batch.py --cases all --times 1 --mode demo` still prints exactly the six B15 outcomes.
6. `finish` on a branch with no real breakage reports "CI is green" and adds nothing.

## Stage runbook (what to type when the jury says "add a case")
All from `D:\greenline\backend`, backend and UI already running (`start.bat`). No restart needed.

**A. Jury invents the bug (real live add)**
```
.venv\Scripts\python.exe scripts\add_case.py new 0151 --slug anything
```
Open `backend\fixtures\ledger-core` in VS Code, break a file with them (a test must go red), then:
```
.venv\Scripts\python.exe scripts\add_case.py finish 0151 --title "what failed" --cls regression
```
It runs CI in the sandbox, prints the failing test and patch target, registers the case. F5 in the UI, click
#0151, Run live. `--cls` is one of flaky, dependency, regression, lint, env (display/ground truth only).

**B. Safe path (pre-staged)**
```
.\scripts\add_spare_case.ps1
```
F5, click #0150 (fee sign bug), Run live. If live misbehaves, run it in demo mode: it replays
`demo_runs\0150.json` (recorded, labelled RECORDED).

**Cleanup:** `add_case.py remove 0151` (and `remove 0150`). Extra cases never count on the scoreboard or
in `run_batch.py --cases all`.

Notes: `seed_repo.py --force` wipes extra branches (extra_cases.json then points at missing branches; run
`remove` for each). Live runs of extra cases write memory traces on this laptop only.
