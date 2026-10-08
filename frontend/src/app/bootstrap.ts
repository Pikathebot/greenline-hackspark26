import { api } from '../api/client'
import { useCaseStore } from '../state/caseStore'
import { useHealthStore } from '../state/healthStore'
import { useRunStore } from '../state/runStore'
import { useUiStore } from '../state/uiStore'
import { shouldAttachActive } from './autoAttach'
import { recallRun, rememberRun } from './runCache'
import { caseSwitchAction } from './runReset'

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

  // Remember each case's last finished run for this session.
  useRunStore.subscribe((run, prev) => {
    if (run.status === 'done' && prev.status !== 'done' && run.state.caseId) {
      rememberRun(run.state.caseId, { runId: run.runId, events: run.events, state: run.state })
    }
  })

  // Picking another case: bring back its last finished run if it has one, else clear the old case's
  // panels so they never sit under the new case header.
  useUiStore.subscribe((ui, prev) => {
    if (ui.selectedCaseId === prev.selectedCaseId) return
    const run = useRunStore.getState()
    const cached = recallRun(ui.selectedCaseId)
    const action = caseSwitchAction({
      status: run.status,
      runCaseId: run.state.caseId,
      selectedCaseId: ui.selectedCaseId,
      hasCached: cached !== null,
    })
    if (action === 'restore' && cached) {
      useRunStore.setState({ ...cached, status: 'done', connection: 'none', problem: null })
    } else if (action === 'reset') {
      run.reset()
    }
  })

  await useCaseStore.getState().refresh()
  const { cases } = useCaseStore.getState()
  const ui = useUiStore.getState()
  if (ui.selectedCaseId === null && cases.length > 0) {
    ui.selectCase(cases.find((c) => c.id === '0142')?.id ?? cases[0]!.id)
  }

  // Re-attach to a run that is already in progress (e.g. after a page refresh), and keep watching:
  // a case detected from a red GitHub build shows up, and its run starts, without a click.
  const attachActive = async () => {
    try {
      const active = await api.activeRun()
      const run = useRunStore.getState()
      if (active && shouldAttachActive({ status: run.status, currentRunId: run.runId, activeRunId: active.runId })) {
        await useCaseStore.getState().refresh()
        useUiStore.getState().selectCase(active.caseId)
        run.attach(active.runId)
      }
    } catch {
      // health polling already reports the backend being down
    }
  }
  await attachActive()
  setInterval(() => {
    void useCaseStore.getState().refresh()
    void attachActive()
  }, 5000)
}
