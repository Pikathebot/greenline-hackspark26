import type { CheckView } from '../view/patch'
import type { VoteView } from '../view/patch'
import { Check, Cross } from '../design/icons'

export function CheckChips({ checks }: { checks: CheckView[] }) {
  if (checks.length === 0) return null
  return (
    <div className="votes">
      {checks.map((k) => (
        <span
          key={k.name}
          className="chk"
          title={k.detail || undefined}
          style={
            k.passed
              ? { color: 'var(--brand-ink)', borderColor: 'var(--brand)' }
              : { color: 'var(--danger)', borderColor: 'var(--danger)', background: 'var(--danger-tint)' }
          }
        >
          {k.passed ? '✓' : '✕'} {k.name}
        </span>
      ))}
    </div>
  )
}

export function CriticRow({ vote }: { vote: VoteView }) {
  return (
    <>
      <div className="votes">
        <span className="lbl" style={{ marginRight: 2 }}>
          Critic
        </span>
        {vote.samples.map((s, i) => (
          <span
            key={i}
            className="vote"
            style={
              s === 'approve'
                ? { background: 'var(--brand)', color: 'var(--on-accent)' }
                : { background: 'var(--danger)', color: 'var(--on-danger)' }
            }
          >
            {s === 'approve' ? <Check size={15} style={{ strokeWidth: 2.6 }} /> : <Cross size={15} style={{ strokeWidth: 2.6 }} />}
          </span>
        ))}
        <span style={{ fontWeight: 600, color: vote.approved ? 'var(--brand-ink)' : 'var(--danger)' }}>{vote.text}</span>
      </div>
      <CheckChips checks={vote.checks} />
    </>
  )
}
