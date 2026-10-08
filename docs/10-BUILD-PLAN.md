# 10: Build plan (re-timed to the real event schedule)

**H+0 = 11:00 on 8 Oct = the moment building is allowed to start.** Person **A** = frontend
(RTX 4060 laptop). Person **B** = backend (RTX 5070 laptop). Clock times are the real ones.

## The real event schedule (D17)

| Clock | H+ | What happens | What it means for us |
|---|---|---|---|
| 8 Oct 11:00 | 0:00 | Hackathon starts | Env check, repo, contract |
| 14:00 | 3:00 | **Checkpoint 1 (CP1)** | The one that decides selection. Must *look* and *sound* finished. |
| 16:00 | 5:00 | Selection announcement | Stop, commit, push (15:45) |
| 16:15 | 5:15 | **Move to another venue** | Pack, travel, re-establish power, network, GPU, Docker. Budget ~45 min of lost build time. |
| 18:00 onwards | 7:00+ | **Evaluation 2 (CP2)**, probably rolling | Live #0142 if at all possible; the demo must stay up for hours |
| 9 Oct 07:30 | 20:30 | **Final evaluation** | Real deadline: everything is frozen by 06:50 (H+19:50) |

So the usable build time is about **20 hours, not 24**, and ~45 min of it is the venue move.
Ask the organizers once: **is there a code-freeze or submission time before 07:30?** If yes,
shift everything after G3 earlier by that amount.

**Priorities, in order:** (1) CP1 is a *selection* gate, so the polished designed UI animating a
demo-mode run beats any backend depth at 14:00. (2) Stay selected: CP2 needs live #0142 (stretch)
or an honest RECORDED run plus whatever live parts work. (3) The final needs all six cases,
numbers, rehearsal.

## Gates (both people stop and check together for 10 minutes)

| Gate | Clock | H+ | Definition of done |
|---|---|---|---|
| **G0: Contract frozen** | 12:30 | 1:30 | Repo exists on GitHub with `docs/` + `CLAUDE.md`. Contract typed in TS **and** Pydantic. Backend round-trip test green, frontend reducer tests green. `check_env` green on both laptops: tools, Docker, `llama-server` serving the pre-staged model. Tag `g0`. |
| **G1 = CP1 ready** | 13:30 | 2:30 | From A's laptop, the designed frontend starts a **demo-mode** run of #0142 on B's backend. Events stream over SSE, the reducer's `RunState` renders in the designed AgentGraph and TopBar (RECORDED badge visible). Tag `cp1`. 13:30–14:00 is rehearsal of the CP1 pitch, not build time. |
| **G2 = CP2 ready** | 17:45 | 6:45 | #0142 runs **live** (real Watcher CI run, real model, real sandbox reruns with a mixed result, verdict, `protected_file` fires, escalation) in the designed components. **Stretch.** If not live by 17:30, CP2 is demo-mode + the live pieces that work, said honestly. Tag `cp2`. |
| **G3: Feature freeze** | 00:30 (9 Oct) | 13:30 | All six cases run live with the expected outcomes (`05-BACKEND-SPEC.md` §9 table), plus #0128 Tight → `budget_exhausted`. The 12 UI states in `08-FRONTEND-SPEC.md` §6 reachable. `pytest` + `npm run build` clean. **No new features after this. Bug fixes only.** Tag `g3`. |
| **G4: Demo-ready** | 05:00 | 18:00 | Golden runs exported to `demo_runs/` for all six cases. Scoreboard history built (≥ 3 live runs per case). The spare laptop runs the full stack. Deck numbers re-measured. Backup video recorded (05:45 at the latest). Tag `g4`. |
| **v1.0: Hands off** | 06:50 | 19:50 | Final commit, tag `v1.0`, pushed. After this: only machine prep (`11-SETUP-CHECKLIST.md` §6). |

If a gate slips by more than 1 hour, **apply the cut list**. Don't push the next gate.
**CP1 and the venue move are fixed points. They never slip.**

## Schedule at a glance

