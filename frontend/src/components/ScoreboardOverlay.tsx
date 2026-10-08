import { useEffect } from 'react'
import { useScoreboardStore } from '../state/scoreboardStore'
import { useUiStore } from '../state/uiStore'
import { TONE } from '../view/consts'
import { scoreboardView, type CellKind } from '../view/scoreboard'

const CELL_STYLE: Record<CellKind, React.CSSProperties> = {
  diag: { color: TONE.brand.c, background: TONE.brand.bg, border: `1px solid ${TONE.brand.b}` },
  off: { color: TONE.warn.c, background: TONE.warn.bg, border: `1px solid ${TONE.warn.b}` },
  zero: { color: 'var(--muted)', background: 'var(--bg)', border: '1px solid var(--border)' },
}

export function ScoreboardOverlay() {
  const open = useUiStore((s) => s.scoreboardOpen)
  const data = useScoreboardStore((s) => s.data)
  const status = useScoreboardStore((s) => s.status)

  useEffect(() => {
    if (open) void useScoreboardStore.getState().refresh()
  }, [open])

  if (!open) return null
  const close = () => useUiStore.getState().setScoreboardOpen(false)
  const v = data ? scoreboardView(data) : null

  return (
    <div className="sb-back" onClick={close}>
      <div className="sb" role="dialog" aria-label="Scoreboard" onClick={(e) => e.stopPropagation()}>
        <div className="sb-h">
          <span style={{ fontSize: 24, fontWeight: 600 }}>Scoreboard</span>
          {v && <span className="chip mono">{v.chip}</span>}
          {status === 'loading' && <span className="muted">loading…</span>}
          <span className="grow" />
          <button className="btn" type="button" onClick={close}>
            Close <kbd>Esc</kbd>
          </button>
        </div>
        {status === 'error' && (
          <p className="muted" style={{ margin: '0 0 12px' }}>
            {v ? 'Could not refresh; showing the last numbers.' : 'Scoreboard unavailable: backend unreachable.'}
          </p>
        )}
        {v && (
          <>
            <div className="tiles">
              {v.tiles.map((t) => (
                <div className="tile" key={t.label}>
                  <div className="lbl">{t.label}</div>
                  <div className="tile-v mono">{t.value}</div>
                  <div className="tile-s">{t.sub}</div>
                </div>
              ))}
            </div>
            <div className="sb-grid">
              <div className="tile" style={{ padding: '16px 18px' }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 12 }}>
                  <span className="h">Triage confusion matrix</span>
                  <span className="muted" style={{ fontSize: 13 }}>
                    rows: actual class · columns: predicted
                  </span>
                </div>
                <div className="mx">
                  <span />
                  {v.classes.map((c) => (
                    <span className="mx-l" key={c}>
                      {c}
                    </span>
                  ))}
                  {v.matrix.map((row) => (
                    <MatrixRow key={row.label} row={row} />
                  ))}
                </div>
                {v.footnote && (
                  <div className="muted" style={{ fontSize: 13, marginTop: 12 }}>
                    {v.footnote}
                  </div>
                )}
              </div>
              <div className="tile" style={{ padding: '16px 18px' }}>
                <div className="h" style={{ marginBottom: 6 }}>
                  Per case
                </div>
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Case</th>
                      <th>Runs</th>
                      <th>Last outcome</th>
                      <th style={{ textAlign: 'right' }}>Median</th>
                    </tr>
                  </thead>
                  <tbody>
                    {v.rows.map((r) => {
                      const t = TONE[r.outcomeTone]
                      return (
                        <tr key={r.id}>
                          <td className="mono">#{r.id}</td>
                          <td className="mono">{r.runs}</td>
                          <td>
                            <span className="pill" style={{ color: t.c, background: t.bg, borderColor: t.b, marginLeft: 0 }}>
                              {r.outcome}
                            </span>
                          </td>
                          <td className="mono" style={{ textAlign: 'right' }}>
                            {r.median}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function MatrixRow({ row }: { row: ReturnType<typeof scoreboardView>['matrix'][number] }) {
  return (
    <>
      <span className="mx-l" style={{ justifyContent: 'flex-start' }}>
        {row.label}
      </span>
      {row.cells.map((c, i) => (
        <span className="mx-c mono" key={i} style={CELL_STYLE[c.kind]}>
          {c.n}
        </span>
      ))}
    </>
  )
}
