import type { Scoreboard } from '../api/types'
import { FAILURE_CLASSES } from '../contract/events'
import { OUTCOME_VIEW, type ToneName } from './consts'

const SMALL_SAMPLE = 30
const DASH = '–'

export interface TileView {
  label: string
  value: string
  sub: string
}
export type CellKind = 'diag' | 'off' | 'zero'
export interface MatrixRowView {
  label: string
  cells: { n: number; kind: CellKind }[]
}
export interface CaseRowView {
  id: string
  runs: number
  outcome: string
  outcomeTone: ToneName
  median: string
}
export interface ScoreboardView {
  chip: string
  tiles: TileView[]
  classes: string[]
  matrix: MatrixRowView[]
  rows: CaseRowView[]
  footnote: string
}

const NOT_MEASURED_LABEL: Record<string, string> = {
  falsePrRate: 'false-PR rate',
  humanBaseline: 'human baseline',
}

const pct = (x: number | null) => (x === null ? DASH : `${Math.round(x * 100)}%`)
const sec = (ms: number | null) => (ms === null ? DASH : `${(ms / 1000).toFixed(1)} s`)
const secBare = (ms: number) => (ms / 1000).toFixed(1)

function matrixTotals(m: Scoreboard['matrix']): { diag: number; total: number } {
  let diag = 0
  let total = 0
  for (const [actual, row] of Object.entries(m)) {
    for (const [pred, n] of Object.entries(row)) {
      total += n
      if (actual === pred) diag += n
    }
  }
  return { diag, total }
}

export function scoreboardView(sb: Scoreboard): ScoreboardView {
  const n = sb.sampleSize
  const { metrics: m } = sb
  const { diag, total } = matrixTotals(sb.matrix)
  const warm = m.warmVsCold.warmMs
  const cold = m.warmVsCold.coldMs

  const tiles: TileView[] = [
    {
      label: 'Triage accuracy',
      value: pct(m.triageAccuracy),
      sub: m.triageAccuracy === null || total === 0 ? 'not measured' : `${diag} of ${total} verdicts correct`,
    },
    {
      label: 'Patch success',
      value: pct(m.patchSuccessRate),
      sub: m.patchSuccessRate === null ? 'not measured' : 'of runs that reached a patch',
    },
    {
      label: 'Escalation rate',
      value: pct(m.escalationRate),
      sub: m.escalationRate === null ? 'not measured' : `${Math.round(m.escalationRate * n)} of ${n} runs`,
    },
    {
      label: 'Median to verdict',
      value: sec(m.medianTimeToVerdictMs),
      sub: m.medianTimeToVerdictMs === null ? 'not measured' : 'live runs only',
    },
    {
      label: 'P95 run duration',
      value: sec(m.p95DurationMs),
      sub: m.p95DurationMs === null ? 'not measured' : 'live runs only',
    },
    {
      label: 'Warm vs cold',
      value: warm === null || cold === null ? DASH : `${secBare(warm)} / ${secBare(cold)} s`,
      sub: warm === null || cold === null ? 'not measured' : '#0144 vs #0142, median',
    },
  ]

  const matrix = FAILURE_CLASSES.map(
    (actual): MatrixRowView => ({
      label: actual,
      cells: FAILURE_CLASSES.map((pred) => {
        const count = sb.matrix[actual]?.[pred] ?? 0
        const kind: CellKind = count === 0 ? 'zero' : actual === pred ? 'diag' : 'off'
        return { n: count, kind }
      }),
    }),
  )

  const rows = sb.perCase.map((c): CaseRowView => {
    const known = c.lastOutcome && c.lastOutcome in OUTCOME_VIEW ? OUTCOME_VIEW[c.lastOutcome as keyof typeof OUTCOME_VIEW] : null
    return {
      id: c.caseId,
      runs: c.runs,
      outcome: known ? known.label : c.lastOutcome ?? DASH,
      outcomeTone: known ? known.tone : 'muted',
      median: sec(c.medianDurationMs),
    }
  })

  const missing = sb.notMeasured.map((k) => NOT_MEASURED_LABEL[k] ?? k)
  const footnote = missing.length
    ? `Not measured: ${missing.join(', ')}. They need human review, so they are not shown as numbers.`
    : ''

  return {
    chip: `from ${n} live run${n === 1 ? '' : 's'}${n < SMALL_SAMPLE ? ' · small sample' : ''}`,
    tiles,
    classes: [...FAILURE_CLASSES],
    matrix,
    rows,
    footnote,
  }
}
