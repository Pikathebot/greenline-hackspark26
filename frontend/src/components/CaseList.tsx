import { useCaseStore } from '../state/caseStore'
import { useHealthStore } from '../state/healthStore'
import { useUiStore } from '../state/uiStore'
import { caseRows } from '../view/chrome'
import { TONE } from '../view/consts'

export function CaseList() {
  const cases = useCaseStore((s) => s.cases)
  const selectedId = useUiStore((s) => s.selectedCaseId)
  const reachable = useHealthStore((s) => s.backendReachable)
  const offline = reachable === false
  const rows = caseRows(cases, selectedId)

  return (
    <>
      <div className="ph">
        <span className="h">Failure cases</span>
        <span className="mono muted">{offline || rows.length === 0 ? '–' : rows.length}</span>
      </div>
      <div className="cases">
        {offline || rows.length === 0 ? (
          <>
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} className="skel" />
            ))}
            <p className="hint" style={{ margin: '8px 4px 0' }}>
              Cases load from /api/cases once the backend answers.
            </p>
          </>
        ) : (
          rows.map((c) => {
            const t = TONE[c.pillTone]
            return (
              <button
                key={c.id}
                className="case"
                type="button"
                title={c.beat}
                style={c.selected ? { background: 'var(--surface-2)', borderColor: 'var(--border-strong)' } : undefined}
                onClick={() => useUiStore.getState().selectCase(c.id)}
              >
                <span className="case-r1">
                  <span className="cid mono" style={c.selected ? { color: 'var(--brand-ink)' } : undefined}>
                    #{c.id}
                  </span>
                  <span className="cls">{c.cls}</span>
                  <span className="pill" style={{ color: t.c, background: t.bg, borderColor: t.b }}>
                    {c.pillLabel}
                  </span>
                </span>
                <span className="case-title mono">{c.title}</span>
                <span className="case-meta">{c.meta}</span>
              </button>
            )
          })
        )}
      </div>
    </>
  )
}
