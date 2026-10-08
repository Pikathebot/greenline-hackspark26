import { api } from '../api/client'
import { useCaseStore } from '../state/caseStore'
import { useHealthStore } from '../state/healthStore'
import { useRunStore } from '../state/runStore'
import { useUiStore } from '../state/uiStore'

let started = false

export async function bootstrap(): Promise<void> {
  if (started) return
  started = true

  useHealthStore.getState().startPolling()

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
