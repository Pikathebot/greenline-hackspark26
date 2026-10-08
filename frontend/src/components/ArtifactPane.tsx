import { Doc, Person } from '../design/icons'
import { useRunStore } from '../state/runStore'
import { TONE } from '../view/consts'
import { artifactView } from '../view/panels'

export function ArtifactPane() {
  const a = artifactView(useRunStore((s) => s.state))

  return (
    <section className="card art" aria-label="Artifact">
      <div className="card-h">
        <span className="h">Artifact</span>
        <span className="muted" style={{ fontSize: 13, marginLeft: 'auto' }}>
          {a.hint}
        </span>
      </div>
      {a.kind === 'empty' && (
        <div className="art-empty">
          <Doc size={26} />
          The draft PR or the escalation note appears here when the Reporter finishes.
        </div>
      )}
      {a.kind === 'escalation' && (
        <>
          <div className="esc-h" style={{ color: 'var(--warn)' }}>
            <Person />
            {a.header}
          </div>
          <div style={{ marginTop: 8 }}>
            <span
              className="reason"
              style={{
                color: TONE[a.reasonTone].c,
                borderColor: TONE[a.reasonTone].b,
                background: TONE[a.reasonTone].bg,
              }}
            >
              {a.reason}
            </span>
          </div>
          <div className="art-title">{a.title}</div>
          <p className="art-body">{a.body}</p>
        </>
      )}
      {a.kind === 'pr' && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {a.dryRun && (
              <span className="tag" style={{ color: 'var(--brand-ink)', borderColor: 'var(--brand)' }}>
                draft · dry-run
              </span>
            )}
            {a.prUrl && (
              <span className="mono muted" style={{ fontSize: 13 }}>
                {a.prUrl}
              </span>
            )}
          </div>
          <div className="art-title" style={{ marginTop: 10 }}>
            {a.title}
          </div>
          <p className="art-body">{a.body}</p>
        </>
      )}
    </section>
  )
}
