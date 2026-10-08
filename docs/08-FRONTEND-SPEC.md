# 08: Frontend spec (Person A)

**Stack:** React 19 + TypeScript + Vite, Tailwind CSS v4 (CSS-first `@theme` tokens), Zustand
(stores), Framer Motion (state transitions only), **@xyflow/react** (React Flow) for the agent
graph, Vitest for the reducer tests. Fonts are **self-hosted via `@fontsource/*`**, because venue
internet is unreliable and the demo must have zero network dependencies besides the local backend.

**No router.** One screen plus overlays. Desktop only (target 1920×1080; must not break at 1440×900).

The visual design comes from Claude Design (`09-DESIGN-BRIEF.md`). This file defines **what is on
screen and how it behaves**. Claude Design defines **how it looks**.

---

## 1. What is removed (do not build)

Transport bar, scrubber, playhead, rate buttons (1×/2×/8×), virtual clock, scripted fixture events,
recorded-run viewer, `?replay`, `?live`, `?plain` (unless the new design adds texture). Live SSE is
the only data path.

## 2. Data flow

```
GET /api/cases ──► caseStore (static list + lastRun summaries)
GET /api/health (poll 3 s) ──► healthStore
user clicks Run ──► POST /api/cases/{id}/runs {mode, budget} ──► {runId}
                 ──► stream.ts opens EventSource(/api/runs/{runId}/stream)
                 ──► each message: runStore.receive(event) → events.push(e); state = reducer(state, e)
                 ──► on `done`: close EventSource, refetch /api/cases (lastRun updates)
components ──► read runStore.state (RunState, see 04) + uiStore (selection, overlays, presets)
```

- `state/reducer.ts`: **pure** `(RunState, GreenlineEvent) → RunState` with `EMPTY_STATE`. A
  `run.start` resets. Unit-tested with Vitest against the all-variants JSON plus a hand-built
  sequence per invariant in `04-EVENT-CONTRACT.md`.
- `state/runStore.ts` (Zustand): `{ status: 'idle'|'starting'|'streaming'|'done'|'error',
  runId, events: GreenlineEvent[], state: RunState, startRun(caseId, opts), receive(e), reset() }`.
  Keep `events` for debugging only, and render from `state`.
- `state/uiStore.ts`: `selectedCaseId`, `budgetPreset: 'normal'|'tight'`, `mode: 'live'|'demo'`,
  `scoreboardOpen`, `focusedEvidence` (for verdict↔evidence linking).
- `api/stream.ts`: wraps `EventSource`.
  - `onmessage` parses JSON and calls `receive`.
  - On `done`, call `close()` **immediately**, or the browser auto-reconnects and replays.
  - `onerror` before `done`: set `connection: 'reconnecting'`, close, reopen after 1 s, and on
    reopen **reset state and let the server resend the full prefix**. Reducing from scratch is
    simpler than seq-tracking. Give up after 5 tries and show the error state.
- On app load, `GET /api/runs/active`. If a run is in progress (e.g. after a refresh), re-attach to
  its stream.
- Elapsed time display: a `requestAnimationFrame` (or 250 ms interval) ticker from the moment
  `run.start` is received, **display only**. When `done` arrives, show the authoritative
  `done.t`. Never put wall-clock time into `RunState`.

## 3. Screen: information architecture

