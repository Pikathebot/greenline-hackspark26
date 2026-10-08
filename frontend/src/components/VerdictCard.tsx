import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useRunStore } from '../state/runStore'
import { TONE } from '../view/consts'
import { verdictView } from '../view/panels'

export function VerdictCard() {
  const s = useRunStore((st) => st.state)
  const status = useRunStore((st) => st.status)
  const runId = useRunStore((st) => st.runId)
  const v = verdictView({ s, status })
  const [open, setOpen] = useState(false)
  useEffect(() => setOpen(false), [runId])
  const ratRef = useRef<HTMLParagraphElement>(null)
  const [clipped, setClipped] = useState(false)
  const rationale = v.kind === 'verdict' ? v.rationale : ''
  useLayoutEffect(() => {
    const el = ratRef.current
    if (el && !open) setClipped(el.scrollHeight > el.clientHeight + 1)
  }, [rationale, open])

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
          <p ref={ratRef} className={open ? 'rat' : 'rat rat-clamp'}>
            {v.rationale}
          </p>
          {(clipped || open) && (
            <button type="button" className="more" onClick={() => setOpen(!open)}>
              {open ? 'less' : 'more'}
            </button>
          )}
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
