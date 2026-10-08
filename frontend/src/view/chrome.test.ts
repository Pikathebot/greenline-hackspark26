import { describe, expect, it } from 'vitest'
import type { CaseSummary } from '../contract/case'
import { EMPTY_STATE } from '../state/runState'
import { reduceAll } from '../state/reducer'
import { HERO_0142 } from '../state/__fixtures__/sequences'
import { fmtClockTenths } from './format'
import type { HealthInput } from './chrome'
import { bannerView, caseRows, healthViews, narrationView, runButtonView, summaryView } from './chrome'

const health: HealthInput = {
  modelServer: { url: 'http://m', reachable: true },
  embedServer: { url: 'http://e', reachable: false },
  docker: { reachable: true, sandboxImage: true },
}
const kase = (over: Partial<CaseSummary> = {}): CaseSummary => ({
  id: '0142', title: 't', repo: 'r', branch: 'b', cls: 'flaky', detectedAt: '', ciRunUrl: '',
  beat: 'Restraint: proves the flake', lastRun: null, hasDemoRun: true, ...over,
})

describe('chrome view-models', () => {
  it('healthViews', () => {
    expect(healthViews(null, null).map((c) => c.ok)).toEqual([null, null, null])
    expect(healthViews(health, false).map((c) => c.ok)).toEqual([false, false, false])
    expect(healthViews(health, true).map((c) => c.ok)).toEqual([true, false, true])
  })
  it('bannerView', () => {
    expect(bannerView({ reachable: false, runError: 'x' })!.title).toBe('Backend offline: start uvicorn on :8000')
    expect(bannerView({ reachable: true, runError: 'boom' })!.title).toBe('Run error: boom')
    expect(bannerView({ reachable: true, runError: null })).toBeNull()
  })
  it('narrationView', () => {
    const idle = { s: EMPTY_STATE, status: 'idle' as const, reachable: true }
    expect(narrationView({ ...idle, reachable: false, selectedCase: null }).text).toBe('Waiting for the backend on :8000…')
    expect(narrationView({ ...idle, selectedCase: kase() }).text).toBe(
      'Ready: #0142. Restraint: proves the flake. Press Enter to run.',
    )
    expect(narrationView({ ...idle, selectedCase: kase({ beat: 'Ends with dot.' }) }).text).toBe(
      'Ready: #0142. Ends with dot. Press Enter to run.',
    )
    expect(narrationView({ ...idle, selectedCase: null }).text).toBe('Pick a case to begin.')
    const mid = reduceAll(HERO_0142.slice(0, 16))
    const run = narrationView({ s: mid, status: 'streaming', reachable: true, selectedCase: null })
    expect(run.tag).toBe(mid.activeNode)
    expect(run.text).toBe(mid.narration)
  })
  it('summaryView', () => {
    expect(summaryView(EMPTY_STATE)).toBeNull()
    const s = reduceAll(HERO_0142)
    expect(summaryView(s)).toMatchObject({
      outcomeLabel: 'escalated', tone: 'warn', duration: fmtClockTenths(s.lastT), modelCalls: 1, sandboxRuns: 1,
    })
  })
  it('caseRows', () => {
    const rows = caseRows(
      [kase({ lastRun: { runId: 'r', outcome: 'escalated', durationMs: 34000, modelCalls: 3, toolCalls: 11, mode: 'live' } }), kase({ id: '0144' })],
      '0142',
    )
    expect(rows[0]).toMatchObject({ pillLabel: 'escalated', pillTone: 'warn', meta: 'last live run · 00:34', selected: true })
    expect(rows[1]).toMatchObject({ pillLabel: 'not run', pillTone: 'muted', meta: 'no live run yet', selected: false })
  })
  it('runButtonView', () => {
    expect(runButtonView({ reachable: false, status: 'idle', caseId: '0142' })).toEqual({ label: 'Backend offline', enabled: false })
    expect(runButtonView({ reachable: true, status: 'streaming', caseId: '0142' })).toEqual({ label: 'Running #0142…', enabled: false })
    expect(runButtonView({ reachable: true, status: 'idle', caseId: '0142' })).toEqual({ label: 'Run #0142', enabled: true })
    expect(runButtonView({ reachable: true, status: 'idle', caseId: null })).toEqual({ label: 'Run #—', enabled: false })
  })
})
