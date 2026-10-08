import { ShieldClear, ShieldFired, ShieldIdle } from '../design/icons'
import { useRunStore } from '../state/runStore'
import { railViews } from '../view/panels'

export function GuardrailList() {
  const { rails, summary } = railViews(useRunStore((s) => s.state))

  return (
    <section className="card rails" aria-label="Guardrails">
      <div className="card-h">
        <span className="h">Guardrails</span>
        <span className="muted" style={{ fontSize: 13 }}>
          {summary}
        </span>
      </div>
      <div className="rail-list">
        {rails.map((r) => {
          const fired = r.state === 'fired'
          const clear = r.state === 'clear'
          const iconColor = fired ? 'var(--danger)' : clear ? 'var(--brand-ink)' : 'var(--muted)'
          return (
            <div
              key={r.id}
              className="rail"
              style={
                fired
                  ? { borderColor: 'var(--danger)', background: 'var(--danger-tint)', padding: '11px 10px' }
                  : undefined
              }
            >
              <span style={{ color: iconColor, display: 'flex' }}>
                {fired ? <ShieldFired /> : clear ? <ShieldClear /> : <ShieldIdle />}
              </span>
              <span
                className="rid mono"
                style={r.state === 'idle' ? { color: 'var(--muted)' } : fired ? { fontWeight: 700 } : undefined}
              >
                {r.id}
              </span>
              {r.state !== 'idle' && (
                <span
                  className="rstate"
                  style={
                    fired
                      ? { background: 'var(--danger)', color: 'var(--on-danger)', fontSize: 13, padding: '4px 10px' }
                      : { color: 'var(--brand-ink)', background: 'var(--brand-tint)' }
                  }
                >
                  {fired ? 'Blocked' : 'Clear'}
                </span>
              )}
              {r.note && (
                <span
                  className="rnote"
                  style={fired ? { color: 'var(--text)', fontSize: 14.5 } : { color: 'var(--muted)' }}
                >
                  {r.note}
                </span>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
