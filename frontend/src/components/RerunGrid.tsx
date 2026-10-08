import { Check, Cross } from '../design/icons'
import type { CellState, FeedItem } from '../view/feed'

const CELL_STYLE: Record<CellState, React.CSSProperties> = {
  pass: { borderColor: 'var(--brand)', background: 'var(--brand-tint)', color: 'var(--brand-ink)' },
  fail: { borderColor: 'var(--danger)', background: 'var(--danger-tint)', color: 'var(--danger)' },
  cap: { borderColor: 'var(--warn)', borderStyle: 'dashed', color: 'var(--warn)' },
  pending: { borderColor: 'var(--border-strong)', borderStyle: 'dashed', color: 'var(--muted)' },
}

export function RerunGrid({ item }: { item: Extract<FeedItem, { kind: 'grid' }> }) {
  return (
    <div className="rr">
      <div className="rr-h">
        <span className="en">reproducer</span>
        <span style={{ fontWeight: 600 }}>Reruns</span>
        <span className="muted" style={{ fontSize: 14 }}>
          fresh container each · network off
        </span>
        <span className="grow" />
        <span className="mono" style={{ fontSize: 16, fontWeight: 500 }}>
          {item.summary}
        </span>
      </div>
      <div
        className="rr-cells"
        style={{ gridTemplateColumns: `repeat(${item.cells.length}, minmax(0, ${item.cellMin}))` }}
      >
        {item.cells.map((c) => (
          <div key={c.n} className="cell" style={CELL_STYLE[c.state]}>
            {c.state === 'pass' && <Check />}
            {c.state === 'fail' && <Cross />}
            {c.state === 'cap' && (
              <span className="mono" style={{ fontSize: 12 }}>
                cap
              </span>
            )}
            <span className="cell-n mono">{c.n}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
