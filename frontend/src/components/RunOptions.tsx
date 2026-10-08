import { Play } from '../design/icons'
import { useCaseStore } from '../state/caseStore'
import { useHealthStore } from '../state/healthStore'
import { useRunStore } from '../state/runStore'
import { useUiStore } from '../state/uiStore'
import { runButtonView } from '../view/chrome'

const SEG_ON = {
  background: 'var(--surface-2)',
  color: 'var(--text)',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
}
const SEG_ON_WARN = {
  background: 'var(--warn-tint)',
  color: 'var(--warn)',
  boxShadow: 'inset 0 0 0 1px var(--warn)',
}

/** The one case with an alternate recording (backend 18387f3). */
const CRITIC_REJECT_CASE = '0139'
const CRITIC_REJECT = 'critic-reject'

export function RunOptions() {
  const budget = useUiStore((s) => s.budgetPreset)
  const mode = useUiStore((s) => s.mode)
  const recording = useUiStore((s) => s.recording)
  const selectedId = useUiStore((s) => s.selectedCaseId)
  const selected = useCaseStore((s) => s.cases.find((c) => c.id === selectedId) ?? null)
  const reachable = useHealthStore((s) => s.backendReachable)
  const status = useRunStore((s) => s.status)
  const run = runButtonView({ reachable, status, caseId: selectedId })
  const ui = useUiStore.getState

  return (
    <div className="opts">
      <div className="opt-row">
        <span className="lbl">
          Budget <kbd>T</kbd>
        </span>
        <div className="seg">
          <button type="button" style={budget === 'normal' ? SEG_ON : undefined} onClick={() => ui().setBudget('normal')}>
            Normal
          </button>
          <button
            type="button"
            title="Caps model calls at 4 and sandbox runs at 3, to show budget exhaustion."
            style={budget === 'tight' ? SEG_ON_WARN : undefined}
            onClick={() => ui().setBudget('tight')}
          >
            Tight
          </button>
        </div>
      </div>
      <div className="opt-row">
        <span className="lbl">
          Mode <kbd>D</kbd>
        </span>
        <div className="seg">
          <button type="button" style={mode === 'live' ? SEG_ON : undefined} onClick={() => ui().setMode('live')}>
            Live
          </button>
          <button
            type="button"
            disabled={selected !== null && !selected.hasDemoRun}
            style={mode === 'demo' ? SEG_ON_WARN : undefined}
            onClick={() => ui().setMode('demo')}
          >
            Recorded
          </button>
        </div>
      </div>
      {mode === 'demo' && selectedId === CRITIC_REJECT_CASE && (
        <div className="opt-row">
          <span className="lbl">Recording</span>
          <div className="seg">
            <button type="button" style={recording === null ? SEG_ON : undefined} onClick={() => ui().setRecording(null)}>
              Default
            </button>
            <button
              type="button"
              title="Replays a real run where the Critic rejects the patch and the case escalates."
              style={recording === CRITIC_REJECT ? SEG_ON_WARN : undefined}
              onClick={() => ui().setRecording(CRITIC_REJECT)}
            >
              Critic reject
            </button>
          </div>
        </div>
      )}
      <button
        className="run"
        type="button"
        disabled={!run.enabled}
        style={
          run.enabled
            ? { background: 'var(--brand)', color: 'var(--on-accent)' }
            : {
                background: 'var(--surface-2)',
                color: 'var(--muted)',
                cursor: 'not-allowed',
                boxShadow: 'inset 0 0 0 1px var(--border)',
              }
        }
        onClick={() => {
          if (!selectedId) return
          const useRecording = mode === 'demo' && selectedId === CRITIC_REJECT_CASE && recording
          void useRunStore.getState().startRun(selectedId, useRecording ? { mode, budget, recording } : { mode, budget })
        }}
      >
        <Play />
        {run.label} <kbd>Enter</kbd>
      </button>
      <div className="keys">
        <span>
          <kbd>1</kbd>–<kbd>6</kbd> case
        </span>
        <span>
          <kbd>R</kbd> run
        </span>
        <span>
          <kbd>E</kbd> export
        </span>
        <span>
          <kbd>Esc</kbd> close
        </span>
      </div>
    </div>
  )
}
