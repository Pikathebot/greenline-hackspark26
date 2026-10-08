import { describe, expect, it } from 'vitest'
import type { GreenlineEvent } from '../contract/events'
import { reduceAll } from '../state/reducer'
import { HERO_0142, PATCH_LOOP_0137 } from '../state/__fixtures__/sequences'
import { attemptViews, parseDiff, voteView } from './patch'
import { stateAfter } from './testHelpers'

describe('parseDiff', () => {
  it('drops headers, classifies the rest', () => {
    const d = ['--- a/x.py', '+++ b/x.py', '@@ -1,2 +1,2 @@', ' keep', '-old', '+new', ''].join('\n')
    expect(parseDiff(d)).toEqual([
      { kind: 'hunk', text: '@@ -1,2 +1,2 @@' },
      { kind: 'ctx', text: ' keep' },
      { kind: 'del', text: '-old' },
      { kind: 'add', text: '+new' },
    ])
  })
  it('skips git headers and no-newline markers', () => {
    const d = 'diff --git a/x b/x\nindex 1..2 100644\n--- a/x\n+++ b/x\n-a\n\\ No newline at end of file\n+b\n'
    expect(parseDiff(d).map((l) => l.kind)).toEqual(['del', 'add'])
  })
  it('the contract fixture (headers only) and empty input give nothing', () => {
    expect(parseDiff('--- a/x\n+++ b/x\n')).toEqual([])
    expect(parseDiff('')).toEqual([])
  })
  it('unknown prefixes become context; no empty trailing line', () => {
    expect(parseDiff('plain\n')).toEqual([{ kind: 'ctx', text: ' plain' }])
  })
})

describe('voteView', () => {
  const s = reduceAll(PATCH_LOOP_0137)
  it('a deterministic reject has no samples', () => {
    expect(voteView(s, 1)).toMatchObject({
      approved: false, total: 0, text: 'rejected by deterministic checks',
      checks: [{ name: 'tests_green', passed: false, detail: '' }],
    })
  })
  it('an approved vote counts the samples', () => {
    expect(voteView(s, 2)).toMatchObject({
      approvals: 3, total: 3, approved: true, text: 'approved 3 / 3',
      checks: [{ name: 'tests_green', passed: true, detail: '3/3' }],
    })
  })
  it('rejected with samples says rejected x / y', () => {
    const vote: GreenlineEvent = {
      t: 1, type: 'critic.vote', n: 1, samples: ['reject', 'reject', 'approve'], deterministic: [], approved: false,
    }
    expect(voteView(reduceAll([vote]), 1)!.text).toBe('rejected 2 / 3')
  })
  it('approved without samples (deterministic only)', () => {
    const vote: GreenlineEvent = { t: 1, type: 'critic.vote', n: 1, samples: [], deterministic: [], approved: true }
    expect(voteView(reduceAll([vote]), 1)!.text).toBe('approved by deterministic checks')
  })
  it('unknown attempt', () => {
    expect(voteView(s, 9)).toBeNull()
  })
})

describe('attemptViews', () => {
  it('PATCH_LOOP final: red then green, the second is accepted', () => {
    const { attempts, acceptedN } = attemptViews(reduceAll(PATCH_LOOP_0137))
    expect(attempts.map((a) => [a.n, a.state, a.note])).toEqual([
      [1, 'red', 'rejected by Critic'],
      [2, 'green', 'approved by Critic'],
    ])
    expect(attempts.some((a) => a.running)).toBe(false)
    expect(acceptedN).toBe(2)
    expect(attempts[1]!.diff).toEqual([
      { kind: 'del', text: '-a' },
      { kind: 'add', text: '+c' },
    ])
  })
  it('at the second patcher entry: attempt 1 plus a running card', () => {
    const s = stateAfter(PATCH_LOOP_0137, 'node.enter', 2, (e) => e.type === 'node.enter' && e.node === 'patcher')
    const { attempts, acceptedN } = attemptViews(s)
    expect(attempts).toHaveLength(2)
    expect(attempts[0]).toMatchObject({ n: 1, state: 'red' })
    expect(attempts[1]).toMatchObject({ n: 2, state: 'running', running: true, note: '2 / 2' })
    expect(acceptedN).toBeNull()
  })
  it('a green attempt with no vote yet awaits the Critic', () => {
    const s = stateAfter(PATCH_LOOP_0137, 'patch.attempt', 2)
    expect(attemptViews(s).attempts[1]).toMatchObject({ state: 'green', note: 'awaiting Critic' })
  })
  it('a vetoed attempt is blocked by a guardrail', () => {
    const veto: GreenlineEvent = {
      t: 1, type: 'patch.attempt', n: 1, file: 'tests/t.py', diff: '-a\n+b\n', source: 'model', result: 'vetoed',
    }
    expect(attemptViews(reduceAll([veto])).attempts[0]).toMatchObject({ state: 'vetoed', note: 'blocked by a guardrail' })
  })
  it('no patching, nothing to show', () => {
    expect(attemptViews(reduceAll(HERO_0142))).toEqual({ attempts: [], acceptedN: null })
  })
})

describe('parseDiff: real-world edges', () => {
  it('a deleted "-- " or added "++ " line after the first hunk is not mistaken for a header', () => {
    const d = '--- a/x.sql\n+++ b/x.sql\n@@ -1,2 +1,2 @@\n--- old comment\n+++ new comment\n'
    expect(parseDiff(d).map((l) => `${l.kind}:${l.text}`)).toEqual([
      'hunk:@@ -1,2 +1,2 @@',
      'del:--- old comment',
      'add:+++ new comment',
    ])
  })
  it('B\'s real #0137 patch diff (unified, quotes and blank context lines)', () => {
    const d =
      '--- a/ledger_core/rollup.py\n+++ b/ledger_core/rollup.py\n@@ -1,6 +1,6 @@\n-"""Settlement window membership."""\n+\'\'\'Settlement window membership.\'\'\'\n \n \n def in_window(txn_date, start, end) -> bool:\n     """True if txn_date falls within [start, end) -- end is exclusive."""\n-    return start <= txn_date <= end\n+    return start <= txn_date < end'
    const lines = parseDiff(d)
    expect(lines.map((l) => l.kind)).toEqual(['hunk', 'del', 'add', 'ctx', 'ctx', 'ctx', 'ctx', 'del', 'add'])
    expect(lines[lines.length - 1]!.text).toBe('+    return start <= txn_date < end')
  })
})
