# 05: Backend spec (Person B)

Stack: **Python 3.12, FastAPI, uvicorn, Pydantic v2 + pydantic-settings, LangGraph, httpx,
docker (SDK), sqlite-vec, PyGithub (stretch), pytest + pytest-asyncio.** Run every command
from `backend/` as the working directory.

---

## 1. API

| Endpoint | Method | Request | Response |
|---|---|---|---|
| `/api/health` | GET | (none) | `{modelServer:{url,reachable,model}, embedServer:{url,reachable}, docker:{reachable, sandboxImage:bool}, fixtureRepo:{seeded:bool}, gpuVramFreeMb:number|null}`. Each check is independent, so one failure never fails the whole endpoint. Timeout 1.5 s per check. |
| `/api/cases` | GET | (none) | `CaseSummary[]` (`04-EVENT-CONTRACT.md`): `FailureCase` + `lastRun` (last *completed live* run) + `hasDemoRun` |
| `/api/cases/{id}/runs` | POST | JSON `{mode?: 'live'\|'demo' = 'live', budget?: 'normal'\|'tight' = 'normal'}` | `{runId}`. 404 for an unknown case. 409 if a run is already active (one GPU, so one run at a time). 404 for `mode=demo` when `demo_runs/{id}.json` is missing. |
| `/api/runs/{runId}/stream` | GET | (none) | SSE (see contract wire format). Replays the persisted prefix, then tails live. |
| `/api/runs/active` | GET | (none) | `{runId, caseId} \| null`, so a refreshed browser can re-attach |
| `/api/scoreboard` | GET | (none) | See §10 |
| `/api/admin/reset-memory` | POST | (none) | Clears memory traces, used to show a cold #0142 on stage |
| `/api/admin/export-demo-runs` | POST | (none) | Exports the best completed live run per case to `demo_runs/` (same logic as the script) |

CORS is only needed when the frontend isn't using the Vite proxy. Create the SQLite schema on
startup (FastAPI lifespan).

## 2. Persistence (`persistence/db.py`, stdlib `sqlite3`)

```sql
runs(run_id TEXT PK, case_id TEXT, mode TEXT, budget_preset TEXT, status TEXT  -- running|complete|error
     , outcome TEXT, started_at TEXT, ended_at TEXT, model_calls INT, tool_calls INT, duration_ms INT)
events(run_id TEXT, seq INT, t INT, type TEXT, payload TEXT  -- JSON, verbatim event
     , PRIMARY KEY(run_id, seq))
memory_traces(trace_id TEXT PK, run_id TEXT, case_id TEXT, cls TEXT, summary TEXT, vec_rowid INT)
memory_vectors  -- sqlite-vec virtual table: vec0(embedding float[384])
```

- Use one connection with `check_same_thread=False` and WAL mode. Every write goes through a
  small helper that commits. Use idempotent `CREATE TABLE IF NOT EXISTS`, and no migration
  framework.
- Load `sqlite-vec` via `sqlite_vec.load(conn)` (`enable_load_extension(True)` before,
  `False` after). Windows Python from python.org supports extension loading. If it doesn't, fall
  back to computing cosine similarity in Python over a plain BLOB column (it's only a few dozen
  vectors).
- On `done`, update `runs` with outcome, counters and duration (the summary columns feed
  `/api/cases` `lastRun` and the scoreboard).

## 3. Events: models, emitter, bus

**`events/models.py`** mirrors `04-EVENT-CONTRACT.md` exactly (discriminated union +
`TypeAdapter`).

**`RunEmitter(run_id, caps)`** is the only place `t` is created. Responsibilities:

- `emit(event_dict)`: stamp `t = max(last_t, elapsed_ms)`, validate via the adapter, assign
  `seq`, persist, then publish to the bus. Return the payload.
- Counters: `model_calls`, `tool_calls`, `elapsed_ms`. `record_model_call()` and
  `record_tool_call()` increment them and then emit a `budget` event.
- Helpers to keep node code short: `enter(node)`, `exit(node, status, note=None)` (computes
  `durationMs` from its own enter timestamp), `narrate(node, text)` (a `log` at level `info`),
  `evidence(node, kind, text, ref=None)`.

**`events/bus.py`** is a per-run topic of `asyncio.Queue`s: `subscribe`, `unsubscribe`, `publish`,
`close(run_id)` (pushes a `None` sentinel).

**SSE handler** (`api/runs.py`), in this order:

