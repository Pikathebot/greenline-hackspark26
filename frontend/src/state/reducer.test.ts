import { describe, expect, it } from 'vitest'
import { EVENT_TYPES, NODE_IDS, RAIL_IDS, type GreenlineEvent } from '../contract/events'
import fixture from './__fixtures__/allVariants.json'
import {
  ALL_SEQUENCES, ERROR_RUN, HERO_0142, PATCH_LOOP_0137, TIGHT_0128, WARM_0144,
} from './__fixtures__/sequences'
import { EMPTY_STATE, reduce, reduceAll, type RunState } from './reducer'

const fx = fixture as unknown as Record<string, GreenlineEvent>
const ev = (o: object) => o as GreenlineEvent
const afterStart = reduce(EMPTY_STATE, fx['run.start']!)
const apply = (k: string) => reduce(afterStart, fx[k]!)

function deepFreeze<T>(o: T): T {
  if (o && typeof o === 'object' && !Object.isFrozen(o)) {
    Object.freeze(o)
    for (const v of Object.values(o as object)) deepFreeze(v)
  }
  return o
}
const activeCount = (s: RunState) => NODE_IDS.filter((n) => s.nodes[n].status === 'active').length

describe('EMPTY_STATE', () => {
  it('is empty and frozen', () => {
    for (const n of NODE_IDS) expect(EMPTY_STATE.nodes[n]).toEqual({ status: 'idle' })
    for (const r of RAIL_IDS) {
      expect(r in EMPTY_STATE.guardrails).toBe(true)
      expect(EMPTY_STATE.guardrails[r]).toBeUndefined()
    }
    expect(EMPTY_STATE.path).toEqual([])
    expect(EMPTY_STATE.logs).toEqual([])
    expect(EMPTY_STATE.evidence).toEqual([])
    expect(EMPTY_STATE.patchAttempts).toEqual([])
    expect(EMPTY_STATE.criticVotes).toEqual([])
    expect(EMPTY_STATE.budget).toEqual({ modelCalls: 0, toolCalls: 0, elapsedMs: 0 })
    expect(EMPTY_STATE.lastT).toBe(0)
    expect(EMPTY_STATE.runId).toBeNull()
    expect(EMPTY_STATE.outcome).toBeNull()
    expect(Object.isFrozen(EMPTY_STATE.nodes.watcher)).toBe(true)
  })
})

describe('per variant (allVariants.json)', () => {
  it('run.start', () => {
    expect(afterStart).toMatchObject({
      runId: 'run-0142-abc', caseId: '0142', mode: 'live', model: 'qwen3-8b',
      budgetPreset: 'normal', caps: { modelCalls: 16, toolCalls: 16, elapsedMs: 180000 }, lastT: 0,
    })
  })
  it('node.enter', () => {
    const s = apply('node.enter')
    expect(s.nodes.watcher).toEqual({ status: 'active', enteredAt: 120 })
    expect(s.activeNode).toBe('watcher')
    expect(s.path).toEqual(['watcher'])
  })
  it('node.exit', () => {
    const s = apply('node.exit')
    expect(s.nodes.watcher).toEqual({
      status: 'done', outcome: 'ok', durationMs: 1680, note: 'warm memory hit on #0142',
    })
    expect(s.activeNode).toBeNull()
  })
  it('log', () => {
    const s = apply('log')
    expect(s.logs).toHaveLength(1)
    expect(s.narration).toBe('Pulling the red build')
  })
  it('evidence', () => {
    expect(apply('evidence').evidence).toEqual([
      { t: 1600, node: 'watcher', kind: 'command', text: 'pytest -q && ruff check .', ref: '#0142' },
    ])
  })
  it('rerun.tick', () => {
    expect(apply('rerun.tick').rerun).toEqual({
      total: 10, ticks: [{ n: 4, passed: false, durationMs: 1830 }],
    })
  })
  it('memory.hit', () => {
    expect(apply('memory.hit').memoryHit).toEqual({
      caseRef: '0142', similarity: 0.91, summary: 'flaky settlement reconciliation',
    })
  })
  it('verdict', () => {
    expect(apply('verdict').verdict).toEqual({
      cls: 'flaky', confidence: 0.86, rationale: '7 pass / 3 fail across 10 reruns',
    })
  })
  it('patch.attempt', () => {
    expect(apply('patch.attempt').patchAttempts).toEqual([
      { n: 1, file: 'tests/test_settlement.py', diff: '--- a/x\n+++ b/x\n', source: 'model', result: 'green' },
    ])
  })
  it('critic.vote', () => {
    const v = apply('critic.vote').criticVotes
    expect(v).toHaveLength(1)
    expect(v[0]!.samples).toHaveLength(3)
    expect(v[0]!.deterministic).toEqual([{ name: 'tests_green', passed: true, detail: '10/10' }])
    expect(v[0]!.approved).toBe(true)
  })
  it('budget', () => {
    expect(apply('budget').budget).toEqual({ modelCalls: 3, toolCalls: 11, elapsedMs: 9100 })
  })
  it('guardrail', () => {
    const s = apply('guardrail')
    expect(s.guardrails.protected_file).toEqual({ fired: true, note: 'tests/** is protected', t: 9200 })
    expect(s.guardrails.diff_cap).toBeUndefined()
  })
  it('report', () => {
    expect(apply('report').report).toMatchObject({
      kind: 'pr', prUrl: 'https://github.com/acme/ledger-core/pull/42', dryRun: true,
    })
  })
  it('error', () => {
    const s = apply('error')
    expect(s.error).toBe('model server unreachable')
    expect(s.nodes).toEqual(afterStart.nodes)
  })
  it('done', () => {
    expect(apply('done').outcome).toBe('reported')
  })
  it.each(EVENT_TYPES.filter((k) => k !== 'run.start'))('%s: lastT follows event t', (k) => {
    expect(apply(k).lastT).toBe(fx[k]!.t)
  })
})

