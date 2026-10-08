import { create } from 'zustand'
import { api, type Api } from '../api/client'
import type { CaseSummary } from '../contract/case'

export interface CaseStoreState {
  cases: CaseSummary[]
  loaded: boolean
  error: string | null
  refresh(): Promise<void>
}

export function createCaseStore(deps: { api: Pick<Api, 'cases'> }) {
  return create<CaseStoreState>()((set) => ({
    cases: [],
    loaded: false,
    error: null,
    async refresh() {
      try {
        const cases = await deps.api.cases()
        set({ cases, loaded: true, error: null })
      } catch (err) {
        set({ error: err instanceof Error ? err.message : String(err) })
      }
    },
  }))
}

export const useCaseStore = createCaseStore({ api })
