# 04: Event contract v2 (the seam)

Type this **together at H+0:30** into `frontend/src/contract/events.ts` + `case.ts` and
`backend/greenline/events/models.py`, then **freeze it at Gate G0**. Everything the UI renders is
derived from these events. Everything the backend does is reported through them.

Change rules after G0: **additive only** (new optional field or new variant), in **both languages
in one commit**, announced to your partner. Never rename, never remove.

## Shared enums

```ts
type NodeId = 'watcher' | 'triage' | 'reproducer' | 'analyst' | 'patcher' | 'critic' | 'reporter'
type FailureClass = 'flaky' | 'dependency' | 'env' | 'lint' | 'regression'
type RailId = 'protected_file' | 'diff_cap' | 'no_main_write' | 'no_creds' | 'egress_off'
type RunMode = 'live' | 'demo'
type BudgetPreset = 'normal' | 'tight'
type Outcome = 'reported' | 'escalated' | 'budget_exhausted' | 'error'
interface CheckResult { name: string; passed: boolean; detail?: string }
interface BudgetCaps { modelCalls: number; toolCalls: number; elapsedMs: number }
```

## `FailureCase` (static case metadata, `GET /api/cases`)

```ts
interface FailureCase {
  id: string            // display id, e.g. "0142"
  title: string         // e.g. "test_settlement_reconciles_at_eod"
  repo: string          // "acme/ledger-core" (cosmetic)
  branch: string        // e.g. "case/0142-flaky-settlement"
  cls: FailureClass     // ground truth, used ONLY by the scoreboard, never by the graph
  detectedAt: string    // ISO timestamp, display only
  ciRunUrl: string      // cosmetic
  beat: string          // one line: what this case demonstrates (shown in the case list tooltip)
}
```

`GET /api/cases` returns `CaseSummary[]`:

```ts
interface RunSummary { runId: string; outcome: Outcome; durationMs: number;
                       modelCalls: number; toolCalls: number; mode: RunMode }
interface CaseSummary extends FailureCase {
  lastRun: RunSummary | null   // last completed LIVE run of this case
  hasDemoRun: boolean          // demo_runs/<id>.json exists → "Recorded" mode is available
}
```

## `GreenlineEvent` (discriminated union on `type`)

`t` is **integer milliseconds since run start**, stamped by the backend emitter only.

```ts
type GreenlineEvent =
  | { t: number; type: 'run.start'; runId: string; caseId: string; mode: RunMode;
      model: string; budgetPreset: BudgetPreset; caps: BudgetCaps }
  | { t: number; type: 'node.enter'; node: NodeId }
  | { t: number; type: 'node.exit'; node: NodeId; durationMs: number;
      status: 'ok' | 'skip' | 'fail'; note?: string }
  | { t: number; type: 'log'; node: NodeId; level: 'info' | 'warn' | 'error'; text: string }
  | { t: number; type: 'evidence'; node: NodeId; kind: 'command' | 'observation' | 'citation';
      text: string; ref?: string }
  | { t: number; type: 'rerun.tick'; n: number; total: number; passed: boolean; durationMs: number }
  | { t: number; type: 'memory.hit'; caseRef: string; similarity: number; summary: string }
  | { t: number; type: 'verdict'; cls: FailureClass; confidence: number; rationale: string }
  | { t: number; type: 'patch.attempt'; n: number; file: string; diff: string;
      source: 'model' | 'tool'; result: 'green' | 'red' | 'vetoed' }
  | { t: number; type: 'critic.vote'; n: number; samples: ('approve' | 'reject')[];
      deterministic: CheckResult[]; approved: boolean }
  | { t: number; type: 'budget'; modelCalls: number; toolCalls: number; elapsedMs: number }
  | { t: number; type: 'guardrail'; rail: RailId; fired: boolean; note: string }
  | { t: number; type: 'report'; kind: 'pr' | 'escalation'; title: string; body: string;
      prUrl?: string; dryRun?: boolean }
  | { t: number; type: 'error'; node?: NodeId; message: string }
  | { t: number; type: 'done'; outcome: Outcome }
```

### Variant semantics

| Variant | Emitted by | Meaning / UI use |
|---|---|---|
| `run.start` | Run manager / demo player | **Always the first event, `t=0`.** It carries mode (RECORDED badge), model name (header chip) and budget caps (meter denominators). |
| `node.enter` / `node.exit` | Every node | Drives graph node status: idle → active → done (ok / skip / fail). `note` explains a skip, e.g. "warm memory hit on #0142". **Exactly one node is active at a time.** |
| `log` | Any node | **Narration line**: a plain-English "what's happening now" caption (level `info`), plus warnings. Emit one at the start of each meaningful step. |
| `evidence` | Watcher, Reproducer, Analyst, Patcher | The evidence feed. `command` = something run in the sandbox. `observation` = a measured fact. `citation` = a model rationale or a reference to a prior case. `ref` is a short tag (e.g. a test node id, `#0142`). |
| `rerun.tick` | Reproducer | One per sandbox rerun: progress `n/total` plus pass/fail. Drives the rerun grid. |
| `memory.hit` | Triage | A prior trace above threshold. Drives the "recalled #0142" callout and the skip edge on the graph. |
| `verdict` | Analyst | **At most one per run.** Class + evidence-derived confidence (0–1) + rationale. |
| `patch.attempt` | Patcher | One per attempt. `source: 'tool'` for ruff autofix, `'model'` for LLM-authored. `vetoed` = a guardrail blocked it before it was applied. |
| `critic.vote` | Critic | `n` = which patch attempt was judged. `samples` may be empty (deterministic reject, no LLM calls). |
| `budget` | Emitter, after every model or tool call | The current counters. Never emitted on a timer. |
| `guardrail` | Analyst (`protected_file`), Patcher (`diff_cap`, `no_main_write`), Run start (`no_creds`, `egress_off`) | One row per check. `fired: true` = hard stop; `fired: false` = "checked, clear". Always shown, not just on failure. |
| `report` | Reporter | Final artifact: a draft PR (title, body, `prUrl`, `dryRun`) or an escalation note. |
| `error` | Run manager / any node | Something unexpected broke, e.g. the model server died. Always followed by `done{outcome:'error'}`. |
| `done` | Reporter / run manager | **Always the last event, exactly once.** |