describe('semantics', () => {
  it('warn log does not change narration', () => {
    const s = reduceAll([
      ev({ t: 1, type: 'log', node: 'watcher', level: 'info', text: 'hello' }),
      ev({ t: 2, type: 'log', node: 'watcher', level: 'warn', text: 'careful' }),
    ], afterStart)
    expect(s.logs).toHaveLength(2)
    expect(s.narration).toBe('hello')
  })
  it('omits absent optional keys', () => {
    const s = reduceAll([
      ev({ t: 1, type: 'node.enter', node: 'watcher' }),
      ev({ t: 2, type: 'node.exit', node: 'watcher', durationMs: 1, status: 'ok' }),
      ev({ t: 3, type: 'report', kind: 'escalation', title: 't', body: 'b' }),
      ev({ t: 4, type: 'evidence', node: 'watcher', kind: 'observation', text: 'x' }),
    ], afterStart)
    expect('note' in s.nodes.watcher).toBe(false)
    expect('prUrl' in s.report!).toBe(false)
    expect('dryRun' in s.report!).toBe(false)
    expect('ref' in s.evidence[0]!).toBe(false)
  })
  it('latest guardrail per rail wins', () => {
    const s = reduceAll([
      ev({ t: 1, type: 'guardrail', rail: 'diff_cap', fired: false, note: 'a' }),
      ev({ t: 2, type: 'guardrail', rail: 'diff_cap', fired: true, note: 'b' }),
    ], afterStart)
    expect(s.guardrails.diff_cap).toEqual({ fired: true, note: 'b', t: 2 })
  })
  it('run.start resets a previous run', () => {
    const prev = reduceAll(HERO_0142)
    const warmStart = WARM_0144[0]!
    if (warmStart.type !== 'run.start') throw new Error('bad fixture')
    expect(reduce(prev, warmStart)).toEqual({
      ...EMPTY_STATE,
      runId: warmStart.runId, caseId: warmStart.caseId, mode: warmStart.mode, model: warmStart.model,
      budgetPreset: warmStart.budgetPreset, caps: warmStart.caps, lastT: warmStart.t,
    })
  })
  it('PATCH_LOOP_0137: patch loop', () => {
    const s = reduceAll(PATCH_LOOP_0137)
    const tail = s.path.slice(s.path.indexOf('patcher'))
    expect(tail.slice(0, 4)).toEqual(['patcher', 'critic', 'patcher', 'critic'])
    expect(s.patchAttempts.map((p) => p.result)).toEqual(['red', 'green'])
    expect(s.criticVotes.map((c) => c.approved)).toEqual([false, true])
    expect(s.nodes.patcher.outcome).toBe('ok')
  })
  it('WARM_0144: reproducer skipped', () => {
    const s = reduceAll(WARM_0144)
    expect(s.nodes.reproducer).toMatchObject({ status: 'done', outcome: 'skip', note: 'warm memory hit on #0142' })
    expect(s.memoryHit).not.toBeNull()
    expect(s.rerun).toBeNull()
  })
  it('ERROR_RUN: active node closed as fail', () => {
    const s = reduceAll(ERROR_RUN)
    const errT = ERROR_RUN.find((e) => e.type === 'error')!.t
    expect(s.nodes.triage).toMatchObject({ status: 'done', outcome: 'fail' })
    expect(s.nodes.triage.durationMs).toBe(errT - s.nodes.triage.enteredAt!)
    expect(s.activeNode).toBeNull()
    expect(s.error).toBe('model server unreachable')
    expect(s.outcome).toBe('error')
    expect(s.report).toBeNull()
    expect(s.verdict).toBeNull()
  })
  it('enter while another node is active fails the old one', () => {
    const s = reduceAll([
      ev({ t: 10, type: 'node.enter', node: 'watcher' }),
      ev({ t: 50, type: 'node.enter', node: 'triage' }),
    ], afterStart)
    expect(s.nodes.watcher).toMatchObject({ status: 'done', outcome: 'fail', durationMs: 40 })
    expect(s.nodes.triage.status).toBe('active')
    expect(s.activeNode).toBe('triage')
    expect(activeCount(s)).toBe(1)
  })
})

