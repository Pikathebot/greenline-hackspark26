# 02: Decisions (locked) and lessons learned

Everything here is **already decided**. Claude Code sessions at the event must not re-litigate
these. If one turns out to be impossible, raise it with your partner. Don't quietly substitute
something else.

## A. Locked decisions

| # | Topic | Decision |
|---|---|---|
| D1 | Scope | Full system: real backend (LangGraph + local model + Docker sandbox + memory + SSE) plus a redesigned frontend. Same product as the pitch deck. |
| D2 | Rules | Everything is coded at the event. This kit contains specs and contracts only. |
| D3 | Team split | **Person A, frontend** (Claude Design → React), on the **RTX 4060 laptop**. **Person B, backend** (API, graph, model, sandbox, fixture repo), on the **RTX 5070 laptop**. |
| D4 | Demo machine | The **RTX 5070 laptop** runs the full stack for the demo. The 4060 laptop runs a **full second copy** as a hot spare (same models, same images). Both GPUs are 8 GB, so the config is identical. |
| D5 | Model | **Qwen3-8B Q4_K_M GGUF** on `llama-server`, thinking **off**, grammar-constrained JSON output. Embeddings use **bge-small-en-v1.5** on a second, CPU-only `llama-server`. See `07-MODEL-RUNTIME.md`. |
| D6 | Replay | **Removed.** No scrubber, no rate control, no transport bar, no frontend fixture events, no `?replay`/`?live` flags, no recorded-run viewer. The UI has a single code path: start run → SSE stream → reducer → render. |
| D7 | Safety net | **Backend demo mode**: `POST /api/cases/{id}/runs?mode=demo` re-emits a *real, previously recorded* run through the same emitter/SSE path at its original pace. The UI shows a **RECORDED** badge whenever `mode=demo`. Never present a recorded run as live. |
| D8 | Frontend look | **Redesigned in Claude Design at the event.** Direction: agent-graph-centric "mission control", dark dev-tool aesthetic, projector-safe. See `09-DESIGN-BRIEF.md`. The old industrial-brutalist system is retired. |
| D9 | Contract | `GreenlineEvent` **v2** (`04-EVENT-CONTRACT.md`). Written together at H+0:30, frozen at Gate G0. After that, changes are additive only, made in both TS and Pydantic in the same commit, and announced to your partner. |
| D10 | Frontend state | A pure reducer `(RunState, GreenlineEvent) → RunState`. Components read derived state only. No component holds run data of its own. |
| D11 | Persistence | SQLite event log for every run: runs, events, memory traces. It feeds memory, the scoreboard, reconnect-after-refresh and demo mode. |
| D12 | Repo | One GitHub repo (created empty before the event, first commit at the event; D18), a monorepo: `backend/` and `frontend/`, with this kit copied in as `docs/`. |
| D13 | PRs | `GREENLINE_DRY_RUN=true` by default, so the PR is simulated (number and URL shown, marked dry-run). Real draft PRs are a stretch goal only. |
| D14 | Judging | The format is unknown, so plan for a **live demo + pitch**, with demo mode and a recorded backup video as fallbacks. See `13-DEMO-AND-PITCH.md`. |
| D15 | Setup | **Pre-staged.** Tools are installed and model weights downloaded *before* the event, on **both** laptops. The models go straight into the future working folder: **`D:\greenline\backend\models\`** (same path on both laptops; that folder holds nothing else until H+0). At H+0:15 that folder becomes the repo, and **`.gitignore` (excluding `backend/models/`) is the very first commit**. Only third-party, public artifacts are pre-staged: no project code, no built project images, no old databases. See `11-SETUP-CHECKLIST.md` §0. |
| D17 | Schedule | The real event schedule: start 11:00, **CP1 14:00**, selection 16:00, move 16:15, **evaluation 2 from 18:00**, **final 07:30** next day. Usable build time ≈ 20 h. The plan in `10-BUILD-PLAN.md` is re-timed with CP1 (G1) and CP2 (G2) as hard checkpoints. |
| D18 | Git | Remote is `Pikathebot/greenline-hackspark26`, private, created **empty** before the event; HTTPS auth via `gh`. Both commit to `main`, push after every ticket, tag every gate. See `14-GIT-WORKFLOW.md`. |
| D16 | Protected paths | `tests/**`, `**/migrations/**`, `**/*secret*`, `.github/workflows/**`. **Principle: Greenline never edits tests to make them pass.** This is why #0142 and #0144 escalate, and it is the restraint thesis of the demo. |

## B. What changed vs. the prototype, and why

| Area | Prototype | Event build | Why |
|---|---|---|---|
| Frontend sources | Scripted fixtures, SSE, and recorded-replay sources behind one interface | SSE only | You asked for no replay. One path means less code and fewer integration bugs. |
| Clock / fold | A virtual clock driving `events.filter(t ≤ now).reduce(...)` | Plain reducer over events as they arrive. Elapsed time is display-only. | Without scrubbing there's no need for a virtual clock. The reducer stays pure and testable. |
| Contract | v1, 13 variants | v2: adds `run.start` (mode, model, budget caps) and `error`; adds fields like `verdict.rationale`, `patch.attempt.file/source`, `evidence.node`, `memory.hit.summary`, `report.prUrl`; adds `done.outcome: 'error'` | The new UI needs caps for the budget meter, the RECORDED badge, error states and node attribution, and the prototype UI hard-coded these. |
| Watcher | Read a canned CI-log string | **Runs CI once in the sandbox** (`pytest` + `ruff`) and uses the real output | It makes triage reason over real output. Canned logs stay as a fallback only. |
| Rerun count | Fixed 8 for every class | **Adaptive**: flaky 10, dependency/regression/env 3, lint 0 (Reproducer skipped) | Real data: lint wasted 8 sandbox runs, and 8 runs of a 15% flake often show no failure at all. |
| Flake rate (#0142/#0144) | ~15% | **~30%** | P(all 10 pass) ≈ 2.8%, against 27% before. The hero beat now shows reliably. |
| Confidence | Self-reported by the model | **Computed from evidence** with a fixed rule table (`05-BACKEND-SPEC.md`) | Real data: the model answered 0.95 on *every* run, so the number was meaningless. |
| Lint fix | The LLM rewrote the whole file | **Tool-first**: `ruff check --fix` in the sandbox, with 0 model calls | Real data: both LLM lint attempts were red, and the run escalated after 13 model calls. |
| Regression patch context | Target file + CI log | **+ failing test file + the breaking commit's diff** (`git diff main...branch`) | Real data: both attempts red. The branch had also rewritten the docstring to match the bug, so the model couldn't infer the intended behaviour. |
| #0137 branch | Changed the operator **and** the docstring | Changes the operator only. The docstring still says "end is exclusive". | Realistic, because regressions rarely update the docs. It gives the model the signal. |
| Critic | Always 3 LLM samples | If the sandbox is red: deterministic reject, **no LLM calls**. If green: k=3 for model-authored diffs, k=1 for tool-authored. | Saves budget, and calling the model to judge a red patch is pointless. |
| Budget exhaustion | Claimed for #0128, never happened live | A **Tight budget** preset (per-run caps override, visible in the UI) makes it genuinely exhaust | Honest and demonstrable on stage. The default #0128 outcome is an "escalated: no safe fix". |
| Errors | Run marked `error` in the DB; the stream just closed | An `error` event plus `done{outcome:'error'}` | Every run still ends in exactly one `done`, and the UI shows why. |

## C. Lessons from the prototype: real data (32 runs, 8 Sep 2026, RTX 4060 laptop)

These are measured outcomes from the prototype's SQLite log. They are the reason for most of
section B.

| Case | Runs | Outcome (live) | Duration | Model calls | Sandbox runs | Notes |
|---|---|---|---|---|---|---|
| #0142 flaky | 25 | escalated (protected_file) | 25–40 s | 3 | 8 | Reruns often **8/8 pass**, so no flake was visible. Confidence always 0.95. |
| #0144 warm | 2 | escalated (protected_file) | 9–12 s | 3 | **0** | Memory hit worked; Reproducer skipped. The warm-path beat is real. |
| #0139 dependency | 1 | **reported** (green first try) | 39 s | 7 | 9 | The only case that produced a PR. |
| #0137 regression | 1 | escalated: both patches red | 54 s | 11 | 10 | Patcher lacked the breaking commit and the test file. |
| #0131 lint | 1 | escalated: both patches red | 61 s | 13 | 10 | The LLM couldn't do a mechanical lint fix. Now tool-first. |
| #0128 env | 2 | escalated (no safe fix) | 22–25 s | 3 | 8 | Never reached `budget_exhausted`. |

Other lessons that cost hours last time. Bake these in from minute one.

1. **Qwen3 thinking mode must be off** (`--reasoning-budget 0`). With it on, one structured call
   took *minutes*. With it off, a structured call averaged about 1.4 s.
2. **`--flash-attn on`, not bare `-fa`.** In recent llama.cpp builds a bare `-fa` swallows the next
   argument (`--jinja`) as its value.
3. **`--jinja` is required**, or `response_format: json_schema` can return prose.
4. **Flatten Pydantic schemas** (no nested models / `$ref`). The schema-to-grammar converter can 500
   on external refs.
5. **Docker Desktop (WSL2) sometimes fails to remove containers** under back-to-back load. Retry the
   removal once, log it, and never crash the node. Check `docker ps -a` before the demo.
6. **Git Bash rewrites `/work` into a Windows path** in manual `docker -v` commands. Use PowerShell,
   or `MSYS_NO_PATHCONV=1`. The backend uses the Docker SDK, so the backend itself is unaffected.
7. **Serialize model calls** behind one async lock: one GPU, one queue.
8. **Emitter is the only author of `t`**: `t = max(last_t, elapsed_ms)`. Out-of-order `t` broke the
   prototype's frontend.
9. **Subscribe to the live bus *before* reading persisted events** in the SSE handler, and dedupe by
   `seq`. Otherwise events emitted between the two steps are lost.
10. **Small models occasionally corrupt unrelated syntax** when rewriting a whole file. Run
    `ast.parse` on the result and give one corrective retry with the exact error.
11. **The Patcher needs neighbouring files**: the modules the target imports. Otherwise it guesses
    import names.
12. **Memory: store traces only from runs that actually reproduced.** A warm-skipped run shouldn't
    write its borrowed trace back. Exclude the same case ID from retrieval. Require the hit's class
    to match triage's class before skipping Reproducer. Similarity threshold **0.82** worked
    (bge-small, L2-normalised vectors, `cos = 1 − d²/2` from sqlite-vec's L2 distance).
13. **The pitch deck's numbers came from scripted fixtures**, not live runs. "Up to 20×", "62 s →
    11 s", "7 → 3 model calls" and the 88% / 43% / 3.4% scoreboard must be **re-measured** from
    event-build runs before you pitch. See `13-DEMO-AND-PITCH.md`.

## D. Things that are NOT decided (decide at the event, quickly)

- The exact visual tokens (palette, radius, type). Claude Design proposes, Person A picks. The
  constraints are in `09-DESIGN-BRIEF.md`.
- Light vs dark as the *presented* theme. Build both via tokens, then choose after a projector
  test (if you get access) or default to dark.
- Whether to attempt real draft PRs (D13 stretch). Only after Gate G3, and only on a throwaway
  GitHub repo.
- Rerun concurrency: sequential vs 2–3 containers at once. Measure at ticket B7 and pick whatever
  keeps #0142 under ~40 s without making the rerun grid unreadable.
