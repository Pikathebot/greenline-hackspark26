import { create } from 'zustand'
import type { BudgetPreset, RunMode } from '../contract/events'

export interface UiState {
  selectedCaseId: string | null
  budgetPreset: BudgetPreset
  /** 'demo' is labelled "Recorded" in the UI. */
  mode: RunMode
  scoreboardOpen: boolean
  focusedEvidence: number | null
  debugOpen: boolean
  /** Hidden key L. Not persisted: every load starts dark. */
  theme: 'dark' | 'light'
  toggleTheme(): void
  selectCase(id: string | null): void
  setBudget(b: BudgetPreset): void
  toggleBudget(): void
  setMode(m: RunMode): void
  toggleMode(): void
  setScoreboardOpen(v: boolean): void
  setFocusedEvidence(i: number | null): void
  toggleDebug(): void
}

export const useUiStore = create<UiState>()((set) => ({
  selectedCaseId: null,
  budgetPreset: 'normal',
  mode: 'live',
  scoreboardOpen: false,
  focusedEvidence: null,
  debugOpen: false,
  theme: 'dark',
  toggleTheme: () => set((s) => ({ theme: s.theme === 'dark' ? 'light' : 'dark' })),
  selectCase: (id) => set({ selectedCaseId: id }),
  setBudget: (b) => set({ budgetPreset: b }),
  toggleBudget: () => set((s) => ({ budgetPreset: s.budgetPreset === 'normal' ? 'tight' : 'normal' })),
  setMode: (m) => set({ mode: m }),
  toggleMode: () => set((s) => ({ mode: s.mode === 'live' ? 'demo' : 'live' })),
  setScoreboardOpen: (v) => set({ scoreboardOpen: v }),
  setFocusedEvidence: (i) => set({ focusedEvidence: i }),
  toggleDebug: () => set((s) => ({ debugOpen: !s.debugOpen })),
}))