```
┌ TOP BAR ───────────────────────────────────────────────────────────────────────────────┐
│ Greenline logo · model chip "Qwen3-8B · local" · health chips (Model · Memory · Sandbox) │
│                         [LIVE ● / RECORDED]   elapsed 00:27   budget meters   [Scoreboard]│
├ CASE LIST ─────────┬ AGENT GRAPH (hero) ───────────────────────┬ VERDICT & ACTION ───────┤
│ 6 cases:           │ 7 nodes, fixed layout, edges incl.         │ Verdict: class word,     │
│  id · class chip   │ critic→patcher loop + triage→analyst       │  confidence bar,         │
│  title (1 line)    │ "skip" highlight; active node pulses;      │  rationale (2–3 lines)   │
│  last outcome pill │ done nodes show duration & ok/skip/fail;   ├──────────────────────────┤
│  [Run] on hover    │ path taken highlighted                     │ Guardrails: 5 rows,      │
│                    ├────────────────────────────────────────────┤  fired = alarm style     │
│ Run options:       │ NARRATION: plain-English caption of now    ├──────────────────────────┤
│  Budget Normal|Tight│ EVIDENCE FEED (scrolls): commands,         │ Artifact: Draft PR (diff │
│  Mode Live|Recorded│  observations, citations; RERUN GRID inline │  + body) or Escalation   │
│                    │  (10 cells, pass/fail, fill in live)       │  note                    │
│                    │ MEMORY CALLOUT / COST COMPARE (when hit)   │ Run summary card on done │
└────────────────────┴────────────────────────────────────────────┴──────────────────────────┘
Overlay: SCOREBOARD (S). Toasts/banners: backend unreachable, run error, reconnecting.
```

Column widths (starting point): left 300 px, center flexible, right 420 px. Only the evidence feed
and case list scroll. No page scroll.

## 4. Components and their data (all read `RunState` unless noted)

| Component | Data | Behaviour |
|---|---|---|
| `TopBar` | `state.model`, `mode`, `caps`, `budget`, `outcome`; healthStore | **LIVE** indicator (pulsing dot) while streaming a live run. **RECORDED** badge for `mode=demo`, clearly visible and never hidden. Three budget meters (model calls, sandbox runs, time) as `value/cap`, turning to the alarm colour at ≥ 80% and when `budget_exhausted`. |
| `HealthChips` | `/api/health` | Model / Memory / Sandbox: green when reachable, red otherwise. Tooltip has details. If the backend itself is unreachable, show a full-width banner "Backend offline: start uvicorn on :8000". |
| `CaseList` + `CaseRow` | caseStore; `selectedCaseId` | Id, class chip, title, `lastRun.outcome` pill + duration. Click selects. `Run` button / Enter starts. Disabled while a run is streaming (one GPU). |
| `RunOptions` | uiStore | Budget: Normal / **Tight** (tooltip: "caps model calls at 4 and sandbox runs at 3, to demonstrate budget exhaustion"). Mode: Live / Recorded (Recorded is disabled when `hasDemoRun` is false for the case). |
| `AgentGraph` | `nodes`, `activeNode`, `path`, `memoryHit`, `patchAttempts` | React Flow with **hard-coded positions** (no auto-layout). Nodes: idle (muted), active (accent + pulse), done-ok, done-skip (dashed + "skipped" label + note tooltip), done-fail. Edges animate when traversed. **Loop edge** critic→patcher lights up on retry with an attempt counter "2/2". **Skip edge**: when Reproducer is skipped, draw the triage→analyst bypass as highlighted. A **guardrail barrier** icon on the analyst→patcher edge when `protected_file` fired. Each node shows a duration after exit. Zoom and pan disabled: it's a diagram, not an editor. |
| `Narration` | `narration`, `activeNode` | One large, readable line: "Re-running the failing test 10× in fresh containers…". It's for the non-technical judges. |
| `EvidenceFeed` | `evidence`, `rerun` | Newest at the bottom, auto-scroll unless the user scrolled up. Icons per kind: command `›`, observation `•`, citation `“`. Node tag on each line. The **RerunGrid** renders inline once `rerun` exists: `total` cells that fill as ticks arrive (pass/fail colour), plus the summary "7 pass / 3 fail". |
| `MemoryCallout` | `memoryHit`, caseStore.lastRun of `caseRef` | "Recalled #0142 (similarity 0.91): same failure shape. Skipping reproduction." Plus a **cost comparison** once `done`: this run vs #0142's last live run (time, model calls, sandbox runs), shown as two short bars per metric. |
| `VerdictCard` | `verdict`, `outcome` | Class word (large), confidence bar + percentage, rationale. Before the verdict: placeholder "Gathering evidence…". If the run ended without a verdict: "No verdict reached: budget exhausted" / "…: error". |
| `GuardrailList` | `guardrails` | All five rails, always listed. Unchecked = muted "not checked yet". Clear = ✓ + note. **Fired = alarm style + "BLOCKED" + note**. This is the restraint moment, so it needs to be visually unmissable. |
| `ArtifactPane` | `report`, `patchAttempts`, `criticVotes` | PR: title, "draft · dry-run" tag, `prUrl`, a diff viewer (red/green lines, monospace) of the last green attempt, critic votes (✓✓✓ / deterministic checks), body. Escalation: an "Escalated to a human" header, the body, and the reason chip (guardrail / budget / no safe fix / error). Earlier attempts collapse under "Attempt 1: red, rejected by Critic". **Download .md** button (key `E`) in the pane header once `report` exists and `done` has arrived: builds a Markdown file client-side from `RunState` (case, outcome, verdict + confidence, guardrails, rerun summary, evidence, report body + diff), header says RECORDED for `mode=demo`. No backend or contract change. |
| `RunSummary` | `outcome`, `budget`, `done.t` | Appears on `done`: outcome (big), duration, model calls, sandbox runs. This doubles as the "end card" during the demo. |
| `ScoreboardOverlay` | `GET /api/scoreboard` (fetch on open) | Metric tiles (triage accuracy, patch success, escalation rate, median time to verdict, p95 duration, warm vs cold). A **confusion matrix** (5×5, actual × predicted). A per-case table. Always show `sampleSize` ("from 18 live runs"). Show `notMeasured` metrics as "not measured", never invented. |
| `ErrorBanner` / `Toasts` | runStore.status, connection | Reconnecting, run error (shows the `error.message`), and 409 "a run is already in progress". |

