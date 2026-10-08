import type { BudgetPreset, RunMode } from '../contract/events'

export interface Health {
  modelServer: { url: string; reachable: boolean; model: string }
  embedServer: { url: string; reachable: boolean }
  docker: { reachable: boolean; sandboxImage: boolean }
  fixtureRepo: { seeded: boolean }
  gpuVramFreeMb: number | null
}
export interface StartRunOptions {
  mode: RunMode
  budget: BudgetPreset
  /** Demo mode only: replay a named alternate recording instead of the default one. */
  recording?: string
}
export interface WarmVsCold {
  coldMs: number | null
  warmMs: number | null
  coldToolCalls: number | null
  warmToolCalls: number | null
}
export interface ScoreboardMetrics {
  triageAccuracy: number | null
  patchSuccessRate: number | null
  escalationRate: number | null
  medianTimeToVerdictMs: number | null
  p95DurationMs: number | null
  avgModelCalls: number | null
  avgToolCalls: number | null
  warmVsCold: WarmVsCold
}
export interface PerCaseRow {
  caseId: string
  runs: number
  lastOutcome: string | null
  medianDurationMs: number | null
}
export interface Scoreboard {
  sampleSize: number
  metrics: ScoreboardMetrics
  /** Sparse: matrix[actual][predicted] = count; missing cells are zero. */
  matrix: Record<string, Record<string, number>>
  perCase: PerCaseRow[]
  notMeasured: string[]
  note: string
}
export interface ActiveRun {
  runId: string
  caseId: string
}