## Invariants (test these on both sides)

1. The first event is `run.start` with `t = 0`. The last event is `done`. There is exactly one `done`.
2. `t` is monotonic non-decreasing across the run. The emitter enforces `t = max(last_t, elapsed)`.
3. Every `node.enter` has a matching `node.exit` before the next `node.enter`, so at most one node
   is active.
4. At most one `verdict`. `budget_exhausted` and `error` runs may have none, and the UI must render
   "no verdict reached".
5. `rerun.tick.n` counts `1..total` in order.
6. `report` is emitted before `done` for outcomes `reported`, `escalated` and `budget_exhausted`.
   For `error` it is optional (the Reporter's template fallback should still try).
7. Ground-truth `FailureCase.cls` is **never** read by graph code. Only the scoreboard uses it.

## Wire format (SSE)

```
id: 17
data: {"t":12034,"type":"rerun.tick","n":4,"total":10,"passed":false,"durationMs":1830}

```

- One JSON event per `data:` line, with `id:` = persistence `seq` (0-based insertion order).
- A heartbeat comment `: ping` every 15 s while the run is idle-waiting (some proxies drop silent
  streams).
- The server closes the response after sending `done`. The client must **close its
  `EventSource` on `done`**, or the browser auto-reconnects and re-receives the whole run.
- JSON keys are camelCase (as above). Pydantic models use field names that match exactly, or
  `alias_generator=to_camel` with `populate_by_name=True` and `model_dump(by_alias=True)`.
  **Optional fields are omitted when absent** (`exclude_none=True`).

## `RunState` (frontend reducer output; pure function of the event list)

```ts
interface NodeRunState { status: 'idle' | 'active' | 'done'; outcome?: 'ok' | 'skip' | 'fail';
                         durationMs?: number; note?: string; enteredAt?: number }
interface RunState {
  runId: string | null; caseId: string | null; mode: RunMode | null; model: string | null
  budgetPreset: BudgetPreset | null; caps: BudgetCaps | null
  nodes: Record<NodeId, NodeRunState>
  activeNode: NodeId | null
  path: NodeId[]                       // nodes in the order entered (repeats allowed: patcher, critic, patcher…)
  narration: string | null             // latest log(info).text
  logs: { t: number; node: NodeId; level: 'info'|'warn'|'error'; text: string }[]
  evidence: { t: number; node: NodeId; kind: 'command'|'observation'|'citation'; text: string; ref?: string }[]
  rerun: { total: number; ticks: { n: number; passed: boolean; durationMs: number }[] } | null
  memoryHit: { caseRef: string; similarity: number; summary: string } | null
  verdict: { cls: FailureClass; confidence: number; rationale: string } | null
  patchAttempts: { n: number; file: string; diff: string; source: 'model'|'tool'; result: 'green'|'red'|'vetoed' }[]
  criticVotes: { n: number; samples: ('approve'|'reject')[]; deterministic: CheckResult[]; approved: boolean }[]
  guardrails: Record<RailId, { fired: boolean; note: string; t: number } | undefined>  // latest per rail
  budget: { modelCalls: number; toolCalls: number; elapsedMs: number }
  report: { kind: 'pr'|'escalation'; title: string; body: string; prUrl?: string; dryRun?: boolean } | null
  error: string | null
  outcome: Outcome | null
  lastT: number
}
```

The reducer is **pure**: no `Date.now()`, no randomness, no I/O. `EMPTY_STATE` has every node
idle, empty arrays, nulls, and zeroed counters. A `run.start` event **resets** to `EMPTY_STATE`
and then applies its fields, so reusing one store across runs is safe.

## Backend (Pydantic) notes

- Model each variant as its own `BaseModel` with `type: Literal['…']`, and combine them with
  `Annotated[Union[...], Field(discriminator='type')]` behind a `TypeAdapter`.
- The emitter validates every event against the adapter before persisting, so a malformed event
  fails loudly in development rather than silently in the UI.
- Write a round-trip test that builds one valid instance of every variant, serialises it and
  re-parses it. On the frontend, `reducer.test.ts` feeds the same JSON (export it once from Python
  into `frontend/src/state/__fixtures__/allVariants.json`; this is test data, not demo data).
