import type { NodeId } from '../contract/events'
import type { RunState } from '../state/runState'
import { fmtClockTenths } from './format'

export type RowStyle = 'normal' | 'citation' | 'danger' | 'newest'
export type CellState = 'pass' | 'fail' | 'pending' | 'cap'

export type FeedItem =
  | { kind: 'row'; key: string; time: string; glyph: string; node: NodeId; text: string; ref?: string; style: RowStyle }
  | { kind: 'grid'; key: 'grid'; summary: string; cells: { n: number; state: CellState }[]; cellMin: string }

export const GLYPH = { command: '›', observation: '•', citation: '“' } as const
/** An observation this close before a fired guardrail is the line that explains it. */
const GUARDRAIL_WINDOW_MS = 250

export function buildFeed(s: RunState, running: boolean): { items: FeedItem[]; lineCount: number } {
  const firedAt = Object.values(s.guardrails)
    .filter((g) => g?.fired)
    .map((g) => g!.t)

  const rows: FeedItem[] = s.evidence.map((e, i) => {
    let style: RowStyle = e.kind === 'citation' ? 'citation' : 'normal'
    if (e.kind === 'observation' && firedAt.some((t) => t - e.t >= 0 && t - e.t <= GUARDRAIL_WINDOW_MS)) {
      style = 'danger'
    } else if (running && i === s.evidence.length - 1) {
      style = 'newest'
    }
    return {
      kind: 'row',
      key: `e${i}`,
      time: fmtClockTenths(e.t),
      glyph: GLYPH[e.kind],
      node: e.node,
      text: e.text,
      ...(e.ref !== undefined && { ref: e.ref }),
      style,
    }
  })

  const items: FeedItem[] = [...rows]
  if (s.rerun) {
    const { total, ticks } = s.rerun
    const capped = s.outcome === 'budget_exhausted' && ticks.length < total
    const cells = Array.from({ length: total }, (_, i) => {
      const tick = ticks[i]
      const state: CellState = tick ? (tick.passed ? 'pass' : 'fail') : capped ? 'cap' : 'pending'
      return { n: i + 1, state }
    })
    const pass = ticks.filter((t) => t.passed).length
    const fail = ticks.length - pass
    const summary =
      `${pass} pass / ${fail} fail` +
      (ticks.length < total && !capped && running ? `  ·  ${ticks.length} / ${total}` : '') +
      (capped ? '  ·  stopped at cap' : '')
    const grid: FeedItem = { kind: 'grid', key: 'grid', summary, cells, cellMin: total <= 3 ? '96px' : '1fr' }

    const repro = s.evidence.map((e, i) => ({ e, i })).filter(({ e }) => e.node === 'reproducer')
    const lastCommand = [...repro].reverse().find(({ e }) => e.kind === 'command')
    let at = rows.length
    if (lastCommand) at = lastCommand.i + 1
    else if (repro.length > 0) at = repro[0]!.i
    items.splice(at, 0, grid)
  }
  return { items, lineCount: rows.length }
}
