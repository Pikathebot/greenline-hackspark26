import { useRunStore } from '../state/runStore'
import { TONE } from '../view/consts'
import { verdictView } from '../view/panels'

export function VerdictCard() {
  const s = useRunStore((st) => st.state)
  const status = useRunStore((st) => st.status)
  const v = verdictView({ s, status })

  return (
    <section className="card verdict" aria-label="Verdict">
      <div className="card-h">
        <span className="h">Verdict</span>
        <span className="muted" style={{ fontSize: 13 }}>
          confidence computed from evidence
        </span>
      </div>
      {v.kind === 'verdict' ? (
        <>
          <div className="v-word" style={{ color: 'var(--text)' }}>
            {v.word}
          </div>
          <div className="conf">
            <div className="track">
              <div className="fill" style={{ width: `${v.fillPct}%`, background: 'var(--brand)' }} />
            </div>
            <span className="pct mono">{v.pct}</span>
          </div>
          <p className="rat">{v.rationale}</p>
        </>
      ) : (
        <>
          <div className="v-ph" style={{ color: TONE[v.tone].c }}>
            {v.title}
          </div>
          <p className="v-sub">{v.sub}</p>
        </>
      )}
    </section>
  )
}
