import { triggerDownload } from '../app/download'
import { Download, Person } from '../design/icons'
import { useCaseStore } from '../state/caseStore'
import { useRunStore } from '../state/runStore'
import { AttemptCard } from './AttemptCard'
import { CriticRow } from './CriticRow'
import { DiffBlock } from './DiffBlock'
import { TONE } from '../view/consts'
import { artifactView } from '../view/panels'
import { attemptViews } from '../view/patch'
import { buildReportMarkdown, canDownload, reportFilename } from '../view/report'

export function ArtifactPane() {
  const state = useRunStore((s) => s.state)
  const caseInfo = useCaseStore((s) => s.cases.find((c) => c.id === state.caseId) ?? null)
  const a = artifactView(state)
  const { attempts, acceptedN } = attemptViews(state)
  const earlier = attempts.filter((x) => x.n !== acceptedN && !x.running)

  return (
    <section className="card art" aria-label="Artifact">
      <div className="card-h">
        <span className="h">Artifact</span>
        <span className="muted" style={{ fontSize: 13, marginLeft: 'auto' }}>
          {a.hint}
        </span>
        {canDownload(state) && (
          <button
            className="btn"
            type="button"
            title="Download this report as Markdown"
            style={{ height: 32, fontSize: 14, padding: '0 8px 0 10px' }}
            onClick={() =>
              triggerDownload(
                reportFilename(state),
                buildReportMarkdown(
                  state,
                  caseInfo
                    ? { id: caseInfo.id, title: caseInfo.title, repo: caseInfo.repo, branch: caseInfo.branch }
                    : null,
                ),
              )
            }
          >
            <Download size={17} />
            Download .md <kbd>E</kbd>
          </button>
        )}
      </div>
      {a.kind === 'empty' && (
        <p className="muted" style={{ margin: 0, fontSize: 14 }}>
          Draft PR or escalation note appears here.
        </p>
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
          {a.diff.length > 0 && <DiffBlock file={a.file} lines={a.diff} />}
          {a.vote && <CriticRow vote={a.vote} />}
          <p className="art-body">{a.body}</p>
        </>
      )}
      {a.kind === 'loop' && attempts.map((x) => <AttemptCard key={`${x.n}-${x.running}`} a={x} />)}
      {(a.kind === 'pr' || a.kind === 'escalation') && earlier.length > 0 && (
        <>
          <div className="lbl" style={{ marginTop: 14 }}>
            Earlier attempts
          </div>
          {earlier.map((x) => (
            <AttemptCard key={x.n} a={x} collapsed />
          ))}
        </>
      )}
    </section>
  )
}