describe('purity', () => {
  it.each(Object.entries(ALL_SEQUENCES))('%s: frozen intermediates, deterministic', (_n, events) => {
    let s: RunState = EMPTY_STATE
    for (const e of events) {
      const before = structuredClone(s)
      s = deepFreeze(reduce(s, e))
      expect(s).not.toBe(before)
    }
    expect(reduceAll(events)).toEqual(s)
  })
  it('does not mutate its input', () => {
    const before = structuredClone(afterStart)
    reduce(afterStart, fx['node.enter']!)
    expect(afterStart).toEqual(before)
  })
})

describe('invariants through the reducer', () => {
  describe.each(Object.entries(ALL_SEQUENCES))('%s', (_n, events) => {
    it('I1/I2/I3 hold at every step', () => {
      let s: RunState = EMPTY_STATE
      let prevT = 0
      events.forEach((e, i) => {
        s = reduce(s, e)
        if (i === 0) {
          expect(s.runId).not.toBeNull()
          expect(s.outcome).toBeNull()
        }
        if (i < events.length - 1) expect(s.outcome).toBeNull()
        expect(s.lastT).toBeGreaterThanOrEqual(prevT)
        prevT = s.lastT
        expect(activeCount(s)).toBe(s.activeNode === null ? 0 : 1)
      })
      expect(s.outcome).not.toBeNull()
      expect(s.lastT).toBe(events[events.length - 1]!.t)
      expect(activeCount(s)).toBe(0)
    })
  })
  it('I4: verdict presence', () => {
    for (const seq of [HERO_0142, WARM_0144, PATCH_LOOP_0137]) expect(reduceAll(seq).verdict).not.toBeNull()
    const tight = reduceAll(TIGHT_0128)
    expect(tight.verdict).toBeNull()
    expect(tight.outcome).toBe('budget_exhausted')
    const err = reduceAll(ERROR_RUN)
    expect(err.verdict).toBeNull()
    expect(err.outcome).toBe('error')
  })
  it('I5: HERO rerun grid', () => {
    const r = reduceAll(HERO_0142).rerun!
    expect(r.ticks.map((t) => t.n)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    expect(r.total).toBe(10)
    expect(r.ticks.filter((t) => t.passed)).toHaveLength(7)
    expect(r.ticks.filter((t) => !t.passed)).toHaveLength(3)
  })
  it('I6: report exists before done', () => {
    for (const seq of [HERO_0142, WARM_0144, PATCH_LOOP_0137, TIGHT_0128]) {
      expect(reduceAll(seq.slice(0, -1)).report).not.toBeNull()
    }
    expect(reduceAll(ERROR_RUN).report).toBeNull()
  })
})
