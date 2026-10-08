import type { CSSProperties } from 'react'
import { Check, Circle, Cross, Dash } from '../design/icons'
import { useRunStore } from '../state/runStore'
import { TONE } from '../view/consts'
import { arcViews, nodeViews, type ArcView, type NodeView } from '../view/graph'

const LEGEND: [string, CSSProperties][] = [
  ['waiting', { borderColor: 'var(--border-strong)' }],
  ['running', { borderColor: 'var(--info)', background: 'var(--info-tint)' }],
  ['done', { borderColor: 'var(--brand)', background: 'var(--brand-tint)' }],
  ['skipped', { borderColor: 'var(--muted)', borderStyle: 'dashed' }],
  ['failed / blocked', { borderColor: 'var(--danger)', background: 'var(--danger-tint)' }],
]

function nodeStyles(n: NodeView, col: number) {
  const style: CSSProperties = { gridColumn: col }
  let nameColor: string | undefined
  let detailColor = 'var(--muted)'
  let iconColor = 'var(--muted)'
  if (n.status === 'idle') nameColor = 'var(--muted)'
  if (n.status === 'active') {
    Object.assign(style, { borderColor: 'var(--info)', background: 'var(--info-tint)', boxShadow: '0 0 0 3px var(--info-tint)' })
    detailColor = 'var(--info)'
  }
  if (n.status === 'ok') {
    style.borderColor = 'var(--brand)'
    iconColor = 'var(--brand-ink)'
  }
  if (n.status === 'skip') {
    Object.assign(style, { borderStyle: 'dashed', borderColor: 'var(--muted)', background: 'transparent' })
    nameColor = 'var(--muted)'
  }
  if (n.status === 'fail') {
    Object.assign(style, { borderColor: 'var(--danger)', background: 'var(--danger-tint)' })
    iconColor = 'var(--danger)'
    detailColor = 'var(--danger)'
  }
  return { style, nameColor, detailColor, iconColor }
}

function arcStyle(a: ArcView): { box: CSSProperties; label: CSSProperties } {
  const t = TONE[a.tone]
  return {
    box: {
      gridColumn: `${a.from + 1} / span ${a.span}`,
      marginInline: `calc((100% - ${a.span - 1} * var(--gap)) / ${2 * a.span})`,
      color: a.on ? t.b : 'var(--border-strong)',
      borderStyle: a.on ? 'solid' : 'dashed',
    },
    label: a.on
      ? { color: t.c, borderColor: t.b, fontWeight: 600 }
      : { color: 'var(--muted)', borderColor: 'var(--border)' },
  }
}

function Arc({ a, kind }: { a: ArcView; kind: 'top' | 'bot' }) {
  const s = arcStyle(a)
  return (
    <div className={`arc arc-${kind}`} style={s.box}>
      <span className={kind === 'top' ? 'head-down' : 'head-up'} />
      <span className="arc-lbl" style={s.label}>
        {a.label}
      </span>
    </div>
  )
}

function Icon({ status, color }: { status: NodeView['status']; color: string }) {
  const style = { color }
  if (status === 'active') return <span className="pulse" />
  if (status === 'ok') return <Check style={style} />
  if (status === 'skip') return <Dash style={style} />
  if (status === 'fail') return <Cross style={style} />
  return <Circle style={style} />
}

export function AgentGraph() {
  const s = useRunStore((st) => st.state)
  const nodes = nodeViews(s)
  const arcs = arcViews(s)

  return (
    <section className="graph" aria-label="Agent graph">
      <div className="graph-h">
        <span className="h">Agent crew</span>
        <span className="muted" style={{ fontSize: 14 }}>
          7 agents · one local model · every rerun in a fresh sandbox
        </span>
        <span className="legend">
          {LEGEND.map(([label, style]) => (
            <span key={label}>
              <i className="sw" style={style} />
              {label}
            </span>
          ))}
        </span>
      </div>
      <div className="g-grid">
        <Arc a={arcs.loop} kind="top" />
        {nodes.map((n, i) => {
          const st = nodeStyles(n, i + 1)
          return (
            <div key={n.id} className="node" style={st.style} title={n.title || undefined}>
              <div className="node-top">
                <span className="nicon" style={{ color: st.iconColor }}>
                  <Icon status={n.status} color={st.iconColor} />
                </span>
                <span className="nstep mono">{n.step}</span>
              </div>
              <div className="nname" style={{ color: st.nameColor }}>
                {n.name}
              </div>
              <div className="nrole">{n.role}</div>
              <div className="ndetail mono" style={{ color: st.detailColor }}>
                {n.detail}
              </div>
              {n.connColor && (
                <span className="conn" style={{ width: 'var(--gap)', background: n.connColor, color: n.connColor }} />
              )}
              {n.barrier && (
                <>
                  <span className="barrier" style={{ left: 'calc(100% + var(--gap) / 2)' }} />
                  <span className="bar-lbl" style={{ left: 'calc(100% + var(--gap) / 2)' }}>
                    BLOCKED<span>would edit a test</span>
                  </span>
                </>
              )}
            </div>
          )
        })}
        {arcs.bypass.show && <Arc a={arcs.bypass} kind="bot" />}
        <Arc a={arcs.esc} kind="bot" />
      </div>
    </section>
  )
}
