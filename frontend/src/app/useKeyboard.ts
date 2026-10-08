import { useEffect } from 'react'
import type { RunMode } from '../contract/events'
import { useCaseStore } from '../state/caseStore'
import { useHealthStore } from '../state/healthStore'
import { useRunStore, type RunStatus } from '../state/runStore'
import { useUiStore } from '../state/uiStore'
import { buildReportMarkdown, canDownload, reportFilename } from '../view/report'
import { triggerDownload } from './download'

export type KeyActionName =
  | 'selectCase'
  | 'run'
  | 'toggleBudget'
  | 'toggleMode'
  | 'toggleScoreboard'
  | 'download'
  | 'escape'
  | 'toggleDebug'
  | 'none'

export interface KeyContext {
  /** ids the backend listed */
  caseIds: string[]
  selectedId: string | null
  status: RunStatus
  /** healthStore.backendReachable (null = not checked yet) */
  reachable: boolean | null
  /** report written and run finished */
  hasReport: boolean
  /** for D: don't switch to Recorded when the selected case has no recording */
  selectedHasDemoRun: boolean
  mode: RunMode
  scoreboardOpen: boolean
  debugOpen: boolean
}

export interface KeyEventLike {
  key: string
  code: string
  ctrlKey: boolean
  metaKey: boolean
  altKey: boolean
  repeat: boolean
  target: { tagName?: string; isContentEditable?: boolean } | null
}

/** Fixed demo order (docs/08 §5), by case id. */
export const CASE_KEY_ORDER = ['0142', '0144', '0139', '0131', '0137', '0128'] as const

const TYPING_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT'])

export function keyAction(e: KeyEventLike, ctx: KeyContext): { name: KeyActionName; caseId?: string } {
  const none = { name: 'none' as const }
  if (e.ctrlKey || e.metaKey || e.altKey || e.repeat) return none
  if (e.target && (e.target.isContentEditable || TYPING_TAGS.has((e.target.tagName ?? '').toUpperCase()))) return none

  if (e.code === 'Backquote') return { name: 'toggleDebug' }
  if (e.key === 'Escape') return { name: 'escape' }

  const busy = ctx.status === 'starting' || ctx.status === 'streaming'

  if (/^[1-6]$/.test(e.key)) {
    const caseId = CASE_KEY_ORDER[Number(e.key) - 1]!
    return !busy && ctx.caseIds.includes(caseId) ? { name: 'selectCase', caseId } : none
  }
  const k = e.key.toLowerCase()
  if (e.key === 'Enter' || k === 'r') {
    return ctx.reachable !== false && ctx.selectedId !== null && !busy ? { name: 'run' } : none
  }
  if (k === 't') return busy ? none : { name: 'toggleBudget' }
  if (k === 'd') {
    if (busy) return none
    return ctx.mode === 'live' && !ctx.selectedHasDemoRun ? none : { name: 'toggleMode' }
  }
  if (k === 's') return { name: 'toggleScoreboard' }
  if (k === 'e') return ctx.hasReport ? { name: 'download' } : none
  return none
}

function downloadCurrentReport(): void {
  const { state } = useRunStore.getState()
  if (!canDownload(state)) return
  const c = useCaseStore.getState().cases.find((x) => x.id === state.caseId)
  triggerDownload(
    reportFilename(state),
    buildReportMarkdown(state, c ? { id: c.id, title: c.title, repo: c.repo, branch: c.branch } : null),
  )
}

export function useKeyboard(): void {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const ui = useUiStore.getState()
      const run = useRunStore.getState()
      const cases = useCaseStore.getState().cases
      const selected = cases.find((c) => c.id === ui.selectedCaseId) ?? null
      const action = keyAction(
        {
          key: e.key,
          code: e.code,
          ctrlKey: e.ctrlKey,
          metaKey: e.metaKey,
          altKey: e.altKey,
          repeat: e.repeat,
          target: e.target instanceof HTMLElement ? e.target : null,
        },
        {
          caseIds: cases.map((c) => c.id),
          selectedId: ui.selectedCaseId,
          status: run.status,
          reachable: useHealthStore.getState().backendReachable,
          hasReport: canDownload(run.state),
          selectedHasDemoRun: selected?.hasDemoRun ?? false,
          mode: ui.mode,
          scoreboardOpen: ui.scoreboardOpen,
          debugOpen: ui.debugOpen,
        },
      )
      if (action.name === 'none') return
      e.preventDefault() // so Enter on a focused button can't also click it

      switch (action.name) {
        case 'selectCase':
          ui.selectCase(action.caseId!)
          break
        case 'run':
          if (ui.selectedCaseId) void run.startRun(ui.selectedCaseId, { mode: ui.mode, budget: ui.budgetPreset })
          break
        case 'toggleBudget':
          ui.toggleBudget()
          break
        case 'toggleMode':
          ui.toggleMode()
          break
        case 'toggleScoreboard':
          ui.setScoreboardOpen(!ui.scoreboardOpen)
          break
        case 'download':
          downloadCurrentReport()
          break
        case 'escape':
          if (ui.scoreboardOpen) ui.setScoreboardOpen(false)
          else if (ui.debugOpen) ui.toggleDebug()
          break
        case 'toggleDebug':
          ui.toggleDebug()
          break
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
}
