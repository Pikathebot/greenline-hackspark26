import { useCaseStore } from '../state/caseStore'
import { useHealthStore } from '../state/healthStore'
import { useRunStore } from '../state/runStore'
import { useUiStore } from '../state/uiStore'
import { narrationView } from '../view/chrome'
import { TONE } from '../view/consts'

export function Narration() {
  const s = useRunStore((st) => st.state)
  const status = useRunStore((st) => st.status)
  const reachable = useHealthStore((st) => st.backendReachable)
  const selectedId = useUiStore((st) => st.selectedCaseId)
  const selectedCase = useCaseStore((st) => st.cases.find((c) => c.id === selectedId) ?? null)
  const n = narrationView({ s, status, reachable, selectedCase })
  const t = TONE.info

  return (
    <div className="narr" aria-live="polite">
      {n.tag && (
        <span className="narr-tag" style={{ color: t.c, borderColor: t.b, background: t.bg }}>
          {n.tag}
        </span>
      )}
      <span className="narr-text">{n.text}</span>
    </div>
  )
}