| Clock (H+) | Person A: frontend | Person B: backend |
|---|---|---|
| 11:00 (0:00) | Env check (A0). Paste the design prompt into Claude Design **immediately**. | Env check; start both `llama-server`s (B0) |
| 11:15 (0:15) | Repo: B makes the local repo, `.gitignore` first, links the remote; A joins (`14-GIT-WORKFLOW.md` §3) | (together) |
| 11:30 (0:30) | **Contract hour together** (A1/B1); Claude Design iterates in the background | **Contract hour together** |
| 12:30 (1:30) | **G0** · lock the design by 12:45 (A2, ~1.5 h total) | FastAPI skeleton: db, emitter, bus, SSE, run manager (B2) |
| 12:45 (1:45) | Scaffold app shell, stores, stream client, AgentGraph + TopBar (A3, A4) | Demo player + hand-written `demo_runs/0142.json` (B3) |
| 13:30 (2:30) | **G1 = CP1 ready**, tag `cp1` | **G1 = CP1 ready** |
| 13:30 (2:30) | CP1 pitch rehearsal (both) | CP1 pitch rehearsal (both) |
| **14:00 (3:00)** | **CHECKPOINT 1** | **CHECKPOINT 1** |
| 14:30 (3:30) | Narration, EvidenceFeed, RerunGrid (A4 rest, A5) | Fixture repo seeder (B4) → sandbox image and runner (B5) |
| 15:45 (4:45) | **Commit + push everything. Shut services down. Pack.** | **Same** |
| 16:00 (5:00) | Selection announcement | Selection announcement |
| 16:15–17:00 | Move. At the new venue: power, Wi-Fi/hotspot, new IP in `.env.local`, `check_env` | Move. Docker Desktop up, `llama-server`s up, `check_env` |
| 17:00 (6:00) | Wire VerdictCard + GuardrailList + escalation artifact to live data (A5) | llama smoke + LLM client (B6) → graph core with #0142 live (B7) |
| 17:45 (6:45) | **G2 = CP2 ready** (stretch), tag `cp2` | **G2 = CP2 ready** |
| **18:00 (7:00)** | **EVALUATION 2** (demo from the `cp2` worktree) | **EVALUATION 2** |
| between judges | PR artifact, diff viewer, patch loop on graph, memory callout (A6) | Fake-LLM termination tests (B8) → patcher + guardrails + critic (B9) |
| ~20:30 (9:30) | Case list, run options, keyboard, end card (A7); scoreboard overlay (A8) | Memory (B10) → budget presets (B11) → scoreboard API, export, batch (B12) |
| ~23:00 (12:00) | Error, offline, reconnect, RECORDED, 409 states (A9) | Bug fixing across all six cases (B13) |
| **00:30 (13:30)** | **G3: freeze**, tag `g3` | **G3: freeze** |
| 00:30 (13:30) | Polish, light theme, scaling (A10) until 02:00, then **sleep 02:00 → 05:00** | Start the **batch runs** (B14), **sleep 01:00 → 04:00** |
| 04:00 (17:00) | (asleep) | Wake: export golden runs, spare laptop, compute deck numbers (B15) |
| 05:00 (18:00) | Wake: deck with measured numbers (A11). **G4**, tag `g4` | **G4** |
| 05:30 (18:30) | Backup video together (B16) | Backup video together |
| 06:00 (19:00) | **Rehearsal #1** (stopwatch) | **Rehearsal #1** |
| 06:30 (19:30) | Fix only what rehearsal broke | Fix only what rehearsal broke |
| **06:50 (19:50)** | **Hands off.** Final commit, tag `v1.0`, push | same |
| 07:00 (20:00) | Machine prep (`11` §6), pre-demo checklist | same |
| **07:30 (20:30)** | **FINAL EVALUATION** | **FINAL EVALUATION** |

**Sleep honestly.** Someone awake at 07:30 after 20 hours with no sleep demos worse than someone
with 3 hours. If evaluation 2 runs late, shift your sleep, not the freeze. Eat at 14:30 (before
the move), 20:00 and 02:00. Take 10 min away from the screen every 3–4 hours.

## Between checkpoints, the demo must stay alive

Evaluation 2 may run for hours while you still want to build. Keep two copies of the app:

