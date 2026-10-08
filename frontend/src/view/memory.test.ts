import { describe, expect, it } from 'vitest'
import type { CaseSummary } from '../contract/case'
import { EMPTY_STATE } from '../state/runState'
import { reduceAll } from '../state/reducer'
import { WARM_0144 } from '../state/__fixtures__/sequences'
import { memoryView } from './memory'

const recalled = (over: Partial<CaseSummary> = {}): CaseSummary => ({
  id: '0142', title: 't', repo: 'r', branch: 'b', cls: 'flaky', detectedAt: '', ciRunUrl: '', beat: '',
  hasDemoRun: true,
  lastRun: { runId: 'r', outcome: 'escalated', durationMs: 34000, modelCalls: 3, toolCalls: 11, mode: 'live' },
  ...over,
})

describe('memoryView', () => {
  it('nothing without a memory hit', () => {
    expect(memoryView({ s: EMPTY_STATE, cases: [recalled()] })).toBeNull()
  })

  it('done run: callout plus three paired bars', () => {
    const s = reduceAll(WARM_0144)
    const m = memoryView({ s, cases: [recalled()] })!
    expect(m).toMatchObject({ ref: '#0142', sim: '0.91', text: 'flaky settlement reconciliation' })
    expect(m.bars!.map((b) => b.label)).toEqual(['Time', 'Sandbox runs', 'Model calls'])
    expect(m.bars![0]).toMatchObject({ a: `${(s.lastT / 1000).toFixed(1)} s`, b: '34.0 s', bPx: 150 })
    expect(m.bars![0]!.aPx).toBeGreaterThanOrEqual(4)
    expect(m.bars![1]).toMatchObject({ a: String(s.budget.toolCalls), b: '11', bPx: 150 })
    expect(m.bars![2]).toMatchObject({ a: String(s.budget.modelCalls), b: '3', bPx: 150 })
  })

  it('no bars mid-run, or without a completed live run of the recalled case', () => {
    const mid = reduceAll(WARM_0144.slice(0, 8))
    expect(mid.memoryHit).not.toBeNull()
    expect(memoryView({ s: mid, cases: [recalled()] })!.bars).toBeNull()
    const done = reduceAll(WARM_0144)
    expect(memoryView({ s: done, cases: [] })!.bars).toBeNull()
    expect(memoryView({ s: done, cases: [recalled({ lastRun: null })] })!.bars).toBeNull()
  })

  it('zero on both sides gives the minimum bar width', () => {
    const s = reduceAll(WARM_0144)
    const zero = recalled({ lastRun: { runId: 'r', outcome: 'escalated', durationMs: 1000, modelCalls: 0, toolCalls: 0, mode: 'live' } })
    const bars = memoryView({ s, cases: [zero] })!.bars!
    expect(bars[1]).toMatchObject({ aPx: 4, bPx: 4 })
    expect(bars[2]).toMatchObject({ aPx: 4, bPx: 4 })
  })
})
