import type { CaseSummary } from '../contract/case'
import type { ActiveRun, Health, Scoreboard, StartRunOptions } from './types'

/** status 0 = network failure (backend unreachable). */
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, init)
  } catch {
    throw new ApiError(0, 'backend unreachable')
  }
  if (!res.ok) {
    let detail: string | undefined
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // body wasn't JSON; fall back to the status text
    }
    throw new ApiError(res.status, detail ?? res.statusText)
  }
  return (await res.json()) as T
}

export const api = {
  health: () => request<Health>('/api/health'),
  cases: () => request<CaseSummary[]>('/api/cases'),
  startRun: (caseId: string, o: StartRunOptions) =>
    request<{ runId: string }>(`/api/cases/${encodeURIComponent(caseId)}/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(o),
    }),
  activeRun: () => request<ActiveRun | null>('/api/runs/active'),
  scoreboard: () => request<Scoreboard>('/api/scoreboard'),
}
export type Api = typeof api