- **`D:\greenline\`** (branch `main`): where you work. May be broken at any moment.
- **`D:\greenline-demo\`**: a git worktree pinned to the last good tag (`cp1`, then `cp2`, ...).
  Run the demo from here. Commands in `14-GIT-WORKFLOW.md` §6. Only re-pin it when the new tag is
  rehearsed and green.

## Pitch per checkpoint

See `13-DEMO-AND-PITCH.md` ("Checkpoint pitches"). CP1 is a 2-minute story + designed UI on a
RECORDED run + one live model call as proof. CP2 is #0142 live (or an honest RECORDED run). The
final is the full 3/6-minute script.

---

## Track B: Backend tickets

| # | Ticket | Acceptance (observable) |
|---|---|---|
| B0 | Env check: Docker Desktop running, models present in `D:\greenline\backend\models\`, both `llama-server`s started from the pre-staged models (tools were installed before the event) | `docker info` OK; `:8080/health` and `:8081/health` OK |
| B1 | Contract in Pydantic (`events/models.py`) + `FailureCase` + round-trip test; export `allVariants.json` for A | `pytest tests/test_contract.py` green; JSON handed to A |
| B2 | `config.py`, `db.py`, emitter, bus, `/api/health`, `/api/cases`, `POST runs`, SSE stream, run manager (one active run, try/except → `error` + `done`) | `curl -N .../stream` shows `id:`/`data:` lines; a run that raises still ends with `done{error}` |
| B3 | Demo player + hand-written `demo_runs/0142.json` (~40 events, realistic timing over ~30 s) | `POST runs {mode:'demo'}` streams paced events and closes after `done` |
| B4 | `scripts/seed_repo.py` per `06-FIXTURE-REPO-SPEC.md` | Branches exist; main green |
| B5 | Sandbox Dockerfile + `runner.py` (all methods in §7) + `scripts/run_case.py <id> --ci-only` | The acceptance table in `06` matches, checking the **reason** too; 0142 ×10 shows mixed results; `docker ps -a` shows no leftovers |
| B6 | `llama-server.ps1` running; `llm/client.py` + schemas | 20/20 `TriageOutput` round-trips, average under 3 s |
| B7 | Graph: state, build, budget, confidence; nodes watcher, triage (no memory yet), reproducer, analyst, reporter | **#0142 live** ends `escalated` with `protected_file` fired; first event `run.start`, exactly one `done`. **This is G2 / CP2 (17:45).** |
| B8 | Termination test with fake LLM + fake sandbox over all cases | Green; asserts every invariant in `04` |
| B9 | Patcher (tool-first lint, model path with full context, `ast` retry), `diff_cap`/`no_main_write`, critic (deterministic-first, then k samples), loop to 2 attempts, `vcs` dry-run | #0131 → `reported` with `source:'tool'`; #0139 → `reported`; #0137 → `reported` (a Critic loop is acceptable) |
| B10 | Embedding server + `memory/` + triage hit + analyst store + `/api/admin/reset-memory` | After a 0142 run, **0144 skips Reproducer**, similarity ≥ 0.82, with far fewer sandbox runs |
| B11 | Budget presets (`normal`/`tight`) through POST, `run.start.caps`, the emitter | #0128 normal → `escalated` (no safe fix); #0128 tight → `budget_exhausted` with a report |
| B12 | `/api/cases` `lastRun`, `/api/scoreboard`, `export_demo_runs.py`, `run_batch.py`, `/api/runs/active` | Scoreboard JSON matches DB counts; export writes six JSON files |
| B13 | Six-case live pass, fix whatever breaks | **G3** |
| B14 | `run_batch.py --times 3` (with memory resets so cold and warm both get measured) | ≥ 18 live runs in the DB |
| B15 | Export golden runs; set up the 4060 as a spare (seed, image, models, `.env`); pull the deck numbers from `/api/scoreboard` | The demo mode works on **both** laptops |
| B16 | Record the backup video together (OBS / Xbox Game Bar, 1080p) | A file on two machines + a USB drive |

**If the patcher is fighting you (B9):** get #0139 green first (simplest), then #0131 (tool), then
#0137. If #0137 still won't go green after about 45 minutes, keep it as an honest escalation case.
The Critic loop is still visible if attempt 1 was red.

## Track A: Frontend tickets

| # | Ticket | Acceptance (observable) |
|---|---|---|
| A0 | Env check (tools pre-installed); **paste the design prompt into Claude Design immediately** | First design frames generating |
| A1 | Contract in TS (`src/contract/`), `reducer.ts` + `EMPTY_STATE`, Vitest tests from `allVariants.json` + invariant sequences | `npx vitest run` green |
| A2 | Finish Claude Design iterations (**time-boxed, lock by 12:45**); lock; export screens + tokens to `frontend/design/` and `src/design/tokens.css` | 12 state frames saved (or the most important 8) |
| A3 | Vite + React + TS + Tailwind v4 + fonts + tokens; layout grid; stores; `api/client.ts`, `stream.ts`, health polling; a debug drawer showing `RunState` JSON | **G1** demo run renders through the stores |
| A4 | `AgentGraph` (React Flow, fixed positions, node states, skip edge, loop edge, guardrail barrier), `Narration`, `TopBar` + meters + LIVE/RECORDED | Demo #0142 animates node by node; the barrier appears on `protected_file` |
| A5 | `EvidenceFeed` + `RerunGrid`, `VerdictCard`, `GuardrailList`, `ArtifactPane` (escalation) | **G2** live #0142 looks like design frame 4 |
| A6 | `ArtifactPane` PR mode with diff viewer + critic votes + collapsed earlier attempts; loop counter on graph; `MemoryCallout` + cost comparison | #0139 and #0144 match their frames |
| A7 | `CaseList` with `lastRun`, `RunOptions` (Tight, Recorded), keyboard map, `RunSummary` end card | All keys work; mouse-only also works |
| A8 | `ScoreboardOverlay`: tiles, 5×5 matrix, per-case table, sample size, "not measured" | Renders real `/api/scoreboard` |
| A9 | Offline banner, reconnecting, error run, 409 toast, re-attach to an active run on load | Kill uvicorn mid-run, then restart: the UI recovers or explains itself |
| A10 | Polish against every state frame; light theme toggle (hidden key `L`); 125% scaling; reduced motion; `npm run build` clean | Build clean; no layout shift during a run |
| A11 | Pitch deck refresh with real numbers (`13-DEMO-AND-PITCH.md`) | Deck claims ⊆ measured facts |

## Working agreements

- **Commit and push after every ticket** (`B7: graph core — 0142 live escalates`); rules in
  `14-GIT-WORKFLOW.md`. You're two people on separate folders (`backend/` vs `frontend/`), so conflicts are rare.
  Only `docs/` and the contract files are shared.
- **Contract changes after G0:** additive only, both languages, one commit, and say it out loud.
- **Never fake an outcome to make a gate.** If a case doesn't produce its beat, say so at the gate
  and decide together: fix it, cut it, or reframe the beat honestly.
- **Ask before you install heavy dependencies.** The venue network is a shared resource.
- **Keep the 5070 laptop free for model work from G3 onward.** Don't run games, Chrome with HW
  acceleration, or a second model on it.

## Cut list (apply in this order when behind)

0. **CP2 fallback:** #0142 not live by 17:30 → show demo mode (RECORDED) plus the live pieces that work, and say so.
1. Real GitHub draft PRs (already a stretch; dry-run stays).
2. Light theme. Scoreboard per-case table (keep tiles + matrix).
3. Verdict ↔ evidence hover linking. Cost-comparison bars (keep the text callout).
4. Critic k=3 → k=1 everywhere (saves time per run).
5. Rerun concurrency experiments (stay sequential).
6. #0137 as a "reported" beat: keep it as escalation if the patcher can't do it.
7. The scoreboard overlay entirely: replace it with the RunSummary end cards plus a single "This
   session: N runs" line.
8. **Never cut:** live #0142 with a mixed rerun grid and the guardrail block, #0144 memory skip,
   #0139 PR, demo mode, error states, the RECORDED badge.
