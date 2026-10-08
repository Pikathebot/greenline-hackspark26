import { useEffect, useRef, useState } from 'react'
import { useRunStore } from '../state/runStore'
import { buildFeed, type RowStyle } from '../view/feed'
import { RerunGrid } from './RerunGrid'

const ROW_STYLE: Record<RowStyle, { row?: React.CSSProperties; text?: React.CSSProperties }> = {
  normal: {},
  citation: { text: { color: 'var(--text)' } },
  danger: { row: { background: 'var(--danger-tint)' }, text: { color: 'var(--danger)', fontWeight: 500 } },
  newest: { row: { background: 'var(--info-tint)' } },
}

export function EvidenceFeed() {
  const s = useRunStore((st) => st.state)
  const running = useRunStore((st) => st.status === 'streaming')
  const { items, lineCount } = buildFeed(s, running)
  const listRef = useRef<HTMLDivElement>(null)
  const pinned = useRef(true)
  const runId = useRunStore((st) => st.runId)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  useEffect(() => setExpanded(new Set()), [runId])

  useEffect(() => {
    const el = listRef.current
    if (el && pinned.current) el.scrollTop = el.scrollHeight
  }, [items.length, s.rerun?.ticks.length])

  return (
    <section className="ev" aria-label="Evidence">
      <div className="ev-h">
        <span className="h">Evidence</span>
        <span className="muted" style={{ fontSize: 14 }}>
          {lineCount ? `${lineCount} items · newest at the bottom` : ''}
        </span>
      </div>
      <div
        className="ev-list"
        ref={listRef}
        onScroll={(e) => {
          const el = e.currentTarget
          pinned.current = el.scrollTop + el.clientHeight >= el.scrollHeight - 24
        }}
      >
        {items.length === 0 && (
          <div className="art-empty" style={{ marginTop: 4 }}>
            Commands, observations and citations stream in here, each tagged with its agent.
          </div>
        )}
        {items.map((it) =>
          it.kind === 'grid' ? (
            <RerunGrid key={it.key} item={it} />
          ) : (
            <div key={it.key} className="erow" style={ROW_STYLE[it.style].row}>
              <span className="et mono">{it.time}</span>
              <span className="eg">{it.glyph}</span>
              <span className="en">{it.node}</span>
              <span
                className={expanded.has(it.key) ? 'ex' : 'ex ex-clamp'}
                style={ROW_STYLE[it.style].text}
                onClick={() =>
                  setExpanded((p) => {
                    const n = new Set(p)
                    if (!n.delete(it.key)) n.add(it.key)
                    return n
                  })
                }
              >
                {it.text}
                {it.ref && <span className="eref">{it.ref}</span>}
              </span>
            </div>
          ),
        )}
      </div>
    </section>
  )
}
