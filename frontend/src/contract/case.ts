import type { FailureClass, Outcome, RunMode } from './events'

export interface FailureCase {
  id: string
  title: string
  repo: string
  branch: string
  cls: FailureClass // ground truth: scoreboard ONLY, never read by state/ or graph code
  detectedAt: string
  ciRunUrl: string
  beat: string
}
export interface RunSummary {
  runId: string
  outcome: Outcome
  durationMs: number
  modelCalls: number
  toolCalls: number
  mode: RunMode
}
export interface CaseSummary extends FailureCase {
  lastRun: RunSummary | null
  hasDemoRun: boolean
}
