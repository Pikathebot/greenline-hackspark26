import { History } from '../design/icons'
import { useCaseStore } from '../state/caseStore'
import { useRunStore } from '../state/runStore'
import { memoryView, type BarView } from '../view/memory'

function CostBars({ bars, refLabel }: { bars: BarView[]; refLabel: string }) {
  return (
    <div className="bars">
      {bars.map((b) => (
        <div key={b.label} className="bar-r">
          <span className="lbl">{b.label}</span>
          <div className="bar-pair">
            <span className="bar-line">
              <span className="bar" style={{ width: b.aPx, background: 'var(--brand)' }} />
              <span className="mono">{b.a}</span>
              <span className="muted">this run</span>
            </span>
            <span className="bar-line">
              <span className="bar" style={{ width: b.bPx, background: 'var(--muted)' }} />
              <span className="mono">{b.b}</span>
              <span className="muted">{refLabel}</span>
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

export function MemoryCallout() {
  const s = useRunStore((st) => st.state)
  const cases = useCaseStore((st) => st.cases)
  const m = memoryView({ s, cases })
  if (!m) return null

  return (
    <div className="mem" style={m.bars ? undefined : { gridTemplateColumns: 'minmax(0,1fr)' }}>
      <div>
        <div className="mem-h">
          <History style={{ color: 'var(--brand-ink)' }} />
          Recalled {m.ref}
          <span className="chip mono" style={{ height: 26, fontSize: 13 }}>
            similarity {m.sim}
          </span>
        </div>
        <div className="mem-t">{m.text}</div>
      </div>
      {m.bars && <CostBars bars={m.bars} refLabel={m.ref} />}
    </div>
  )
}
