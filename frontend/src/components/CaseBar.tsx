import { useCaseStore } from '../state/caseStore'
import { useUiStore } from '../state/uiStore'

export function CaseBar() {
  const selectedId = useUiStore((s) => s.selectedCaseId)
  const c = useCaseStore((s) => s.cases.find((x) => x.id === selectedId) ?? null)
  return (
    <div className="casebar">
      {c ? (
        <>
          <span className="mono" style={{ fontSize: 17, fontWeight: 600 }}>
            #{c.id}
          </span>
          <span className="mono" style={{ fontSize: 17, overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {c.title}
          </span>
          <span className="grow" />
          <span className="mono muted" style={{ fontSize: 14 }}>
            {c.repo} · {c.branch}
          </span>
        </>
      ) : (
        <span className="mono" style={{ fontSize: 17 }}>
          No case selected
        </span>
      )}
    </div>
  )
}
