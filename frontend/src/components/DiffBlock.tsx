import type { CSSProperties } from 'react'
import type { DiffLine } from '../view/patch'

const LINE_STYLE: Record<DiffLine['kind'], CSSProperties> = {
  add: { background: 'var(--brand-tint)', color: 'var(--brand-ink)' },
  del: { background: 'var(--danger-tint)', color: 'var(--danger)' },
  hunk: { color: 'var(--info)' },
  ctx: { color: 'var(--muted)' },
}

export function DiffBlock({ file, lines, style }: { file: string; lines: DiffLine[]; style?: CSSProperties }) {
  return (
    <div className="diff" style={style}>
      {file && <div className="dfile">{file}</div>}
      {lines.map((l, i) => (
        <div key={i} className="dl" style={LINE_STYLE[l.kind]}>
          {l.text}
        </div>
      ))}
    </div>
  )
}
