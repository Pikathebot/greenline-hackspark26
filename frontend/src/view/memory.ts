import type { CaseSummary } from '../contract/case'
import type { RunState } from '../state/runState'

export interface BarView {
  label: string
  /** this run */
  a: string
  /** the recalled case's last live run */
  b: string
  aPx: number
  bPx: number
}

export interface MemoryView {
  ref: string
  sim: string
  text: string
  /** null until the run is done and the recalled case has a completed live run */
  bars: BarView[] | null
}

const MAX_BAR_PX = 150

function px(v: number, max: number): number {
  return Math.max(4, Math.round((v / (max || 1)) * MAX_BAR_PX))
}

function bar(label: string, a: number, b: number, fmt: (v: number) => string): BarView {
  const max = Math.max(a, b)
  return { label, a: fmt(a), b: fmt(b), aPx: px(a, max), bPx: px(b, max) }
}

export function memoryView(p: { s: RunState; cases: CaseSummary[] }): MemoryView | null {
  const { s, cases } = p
  const hit = s.memoryHit
  if (!hit) return null
  const recalled = cases.find((c) => c.id === hit.caseRef)?.lastRun ?? null
  const bars =
    s.outcome !== null && recalled
      ? [
          bar('Time', s.lastT / 1000, recalled.durationMs / 1000, (v) => `${v.toFixed(1)} s`),
          bar('Sandbox runs', s.budget.toolCalls, recalled.toolCalls, String),
          bar('Model calls', s.budget.modelCalls, recalled.modelCalls, String),
        ]
      : null
  return { ref: `#${hit.caseRef}`, sim: hit.similarity.toFixed(2), text: hit.summary, bars }
}
