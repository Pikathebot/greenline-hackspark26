import type { RunStatus } from '../state/runStore'

/**
 * A finished (or failed) run stays on screen until you pick another case; then it is cleared so the
 * panels never show one case's verdict under another case's header. A run in flight is never cleared.
 */
export function shouldResetRun(p: { status: RunStatus; runCaseId: string | null; selectedCaseId: string | null }): boolean {
  if (p.status !== 'done' && p.status !== 'error') return false
  return p.runCaseId !== p.selectedCaseId
}
