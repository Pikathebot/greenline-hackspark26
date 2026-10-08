import type { RunStatus } from '../state/runStore'

export type CaseSwitchAction = 'keep' | 'reset' | 'restore'

/**
 * What to do with the run on screen when another case is picked:
 * - a run in flight, or one that already belongs to the picked case, stays ('keep');
 * - a case that finished earlier in this session gets its last run back ('restore');
 * - otherwise a finished or failed run of another case is cleared ('reset'), so the panels never show
 *   one case's verdict under another case's header.
 */
export function caseSwitchAction(p: {
  status: RunStatus
  runCaseId: string | null
  selectedCaseId: string | null
  hasCached: boolean
}): CaseSwitchAction {
  if (p.status === 'starting' || p.status === 'streaming') return 'keep'
  if (p.runCaseId === p.selectedCaseId) return 'keep'
  if (p.hasCached) return 'restore'
  if (p.status === 'done' || p.status === 'error') return 'reset'
  return 'keep'
}
