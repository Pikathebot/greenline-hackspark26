import type { GreenlineEvent, NodeId } from './events'

/** Stream validator for invariants 1-6 of docs/04. Returns one message per violation. */
export function checkInvariants(events: readonly GreenlineEvent[]): string[] {
  const out: string[] = []
  const first = events[0]
  const last = events[events.length - 1]

  // I1
  if (!first) {
    out.push('I1: empty event list')
    return out
  }
  if (first.type !== 'run.start') out.push(`I1: first event is ${first.type}, expected run.start`)
  else if (first.t !== 0) out.push(`I1: run.start has t=${first.t}, expected 0`)
  if (!last || last.type !== 'done') out.push('I1: last event is not done')
  const doneCount = events.filter((e) => e.type === 'done').length
  if (doneCount !== 1) out.push(`I1: expected exactly one done, found ${doneCount}`)

  // I2
  for (let i = 1; i < events.length; i++) {
    const prev = events[i - 1]!
    const cur = events[i]!
    if (cur.t < prev.t) out.push(`I2: t went backwards at index ${i} (${prev.t} -> ${cur.t})`)
  }

  // I3
  let active: NodeId | null = null
  events.forEach((e, i) => {
    if (e.type === 'node.enter') {
      if (active !== null) out.push(`I3: node.enter ${e.node} at index ${i} while ${active} is active`)
      active = e.node
    } else if (e.type === 'node.exit') {
      if (active !== e.node) {
        out.push(`I3: node.exit ${e.node} at index ${i} but active node is ${active ?? 'none'}`)
      }
      if (active === e.node) active = null
    }
  })

  // I4
  const verdicts = events.filter((e) => e.type === 'verdict').length
  if (verdicts > 1) out.push(`I4: ${verdicts} verdict events, expected at most one`)

  // I5
  let expectedN = 1
  let total: number | null = null
  for (const e of events) {
    if (e.type !== 'rerun.tick') continue
    if (e.n !== expectedN) out.push(`I5: rerun.tick n=${e.n}, expected ${expectedN}`)
    if (total !== null && e.total !== total) out.push(`I5: rerun.tick total changed ${total} -> ${e.total}`)
    if (e.n > e.total) out.push(`I5: rerun.tick n=${e.n} exceeds total=${e.total}`)
    total = e.total
    expectedN = e.n + 1
  }

  // I6
  if (last && last.type === 'done' && last.outcome !== 'error') {
    const reportIdx = events.findIndex((e) => e.type === 'report')
    if (reportIdx === -1 || reportIdx > events.length - 1) {
      out.push(`I6: outcome ${last.outcome} requires a report before done`)
    }
  }

  return out
}
