import { useEffect, useRef } from 'react'
import { useRunStore } from '../state/runStore'
import { buildFeed, type RowStyle } from '../view/feed'
import { RerunGrid } from './RerunGrid'

const ROW_STYLE: Record<RowStyle, { row?: React.CSSProperties; text?: React.CSSProperties }> = {
  normal: {},
  citation: { text: { color: 'var(--text)', fontStyle: 'italic' } },
  danger: { row: { background: 'var(--danger-tint)' }, text: { color: 'var(--danger)', fontWeight: 500 } },
  newest: { row: { background: 'var(--info-tint)' } },
}

export function EvidenceFeed() {
  const s = useRunStore((st) => st.state)
  const running = useRunStore((st) => st.status === 'streaming')
  const { items, lineCount } = buildFeed(s, running)
  const listRef = useRef<HTMLDivElement>(null)
  const pinned = useRef(true)

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
        <span className="grow" />
        <span className="muted" style={{ fontSize: 13 }}>
          › command · • observation · “ citation
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
              <span className="ex" style={ROW_STYLE[it.style].text}>
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
