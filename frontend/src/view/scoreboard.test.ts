import { describe, expect, it } from 'vitest'
import type { Scoreboard } from '../api/types'
import { scoreboardView } from './scoreboard'

// A real /api/scoreboard response (B12, 8 Oct 2026, 17 live runs).
const REAL: Scoreboard = {
  sampleSize: 17,
  metrics: {
    triageAccuracy: 1.0,
    patchSuccessRate: 1.0,
    escalationRate: 0.4117647058823529,
    medianTimeToVerdictMs: 7366.5,
    p95DurationMs: 20643.399999999998,
    avgModelCalls: 4.529411764705882,
    avgToolCalls: 5.823529411764706,
    warmVsCold: { coldMs: 15141.0, warmMs: 12983.5, coldToolCalls: 12.0, warmToolCalls: 8.0 },
  },
  matrix: { flaky: { flaky: 5 }, dependency: { dependency: 3 }, lint: { lint: 4 }, regression: { regression: 2 }, env: { env: 2 } },
  perCase: [
    { caseId: '0142', runs: 3, lastOutcome: 'escalated', medianDurationMs: 15141.0 },
    { caseId: '0128', runs: 3, lastOutcome: 'budget_exhausted', medianDurationMs: 8391.0 },
  ],
  notMeasured: ['falsePrRate', 'humanBaseline'],
  note: 'Computed from 17 completed live run(s).',
}

const EMPTY: Scoreboard = {
  sampleSize: 0,
  metrics: {
    triageAccuracy: null,
    patchSuccessRate: null,
    escalationRate: null,
    medianTimeToVerdictMs: null,
    p95DurationMs: null,
    avgModelCalls: null,
    avgToolCalls: null,
    warmVsCold: { coldMs: null, warmMs: null, coldToolCalls: null, warmToolCalls: null },
  },
  matrix: {},
  perCase: [{ caseId: '0142', runs: 0, lastOutcome: null, medianDurationMs: null }],
  notMeasured: ['falsePrRate', 'humanBaseline'],
  note: '',
}

describe('scoreboardView', () => {
  it('formats the six tiles from a real response', () => {
    const v = scoreboardView(REAL)
    expect(v.tiles.map((t) => [t.label, t.value, t.sub])).toEqual([
      ['Triage accuracy', '100%', '16 of 16 verdicts correct'],
      ['Patch success', '100%', 'of runs that reached a patch'],
      ['Escalation rate', '41%', '7 of 17 runs'],
      ['Median to verdict', '7.4 s', 'live runs only'],
      ['P95 run duration', '20.6 s', 'live runs only'],
      ['Warm vs cold', '13.0 / 15.1 s', '#0144 vs #0142, median'],
    ])
  })

  it('says it is a small sample', () => {
    expect(scoreboardView(REAL).chip).toBe('from 17 live runs · small sample')
  })

  it('fills the sparse matrix to 5x5 and marks diagonal and off-diagonal cells', () => {
    const v = scoreboardView({ ...REAL, matrix: { ...REAL.matrix, regression: { regression: 2, dependency: 1 } } })
    expect(v.classes).toEqual(['flaky', 'dependency', 'env', 'lint', 'regression'])
    expect(v.matrix).toHaveLength(5)
    expect(v.matrix.every((r) => r.cells.length === 5)).toBe(true)
    const flaky = v.matrix.find((r) => r.label === 'flaky')!
    expect(flaky.cells.map((c) => c.kind)).toEqual(['diag', 'zero', 'zero', 'zero', 'zero'])
    const reg = v.matrix.find((r) => r.label === 'regression')!
    expect(reg.cells[1]).toEqual({ n: 1, kind: 'off' })
    expect(reg.cells[4]).toEqual({ n: 2, kind: 'diag' })
  })

  it('maps outcomes to labels and tones, and times to seconds', () => {
    const rows = scoreboardView(REAL).rows
    expect(rows[0]).toMatchObject({ id: '0142', outcome: 'escalated', outcomeTone: 'warn', median: '15.1 s' })
    expect(rows[1]).toMatchObject({ outcome: 'budget exhausted', outcomeTone: 'warn', median: '8.4 s' })
  })

  it('shows dashes and "not measured" when there is no sample', () => {
    const v = scoreboardView(EMPTY)
    expect(v.tiles.every((t) => t.value === '–' && t.sub === 'not measured')).toBe(true)
    expect(v.rows[0]).toMatchObject({ outcome: '–', outcomeTone: 'muted', median: '–', runs: 0 })
    expect(v.matrix.every((r) => r.cells.every((c) => c.kind === 'zero'))).toBe(true)
    expect(v.chip).toBe('from 0 live runs · small sample')
  })

  it('names what is not measured', () => {
    expect(scoreboardView(REAL).footnote).toContain('false-PR rate, human baseline')
    expect(scoreboardView({ ...REAL, notMeasured: [] }).footnote).toBe('')
  })
})