1. Look up the run; return 404 if missing.
2. If it is running, **subscribe first**.
3. Send the persisted events (`id: seq`).
4. Tail the queue and skip `seq <= last_sent`. Stop on the sentinel.
5. Send a `: ping` every 15 s of silence (`asyncio.wait_for` on `queue.get()` with timeout).
6. Always unsubscribe in `finally`.

Response headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`.

## 4. Run manager (`graph/run.py`)

- One active run at a time (module-level lock / `active_run_id`).
- `start_run(case_id, mode, budget)`: insert the `runs` row, then create a task:
  - `live`: emit `run.start`, then emit `guardrail` rows for `no_creds` and `egress_off` (asserted
    from the sandbox's construction kwargs, see §7), then invoke the graph.
  - `demo`: hand off to the demo player (§11).
- Wrap the whole task in `try/except Exception`. On error, emit `error{message}`, try the Reporter's
  **template** fallback (no model call), then emit `done{outcome:'error'}`, mark the run `error` and
  close the bus. **Every run ends in exactly one `done`, whatever happens.**
- Budget presets map to caps from config (`normal` / `tight`). The caps go into `run.start.caps`
  and the emitter.

## 5. LLM client (`llm/client.py`)

- `complete(system, user, schema: type[BaseModel], temperature) -> BaseModel`, async via httpx,
  posting to `{MODEL_URL}/v1/chat/completions` with
  `response_format = {type:'json_schema', json_schema:{name, schema: schema.model_json_schema(), strict:true}}`.
- **One global `asyncio.Lock`** around the HTTP call (one GPU, one queue).
- Retry up to 3× on `httpx.HTTPError`, JSON/validation errors, and missing keys. Timeout 120 s.
  After 3 failures, raise `ModelUnavailable` (the run manager turns it into `error`).
- Budget accounting happens in the **calling node** (`emitter.record_model_call()` after each
  successful call), because the client is shared and run-agnostic.
- `llm/schemas.py` holds flat models only, with no nested `BaseModel` fields:

| Schema | Fields |
|---|---|
| `TriageOutput` | `cls: FailureClass`, `rationale: str` |
| `AnalystOutput` | `cls: FailureClass`, `rationale: str`, `evidence_strength: Literal['weak','moderate','strong']` (shown in logs only; confidence comes from §8) |
| `PatchOutput` | `new_content: str` (the **full corrected file**, not a diff), `summary: str` |
| `CriticOutput` | `decision: Literal['approve','reject']`, `rationale: str` |
| `ReportOutput` | `title: str`, `body: str` |

The Patcher returns the full file content because an 8B model writes broken unified diffs. The
backend computes the real diff with `difflib.unified_diff` (`a/<path>`, `b/<path>`).

## 6. Prompts (`llm/prompts/*.md`): intent to encode

Write each prompt fresh at the event. It must cover:

- **triage**: the CI log is for a Python repo (pytest + ruff). Give the five class definitions
  verbatim from `01-PRODUCT.md`. Output the class and a 1–2 sentence rationale citing specific log
  lines.
- **analyst**: input is triage's class, the CI log, the evidence summary (rerun distribution with
  a sample failure tail, *or* the memory hit, *or* "lint: static analysis only"). Confirm or revise
  the class. The rationale must cite concrete evidence (counts, test ids, error names). Give a
  qualitative evidence strength.
- **patcher** (the most important one):
  - Inputs: the target file's full content, the CI log, the diagnosis, the **failing test file's
    content**, the **breaking commit's diff** (`git diff main...<branch>`), the content of local
    modules the target imports, and, on a retry, the previous diff plus the Critic's reason.
  - "Smallest change that fixes the diagnosed defect. Do not refactor, reformat or touch unrelated
    lines. Keep docstrings and comments."
  - "Never invent names that aren't visible in the provided files."
  - "Treat the failing test as the specification. You may not edit tests."
  - "If the class is `env`, do not invent defaults or hardcode values. Return the file unchanged
    and explain."
  - Include one short worked example: a regression where the breaking diff flips `<` to `<=`, and
    the fix flips it back.
- **critic**: input is the diff, the diagnosis, the deterministic check results (all green when
  the Critic is called). Reject if the diff goes beyond the diagnosis, touches unrelated code, or
  masks the problem (hardcoding, skipping or deleting assertions). Approve only a minimal, correct
  fix. Rationale in one sentence.
- **reporter**: plain text, 3–6 sentences, cites test names, file paths and rerun counts. A PR
  body for `reported`. An escalation note for the others that says explicitly *why* there's no
  patch (guardrail / budget / no safe fix / error), addressed to a human.

## 7. Sandbox (`sandbox/runner.py`, `sandbox/Dockerfile`)

**Image:** `python:3.12-slim` + `pip install pytest ruff`, tagged `greenline-sandbox:latest`. This
is the only network use the sandbox ever has, at build time. Build it during setup with
`docker build -t greenline-sandbox:latest greenline/sandbox`.

**Per run (never reuse a container):**

1. Make a scratch copy of the branch: `git archive <branch>` into a temp dir and untar it. There is
   no `.git` inside, so nothing can touch the fixture repo's history.
2. Optionally overwrite one file (for patch verification).
3. `containers.run(image, command, network_disabled=True, environment={}, mem_limit='1g',
   pids_limit=256, nano_cpus=1_000_000_000, volumes={scratch: {'bind':'/work','mode':'rw'}},
   working_dir='/work', detach=True)`.
4. `container.wait(timeout=30)`. On timeout, kill and set `exit_code=-1`.
5. Collect stdout and stderr separately.
6. `finally`: `container.remove(force=True)` with one retry, **log but never raise**. Then
   `rmtree(scratch)`.

**API (sync; nodes call it via `asyncio.to_thread`):**

| Method | Command | Use |
|---|---|---|
| `run_ci(branch)` | `pytest -q` then `ruff check .` (both always run, output concatenated, exit = first non-zero) | Watcher (1 tool call) |
| `run_test(branch, nodeid)` | `python -m pytest -q <nodeid> -p no:cacheprovider` | Reproducer reruns |
| `ruff_fix(branch, path)` | `ruff check --fix <path>` then print the file content | Patcher, lint (tool-first) |
| `run_patched(branch, path, content)` | Same as `run_ci` but with the file overwritten. Returns `{tests_passed, lint_passed, output}` | Patcher verification |
| `read_file(branch, path)` | `git show <branch>:<path>` (host-side, no container) | Patcher context |
| `breaking_diff(branch)` | `git diff main...<branch>` (host-side) | Patcher context |
| `construction_kwargs()` | Returns the dict used above | `no_creds` / `egress_off` assertion at run start |

`TestResult = {passed, exit_code, stdout, stderr, duration_ms, command}`.

Windows notes: the Docker SDK talks to Docker Desktop directly, so there are no path-mangling
issues. Temp dirs under `%TEMP%` bind-mount fine with the WSL2 backend. Use `newline='\n'` when
writing files.

## 8. Evidence-derived confidence (`graph/confidence.py`)

A pure function `confidence(cls, reruns, memory_hit, ci) -> float`, **not** the model's own number.

| Final class | Evidence | Confidence |
|---|---|---|
| flaky | reruns mixed (0 < fails < N) | `0.80 + 0.15 * min(1, N/10)` |
| flaky | memory hit (Reproducer skipped) | `min(0.95, similarity)` |
| flaky | all reruns pass | 0.50 (flake not observed) |
| flaky | all reruns fail | 0.30 (contradicts flaky) |
| dependency / regression | all N reruns fail with the same error type | 0.92 |
| dependency / regression | mixed | 0.50 |
| env | all reruns fail with `KeyError`/missing-config signature | 0.90 |
| lint | ruff fails, tests pass in the Watcher CI run | 0.97 |
| any | anything else | 0.60 |

Show this table in the pitch if asked: "confidence is computed from evidence; the model's
self-reported confidence was 0.95 on every run, so we stopped trusting it".

## 9. The agent graph (`graph/`)

`GreenlineState` is a `TypedDict` that carries live objects (`emitter`, `sandbox`, `llm`, `caps`)
plus data fields. Do **not** use a LangGraph checkpointer, because our persistence is the event log.

Every node is wrapped in a decorator that catches `BudgetExhausted` and sets
`state.budget_exhausted=True`. Every conditional edge checks that flag first and routes to
`reporter`. Call `check_budget(state)` **before** each model or tool call. It raises when the next
call would exceed a cap or when elapsed time is at or above the cap.

Static per-case config (`graph/cases.py`) is the **only** case-specific knowledge the graph gets.
It holds the branch, the failing test node id, the patch target, and a short canned CI log used
**only** as a Watcher fallback when the sandbox CI run fails for infrastructure reasons (always
flagged with a `log(warn)`):

| Case | Branch | Failing test node id (for reruns) | Patch target file |
|---|---|---|---|
| 0142 | `case/0142-flaky-settlement` | `tests/test_settlement.py::test_settlement_reconciles_at_eod` | `tests/test_settlement.py` |
| 0144 | `case/0144-flaky-repeat` | `tests/test_payout.py::test_payout_reconciles_at_eod` | `tests/test_payout.py` |
| 0139 | `case/0139-dep-pin` | `tests/test_http_client.py` | `ledger_core/http_client.py` |
| 0137 | `case/0137-regression` | `tests/test_rollup.py::test_reconcile_window_boundary` | `ledger_core/rollup.py` |
| 0131 | `case/0131-lint` | (none) | `ledger_core/routes.py` |
| 0128 | `case/0128-env-drift` | `tests/test_env.py::test_region_config_present` | `None` (no safe fix) |

Never put expected verdicts, outcomes or event sequences in graph code. Outcomes must emerge from
the real run.

### Nodes

**watcher** (0 model, 1 tool)
- `narrate("Pulling the red build and re-running CI once in a sealed sandbox")`.
- `sandbox.run_ci(branch)` → `record_tool_call()`, then `evidence(command, "pytest -q && ruff check .")`
  and `evidence(observation, "<first failing line>")`.
- `ci_log` = the last ~60 lines of the output. If the sandbox fails for infrastructure reasons,
  use the canned log in `cases.py`, `log(warn, "using cached CI log")`, and **say so**.
- Edge → triage.

**triage** (1 model)
- LLM `TriageOutput` → `evidence(citation, rationale)`.
- Memory: embed `"{test name}: {rationale}"`, query top-3, drop hits from the same `case_id`, keep
  `similarity ≥ 0.82` **and** `hit.cls == triage.cls`. Emit `memory.hit` for the best hit.
  Embedding errors are swallowed, because memory is an optimisation.
- Edge → reproducer, **always**. The Reproducer decides to skip itself, so the UI shows the node
  as *skipped* (with a reason) rather than never visited.

**reproducer** (0 model, N tools)
- When skipped (memory hit or lint): `enter`, then `exit(status='skip', note='warm memory hit on #0142' | 'static analysis, nothing to rerun')`.
- N by triage class: `flaky` 10, `dependency`/`regression`/`env` 3.
- `narrate("Re-running the failing test 10× in fresh containers")`. Run `run_test(nodeid)` N times,
  sequentially or with `RERUN_CONCURRENCY`, and emit ticks in completion order, numbered 1..N.
  Each run gets `check_budget` and `record_tool_call`, then `rerun.tick`.
- `evidence(observation, "7 pass / 3 fail across 10 isolated reruns")`.
- Edge → analyst.

**analyst** (1 model)
- Build context (distribution with a sample failure tail, or memory summary, or lint note). LLM
  `AnalystOutput`, then compute confidence (§8), then emit `verdict{cls, confidence, rationale}`
  and `evidence(citation, rationale)`.
- Store a memory trace **only if Reproducer actually ran** (store `cls`).
- Guardrail: if the target is `None`, emit `evidence(observation, "no safe automated fix for env
  failures — escalating")` and set `blocked`. Otherwise run `protected_file([target])`, emit it, and
  set `blocked = fired`.
- Edge: blocked → reporter; else → patcher.

**patcher** (0–2 model, 1–2 tool)
- `attempt_n = len(attempts) + 1`.
- If `verdict.cls == 'lint'`: run `sandbox.ruff_fix` to get the candidate (`source='tool'`,
  **0 model calls**).
- Otherwise call the LLM with the full context from §6 (`source='model'`). If the result fails
  `ast.parse`, do one corrective call with the exact error.
- Compute the diff, then emit `guardrail` rows for `diff_cap` (80 changed lines) and
  `no_main_write` (target branch = `fix/<caseId>`, never main/master). Also re-check
  `protected_file` on the diff's paths.
- If any rail fires, emit `patch.attempt(result='vetoed')` and go to reporter.
- If the diff is empty, treat it as "no change proposed" and escalate.
- Otherwise `run_patched` → `record_tool_call()` → `patch.attempt(result = green if tests AND lint pass else red)`.
- Edge → critic (or reporter on veto/empty).

**critic** (0–3 model)
- Deterministic checks: `tests_green`, `lint_green`, `diff_within_cap`, `no_protected_paths`.
- If any check fails, emit `critic.vote(samples=[], approved=false)` with no LLM calls.
- Otherwise take k samples (3 for a `model` diff, 1 for a `tool` diff) at temperature 0.4.
  `approved = majority approve`.
- Edge: approved → reporter. Not approved and attempts < 2 → patcher (the next prompt includes the
  rejection reason). Otherwise → reporter.

**reporter** (1 model, template fallback)
- Outcome: `budget_exhausted` if the flag is set. `reported` if the last critic vote approved.
  Otherwise `escalated`.
- LLM `ReportOutput` from a context summary. If the model fails, use a deterministic template.
  The reporter must never fail.
- For `reported`, `vcs.open_draft_pr(...)`. Under `DRY_RUN` this returns a fake number and URL with
  `dryRun=true`.
- Emit `report`, `exit`, then `done{outcome}`.
- Note: the reporter's own model call happens **even after budget exhaustion**. It's exempt from
  the cap (document it: "the report is always written").

### Expected live shapes (targets for verification, NOT hardcoded)

| Case | Path | ≈ model calls | ≈ sandbox runs | Outcome |
|---|---|---|---|---|
| 0142 | W → T → R(10) → A ⛔ → Rep | 3 | 11 | escalated |
| 0144 | W → T(hit) → R(skip) → A ⛔ → Rep | 3 | 1 | escalated |
| 0139 | W → T → R(3) → A → P → C → Rep | 3 + 1 + 3 = 7 | 5 | reported |
| 0131 | W → T → R(skip) → A → P(tool) → C(k=1) → Rep | 4 | 2 | reported |
| 0137 | W → T → R(3) → A → P → C (→ P → C) → Rep | 7–11 | 5–6 | reported (hopefully) |
| 0128 | W → T → R(3) → A ⛔(no safe fix) → Rep | 3 | 4 | escalated |
| 0128 tight | W → T → R(budget hit after 2 reruns) → Rep | 2 | 3 | budget_exhausted |

## 10. Scoreboard (`api/scoreboard.py`)

Computed from completed **live** runs only. Demo runs are excluded.

```
{ sampleSize, metrics: { triageAccuracy, patchSuccessRate, escalationRate, medianTimeToVerdictMs,
  p95DurationMs, avgModelCalls, avgToolCalls, warmVsCold: {coldMs, warmMs, coldToolCalls, warmToolCalls} },
  matrix: { [actual in FailureClass]: { [predicted]: count } },
  perCase: [{caseId, runs, lastOutcome, medianDurationMs}],
  notMeasured: ['falsePrRate', 'humanBaseline'] , note: string }
```

- `triageAccuracy` compares `verdict.cls` with the case's ground-truth `cls`.
- `patchSuccessRate` = reported ÷ runs with a non-vetoed patch attempt.
- `warmVsCold` = 0142 median vs 0144 median.
- **Never invent numbers.** Metrics that need human feedback go in `notMeasured`.
- To build real history, run `scripts/run_batch.py --cases all --times 3` overnight (about 6 × 3 ×
  45 s ≈ 15 min). Reset memory between 0142 and 0144 on alternate passes so you measure both cold
  and warm.

## 11. Demo mode (`demo/player.py`, `scripts/export_demo_runs.py`)

- **Export:** for each case, pick the best completed live run. That means outcome as expected for
  the case and, for 0142, a mixed rerun distribution. Write its events as JSON to
  `demo_runs/<caseId>.json` and commit them, since they're real outputs produced at the event.
- **Play:** create a new run row (`mode='demo'`), emit `run.start` with `mode:'demo'`, then re-emit
  every stored event **except** the original `run.start`, sleeping so the original relative timing
  holds. Events go through the emitter, so `t` is restamped but preserves the gaps. Then `done`.
- The demo player never calls the model, Docker or memory. It must work with only uvicorn running.
- **Before real runs exist (11:00 → G1 at 13:30):** hand-write `demo_runs/0142.json` with about 40 plausible
  events so the frontend has a stream to build against. Replace it with a real export as soon as
  0142 runs live (by G2). It is a temporary dev artifact, so delete it from history if it's never
  replaced.

## 12. Tests (`backend/tests/`), all fast (no GPU, no Docker) unless marked `slow`

1. Contract round-trip: one instance of every variant, serialised and parsed.
2. Emitter: out-of-order `t` gets clamped; `seq` is strictly increasing; a `budget` event follows
   each `record_*`.
3. Guardrails: each rail fires and stays clear on crafted inputs, including `tests/**` and
   `fix/0142` vs `main`.
4. Confidence: one assertion per table row.
5. Graph termination: run the graph with a **fake LLM** (canned schema instances) and a **fake
   sandbox** (scripted pass/fail) over all six cases plus tight 0128. Assert exactly one `done`,
   first event `run.start`, `t` monotonic, enter/exit balanced. This is the most valuable test.
6. SSE: start a demo run, read the stream with `httpx`, and assert it ends at `done`.
7. `slow`: real sandbox, where 0142 × 10 reruns gives a mixed result; real model, where TriageOutput
   round-trips 20/20.
