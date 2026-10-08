import { Logo } from '../design/icons'
import { useElapsedMs } from '../state/useElapsed'
import { useHealthStore } from '../state/healthStore'
import { useRunStore } from '../state/runStore'
import { useUiStore } from '../state/uiStore'
import { fmtClock, fmtClockTenths } from '../view/format'
import { formatModel, healthViews } from '../view/chrome'
import { meterViews } from '../view/meters'

export function TopBar() {
  const health = useHealthStore((s) => s.health)
  const reachable = useHealthStore((s) => s.backendReachable)
  const state = useRunStore((s) => s.state)
  const status = useRunStore((s) => s.status)
  const preset = useUiStore((s) => s.budgetPreset)
  const elapsedMs = useElapsedMs()

  const chips = healthViews(health, reachable)
  const live = health && reachable !== false ? health : null
  const model = state.model ?? live?.modelServer.model ?? 'qwen3-8b'
  const isLive = state.mode === 'live' && status === 'streaming'
  const isRecorded = state.mode === 'demo'
  const meters = meterViews({ s: state, status, preset, elapsedMs, available: reachable !== false })
  const clock = reachable === false ? '--:--' : state.outcome !== null ? fmtClockTenths(elapsedMs) : fmtClock(elapsedMs)

  return (
    <header className="tb">
      <div className="tb-l">
        <div className="logo">
          <Logo />
          <span className="wordmark">Greenline</span>
        </div>
        <span className="sep" />
        <span className="chip mono">{formatModel(model)} · local</span>
        {chips.map((c) => (
          <span key={c.label} className="chip" title={c.tip}>
            <span
              className="dot"
              style={{ background: c.ok === null ? 'var(--muted)' : c.ok ? 'var(--brand)' : 'var(--danger)' }}
            />
            {c.label}
          </span>
        ))}
      </div>
      <div className="tb-r">
        {isLive && (
          <span className="live">
            <span className="live-dot" />
            LIVE
          </span>
        )}
        {isRecorded && (
          <span className="recorded">
            RECORDED <span>re-streamed real run</span>
          </span>
        )}
        <div className="timer">
          <span className="lbl">Elapsed</span>
          <span className="timer-v mono">{clock}</span>
        </div>
        <span className="sep" />
        {meters.map((m) => (
          <div key={m.label} className="meter">
            <div className="meter-top">
              <span className="lbl">{m.label}</span>
              <span className="meter-v mono" style={{ color: m.valColor, fontWeight: m.alarm ? 700 : undefined }}>
                {m.val}
                <span className="muted">/{m.cap}</span>
              </span>
            </div>
            <div className="track">
              <div className="fill" style={{ width: `${m.pct}%`, background: m.fillColor }} />
            </div>
          </div>
        ))}
        <span className="sep" />
        <button className="btn" type="button" onClick={() => useUiStore.getState().setScoreboardOpen(true)}>
          Scoreboard <kbd>S</kbd>
        </button>
      </div>
    </header>
  )
}
