import type { GreenlineEvent } from '../contract/events'
import type { RunState } from '../state/runState'

export interface RunSnapshot {
  runId: string | null
  events: GreenlineEvent[]
  state: RunState
}

/** The last finished run of each case this session, so switching cases doesn't lose its result. */
const cache = new Map<string, RunSnapshot>()

export function rememberRun(caseId: string, snap: RunSnapshot): void {
  cache.set(caseId, snap)
}

export function recallRun(caseId: string | null): RunSnapshot | null {
  return caseId === null ? null : (cache.get(caseId) ?? null)
}

export function forgetRuns(): void {
  cache.clear()
}
