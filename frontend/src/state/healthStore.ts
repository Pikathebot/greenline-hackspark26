import { create } from 'zustand'
import { api, ApiError, type Api } from '../api/client'
import type { Health } from '../api/types'

export const HEALTH_POLL_MS = 3000
/** The dev proxy drops an occasional poll during a live run; only a streak of misses is an outage. */
export const OFFLINE_AFTER_MISSES = 3

export interface HealthStoreState {
  health: Health | null
  /** null = not checked yet */
  backendReachable: boolean | null
  check(): Promise<void>
  /** Checks now and every HEALTH_POLL_MS; returns a stop function. */
  startPolling(): () => void
}

export function createHealthStore(deps: { api: Pick<Api, 'health'> }) {
  let misses = 0
  return create<HealthStoreState>()((set, get) => ({
    health: null,
    backendReachable: null,
    async check() {
      try {
        const health = await deps.api.health()
        misses = 0
        set({ health, backendReachable: true })
      } catch (err) {
        // status 0 = network failure; 5xx = the Vite proxy has no backend to forward to
        if (err instanceof ApiError && (err.status === 0 || err.status >= 500)) {
          misses += 1
          // Never reached it yet: say so at once. Reached it before: ride out a blip.
          if (get().backendReachable !== true || misses >= OFFLINE_AFTER_MISSES) {
            set({ backendReachable: false })
          }
        }
      }
    },
    startPolling() {
      void get().check()
      const id = setInterval(() => void get().check(), HEALTH_POLL_MS)
      return () => clearInterval(id)
    },
  }))
}

export const useHealthStore = createHealthStore({ api })
