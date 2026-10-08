// Test data only: imported by *.test.ts, never by app code.
import type { GreenlineEvent, NodeId } from '../../contract/events'

type Draft = { type: GreenlineEvent['type']; t?: number } & Record<string, unknown>

function seq(drafts: Draft[]): GreenlineEvent[] {
  return drafts.map((d, i) => ({ ...d, t: d.t ?? i * 100 }) as unknown as GreenlineEvent)
}

const enter = (node: NodeId): Draft => ({ type: 'node.enter', node })
const exit = (node: NodeId, status: 'ok' | 'skip' | 'fail' = 'ok', note?: string): Draft => ({
  type: 'node.exit', node, durationMs: 100, status, ...(note !== undefined && { note }),
})
const log = (node: NodeId, text: string): Draft => ({ type: 'log', node, level: 'info', text })
const budget = (modelCalls: number, toolCalls: number): Draft => ({
  type: 'budget', modelCalls, toolCalls, elapsedMs: 1000,
})
const rail = (r: string, fired: boolean, note: string): Draft => ({ type: 'guardrail', rail: r, fired, note })
const start = (caseId: string, preset: 'normal' | 'tight' = 'normal'): Draft => ({
  type: 'run.start', t: 0, runId: `run-${caseId}`, caseId, mode: 'live', model: 'qwen3-8b',
  budgetPreset: preset,
  caps: preset === 'tight'
    ? { modelCalls: 4, toolCalls: 3, elapsedMs: 180000 }
    : { modelCalls: 16, toolCalls: 16, elapsedMs: 180000 },
})
const tick = (n: number, total: number, passed: boolean): Draft => ({
  type: 'rerun.tick', n, total, passed, durationMs: 1800,
})
const escalation: Draft = { type: 'report', kind: 'escalation', title: 'Escalated', body: 'Needs a human.' }

export const HERO_0142: GreenlineEvent[] = seq([
  start('0142'),
  rail('no_creds', false, 'no credentials in sandbox'),
  rail('egress_off', false, 'network disabled'),
  enter('watcher'),
  log('watcher', 'Pulling the red build'),
  { type: 'evidence', node: 'watcher', kind: 'command', text: 'pytest -q && ruff check .' },
  { type: 'evidence', node: 'watcher', kind: 'observation', text: '1 failed', ref: 'tests/test_settlement.py' },
  budget(0, 1),
  exit('watcher'),
  enter('triage'),
  log('triage', 'Classifying the failure'),
  budget(1, 1),
  exit('triage'),
  enter('reproducer'),
  log('reproducer', 'Re-running the failing test 10× in fresh containers'),
  ...Array.from({ length: 10 }, (_, i) => tick(i + 1, 10, (i + 1) % 3 !== 0)),
  { type: 'evidence', node: 'reproducer', kind: 'observation', text: '7 pass / 3 fail across 10 isolated reruns' },
  exit('reproducer'),
  enter('analyst'),
  { type: 'verdict', cls: 'flaky', confidence: 0.95, rationale: '7 pass / 3 fail across 10 reruns' },
  rail('protected_file', true, 'tests/** is protected'),
  exit('analyst'),
  enter('reporter'),
  escalation,
  exit('reporter'),
  { type: 'done', outcome: 'escalated' },
])

export const WARM_0144: GreenlineEvent[] = seq([
  start('0144'),
  enter('watcher'), exit('watcher'),
  enter('triage'),
  { type: 'memory.hit', caseRef: '0142', similarity: 0.91, summary: 'flaky settlement reconciliation' },
  exit('triage'),
  enter('reproducer'),
  exit('reproducer', 'skip', 'warm memory hit on #0142'),
  enter('analyst'),
  { type: 'verdict', cls: 'flaky', confidence: 0.91, rationale: 'same failure shape as #0142' },
  rail('protected_file', true, 'tests/** is protected'),
  exit('analyst'),
  enter('reporter'), escalation, exit('reporter'),
  { type: 'done', outcome: 'escalated' },
])

export const PATCH_LOOP_0137: GreenlineEvent[] = seq([
  start('0137'),
  enter('watcher'), exit('watcher'),
  enter('triage'), exit('triage'),
  enter('reproducer'), tick(1, 3, false), tick(2, 3, false), tick(3, 3, false), exit('reproducer'),
  enter('analyst'),
  { type: 'verdict', cls: 'regression', confidence: 0.92, rationale: 'all reruns fail the same way' },
  exit('analyst'),
  enter('patcher'),
  { type: 'patch.attempt', n: 1, file: 'src/rollup.py', diff: '-a\n+b\n', source: 'model', result: 'red' },
  exit('patcher'),
  enter('critic'),
  { type: 'critic.vote', n: 1, samples: [], deterministic: [{ name: 'tests_green', passed: false }], approved: false },
  exit('critic'),
  enter('patcher'),
  { type: 'patch.attempt', n: 2, file: 'src/rollup.py', diff: '-a\n+c\n', source: 'model', result: 'green' },
  exit('patcher'),
  enter('critic'),
  {
    type: 'critic.vote', n: 2, samples: ['approve', 'approve', 'approve'],
    deterministic: [{ name: 'tests_green', passed: true, detail: '3/3' }], approved: true,
  },
  rail('diff_cap', false, 'diff within cap'),
  rail('no_main_write', false, 'branch only'),
  exit('critic'),
  enter('reporter'),
  { type: 'report', kind: 'pr', title: 'Fix window boundary', body: 'Draft PR.', prUrl: 'https://example.test/pr/1', dryRun: true },
  exit('reporter'),
  { type: 'done', outcome: 'reported' },
])

export const TIGHT_0128: GreenlineEvent[] = seq([
  start('0128', 'tight'),
  enter('watcher'), exit('watcher'),
  enter('triage'), exit('triage'),
  enter('reproducer'), tick(1, 3, false), tick(2, 3, false), budget(2, 3), exit('reproducer'),
  enter('reporter'), escalation, exit('reporter'),
  { type: 'done', outcome: 'budget_exhausted' },
])

export const ERROR_RUN: GreenlineEvent[] = seq([
  start('0142'),
  enter('watcher'),
  log('watcher', 'Pulling the red build'),
  exit('watcher'),
  enter('triage'),
  { type: 'error', message: 'model server unreachable' },
  { type: 'done', outcome: 'error' },
])

export const ALL_SEQUENCES = { HERO_0142, WARM_0144, PATCH_LOOP_0137, TIGHT_0128, ERROR_RUN }
