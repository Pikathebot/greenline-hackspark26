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
}
export interface ActiveRun {
  runId: string
  caseId: string
}
