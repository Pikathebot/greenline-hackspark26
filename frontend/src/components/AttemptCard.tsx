import { Chevron } from '../design/icons'
import type { AttemptView } from '../view/patch'
import { CheckChips } from './CriticRow'
import { DiffBlock } from './DiffBlock'

function Header({ a }: { a: AttemptView }) {
  if (a.running) {
    return (
      <div className="att-h">
        <span className="pulse" style={{ margin: '0 4px 0 2px' }} />
        Attempt {a.n}
        <span className="mono muted" style={{ fontWeight: 400, fontSize: 13 }}>
          {a.note}
        </span>
      </div>
    )
  }
  const bad = a.state === 'red' || a.state === 'vetoed'
  return (
    <div className="att-h">
      <Chevron style={{ color: 'var(--muted)' }} />
      Attempt {a.n}
      <span
        className="reason"
        style={bad ? { color: 'var(--danger)', borderColor: 'var(--danger)' } : { color: 'var(--brand-ink)', borderColor: 'var(--brand)' }}
      >
        {a.state}
      </span>
      <span className="muted" style={{ fontWeight: 400 }}>
        {a.note}
      </span>
    </div>
  )
}

function Body({ a }: { a: AttemptView }) {
  if (a.running) {
    return (
      <p className="art-body" style={{ marginTop: 6 }}>
        {a.body}
      </p>
    )
  }
  return (
    <>
      {a.diff.length > 0 && <DiffBlock file={a.file} lines={a.diff} style={{ marginBottom: 8 }} />}
      {a.vote && <CheckChips checks={a.vote.checks} />}
    </>
  )
}

/** expanded: a plain card (patch loop in progress); collapsed: <details> under the PR/escalation. */
export function AttemptCard({ a, collapsed }: { a: AttemptView; collapsed?: boolean }) {
  const style = a.running ? { borderColor: 'var(--info)', background: 'var(--info-tint)' } : undefined
  if (collapsed) {
    return (
      <details className="att" style={style}>
        <summary style={{ cursor: 'pointer', listStyle: 'none' }}>
          <Header a={a} />
        </summary>
        <div style={{ marginTop: 8 }}>
          <Body a={a} />
        </div>
      </details>
    )
  }
  return (
    <div className="att" style={style}>
      <Header a={a} />
      <Body a={a} />
    </div>
  )
}
