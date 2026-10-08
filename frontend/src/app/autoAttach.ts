import type { RunStatus } from '../state/runStore'

/**
 * A run can start without a click (B18: Greenline notices a red GitHub Actions build and runs it by
 * itself). Attach to it when the backend reports an active run this page is not already showing.
 */
export function shouldAttachActive(p: {
  status: RunStatus
  currentRunId: string | null
  activeRunId: string | null
}): boolean {
  if (p.activeRunId === null) return false
  if (p.status === 'starting' || p.status === 'streaming') return false
  return p.activeRunId !== p.currentRunId
}
