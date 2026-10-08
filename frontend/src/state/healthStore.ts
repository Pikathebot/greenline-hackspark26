import { create } from 'zustand'
import { api, ApiError, type Api } from '../api/client'
import type { Health } from '../api/types'

export const HEALTH_POLL_MS = 3000

export interface HealthStoreState {
  health: Health | null
  /** null = not checked yet */
  backendReachable: boolean | null
  check(): Promise<void>
  /** Checks now and every HEALTH_POLL_MS; returns a stop function. */
  startPolling(): () => void
}

export function createHealthStore(deps: { api: Pick<Api, 'health'> }) {
  return create<HealthStoreState>()((set, get) => ({
    health: null,
    backendReachable: null,
    async check() {
      try {
        const health = await deps.api.health()
        set({ health, backendReachable: true })
      } catch (err) {
        // status 0 = network failure; 5xx = the Vite proxy has no backend to forward to
        if (err instanceof ApiError && (err.status === 0 || err.status >= 500)) {
          set({ backendReachable: false })
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
