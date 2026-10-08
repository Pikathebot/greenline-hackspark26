import type { BudgetPreset } from '../contract/events'
import type { RunStatus } from '../state/runStore'
import type { RunState } from '../state/runState'
import { PRESET_CAPS } from './consts'
import { fmtMeterSeconds } from './format'

export interface MeterView {
  label: string
  val: string
  cap: string
  pct: number
  alarm: boolean
  valColor: string
  fillColor: string
}

export function meterViews(p: {
  s: RunState
  status: RunStatus
  preset: BudgetPreset
  elapsedMs: number
  /** false when the backend is unreachable and nothing has run: show dashes */
  available: boolean
}): MeterView[] {
  const { s, status, preset, elapsedMs, available } = p
  const labels = ['Model calls', 'Sandbox runs', 'Time']
  if (!available) {
    return labels.map((label) => ({
      label, val: '–', cap: '–', pct: 0, alarm: false, valColor: 'var(--muted)', fillColor: 'var(--muted)',
    }))
  }
  const caps = s.caps ?? PRESET_CAPS[preset]
  const running = status === 'streaming'
  const done = s.outcome !== null
  const rows: [number, number, string, string][] = [
    [s.budget.modelCalls, caps.modelCalls, String(s.budget.modelCalls), String(caps.modelCalls)],
    [s.budget.toolCalls, caps.toolCalls, String(s.budget.toolCalls), String(caps.toolCalls)],
    [elapsedMs, caps.elapsedMs, fmtMeterSeconds(elapsedMs), fmtMeterSeconds(caps.elapsedMs)],
  ]
  return rows.map(([v, cap, val, capText], i) => {
    const pct = cap > 0 ? Math.min(100, Math.round((v / cap) * 100)) : 0
    const alarm = s.outcome === 'budget_exhausted' || pct >= 80
    return {
      label: labels[i]!,
      val,
      cap: capText,
      pct,
      alarm,
      valColor: alarm ? 'var(--danger)' : running ? 'var(--info)' : done ? 'var(--text)' : 'var(--muted)',
      fillColor: alarm ? 'var(--danger)' : running ? 'var(--info)' : 'var(--muted)',
    }
  })
}