## 5. Interactions and keyboard

| Key | Action |
|---|---|
| `1`–`6` | Select case (in demo order: 0142, 0144, 0139, 0131, 0137, 0128) |
| `Enter` / `R` | Run the selected case with the current options |
| `T` | Toggle Normal / Tight budget |
| `D` | Toggle Live / Recorded mode |
| `S` | Toggle scoreboard |
| `E` | Download the report as `.md` (only when a report exists) |
| `Esc` | Close overlay |

Everything must also be reachable by mouse, in case the person presenting isn't the person who
built it.

## 6. States to design and implement (Claude Design should mock every one)

1. Cold start: backend offline (banner), nothing selected.
2. Idle: backend healthy, case selected, nothing run yet.
3. Running: Watcher/Triage active, early evidence.
4. Running: Reproducer mid-way (rerun grid 6/10).
5. Memory hit: Reproducer skipped, callout visible (#0144).
6. Verdict + **guardrail fired** → escalation (#0142, the hero frame).
7. Patch loop: attempt 1 red, Critic reject, attempt 2 running (#0137).
8. Reported: green patch, Critic approved, draft PR artifact (#0139).
9. Budget exhausted (#0128 Tight): meters at cap, "no verdict reached", escalation.
10. Error mid-run: model server died, error banner, `done: error`.
11. RECORDED (demo mode) badge on any running state.
12. Scoreboard overlay.

## 7. Quality bar

- Readable from the back of a room: body text ≥ 15 px, narration ≥ 20 px, verdict word ≥ 48 px.
  Test at 1920×1080 at 100% and 125% Windows scaling.
- No layout shift as events stream in: reserve space for the verdict, rerun grid and artifact.
- Motion only for state changes (node activation, edge traversal, evidence insert, a guardrail
  firing). Respect `prefers-reduced-motion`.
- `npm run build` is clean, with zero TypeScript errors. `npm run lint` (oxlint or ESLint) is clean.
- Components never import from `api/` directly except through stores and hooks, and there is no
  fixture data under `src/` except reducer test JSON.
