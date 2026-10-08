import { api } from '../api/client'
import { useCaseStore } from '../state/caseStore'
import { useHealthStore } from '../state/healthStore'
import { useRunStore } from '../state/runStore'
import { useUiStore } from '../state/uiStore'
import { shouldResetRun } from './runReset'

let started = false

export async function bootstrap(): Promise<void> {
  if (started) return
  started = true

  useHealthStore.getState().startPolling()

  // Hidden key L: tokens.css defines the light palette under :root[data-theme='light'].
  useUiStore.subscribe((ui, prev) => {
    if (ui.theme === prev.theme) return
    if (ui.theme === 'light') document.documentElement.dataset.theme = 'light'
    else delete document.documentElement.dataset.theme
  })

  // Picking another case clears a finished run, so its panels don't sit under the new case header.
  useUiStore.subscribe((ui, prev) => {
    if (ui.selectedCaseId === prev.selectedCaseId) return
    const run = useRunStore.getState()
    if (shouldResetRun({ status: run.status, runCaseId: run.state.caseId, selectedCaseId: ui.selectedCaseId })) {
      run.reset()
    }
  })

  await useCaseStore.getState().refresh()
  const { cases } = useCaseStore.getState()
  const ui = useUiStore.getState()
  if (ui.selectedCaseId === null && cases.length > 0) {
    ui.selectCase(cases.find((c) => c.id === '0142')?.id ?? cases[0]!.id)
  }

  // Re-attach to a run that is already in progress (e.g. after a page refresh).
  try {
    const active = await api.activeRun()
    if (active) {
      useUiStore.getState().selectCase(active.caseId)
      useRunStore.getState().attach(active.runId)
    }
  } catch {
    // health polling already reports the backend being down
  }
}
