import { describe, expect, it } from 'vitest'
import { EMPTY_STATE } from '../state/runState'
import { reduceAll } from '../state/reducer'
import { ERROR_RUN, HERO_0142, PATCH_LOOP_0137, TIGHT_0128 } from '../state/__fixtures__/sequences'
import { artifactView, railViews, verdictView } from './panels'
import { stateAfter } from './testHelpers'

describe('verdictView', () => {
  it('idle / running without a verdict', () => {
    expect(verdictView({ s: EMPTY_STATE, status: 'idle' })).toMatchObject({ kind: 'none', title: 'No run yet' })
    expect(verdictView({ s: reduceAll(HERO_0142.slice(0, 5)), status: 'streaming' })).toMatchObject({
      kind: 'none', title: 'Gathering evidence…',
    })
  })
  it('HERO: FLAKY 95%', () => {
    expect(verdictView({ s: reduceAll(HERO_0142), status: 'done' })).toMatchObject({
      kind: 'verdict', word: 'FLAKY', pct: '95%', fillPct: 95,
    })
  })
  it('TIGHT: no verdict, budget text from the run caps', () => {
    expect(verdictView({ s: reduceAll(TIGHT_0128), status: 'done' })).toMatchObject({
      kind: 'none', title: 'No verdict reached', tone: 'warn',
      sub: 'Budget exhausted. Tight allows 4 model calls and 3 sandbox runs.',
    })
  })
  it('ERROR: names the failed node', () => {
    expect(verdictView({ s: reduceAll(ERROR_RUN), status: 'done' })).toMatchObject({
      kind: 'none', tone: 'danger', sub: 'The run ended with an error during Triage.',
    })
  })
})

describe('railViews', () => {
  it('HERO: one blocked, two clear, two not checked', () => {
    const { rails, summary } = railViews(reduceAll(HERO_0142))
    expect(rails.map((r) => `${r.id}:${r.state}`)).toEqual([
      'protected_file:fired', 'diff_cap:idle', 'no_main_write:idle', 'no_creds:clear', 'egress_off:clear',
    ])
    expect(rails[1]!.note).toBe('Not checked yet')
    expect(summary).toBe('1 blocked · 2 clear · 2 not checked')
  })
  it('PATCH_LOOP: diff_cap and no_main_write clear', () => {
    const { rails } = railViews(reduceAll(PATCH_LOOP_0137))
    expect(rails.find((r) => r.id === 'diff_cap')!.state).toBe('clear')
    expect(rails.find((r) => r.id === 'no_main_write')!.state).toBe('clear')
  })
})

describe('artifactView', () => {
  it('empty before a report', () => {
    expect(artifactView(EMPTY_STATE)).toEqual({ kind: 'empty', hint: '' })
  })
  it('escalation reasons', () => {
    expect(artifactView(reduceAll(HERO_0142))).toMatchObject({
      kind: 'escalation', reason: 'guardrail · protected_file', reasonTone: 'danger', header: 'Escalated to a human',
    })
    expect(artifactView(reduceAll(TIGHT_0128))).toMatchObject({ reason: 'budget exhausted', reasonTone: 'warn' })
    const err = reduceAll([...ERROR_RUN.slice(0, -1), { t: 999, type: 'report', kind: 'escalation', title: 't', body: 'b' }, ERROR_RUN[ERROR_RUN.length - 1]!])
    expect(artifactView(err)).toMatchObject({ reason: 'error', reasonTone: 'danger' })
  })
  it('PR kind carries the url and dry-run flag', () => {
    expect(artifactView(reduceAll(PATCH_LOOP_0137))).toMatchObject({
      kind: 'pr', hint: 'draft PR', prUrl: 'https://example.test/pr/1', dryRun: true,
    })
  })
})

describe('artifactView: patch loop and PR with diff', () => {
  it('PR carries the accepted attempt: file, parsed diff, vote', () => {
    const a = artifactView(reduceAll(PATCH_LOOP_0137))
    expect(a.kind).toBe('pr')
    if (a.kind !== 'pr') return
    expect(a.file).toBe('src/rollup.py')
    expect(a.diff).toEqual([
      { kind: 'del', text: '-a' },
      { kind: 'add', text: '+c' },
    ])
    expect(a.vote!.text).toBe('approved 3 / 3')
  })
  it('while patching (no report) the artifact is the loop view', () => {
    const s = stateAfter(PATCH_LOOP_0137, 'node.enter', 2, (e) => e.type === 'node.enter' && e.node === 'patcher')
    expect(artifactView(s)).toEqual({ kind: 'loop', hint: '2 attempts max' })
  })
  it('a PR report with no green attempt still renders (empty diff, no vote)', () => {
    const s = reduceAll([{ t: 1, type: 'report', kind: 'pr', title: 't', body: 'b' } as never])
    expect(artifactView(s)).toMatchObject({ kind: 'pr', file: '', diff: [], vote: null })
  })
})
