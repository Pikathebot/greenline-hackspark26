import { create } from 'zustand'
import { api, type Api } from '../api/client'
import type { Scoreboard } from '../api/types'

export type ScoreboardStatus = 'idle' | 'loading' | 'ready' | 'error'

export interface ScoreboardStoreState {
  data: Scoreboard | null
  status: ScoreboardStatus
  refresh(): Promise<void>
}

export function createScoreboardStore(deps: { api: Pick<Api, 'scoreboard'> }) {
  return create<ScoreboardStoreState>()((set) => ({
    data: null,
    status: 'idle',
    async refresh() {
      set({ status: 'loading' })
      try {
        const data = await deps.api.scoreboard()
        set({ data, status: 'ready' })
      } catch {
        // keep whatever we had; the overlay shows the error line
        set({ status: 'error' })
      }
    },
  }))
}

export const useScoreboardStore = createScoreboardStore({ api })
