import { NODE_IDS, type NodeId } from '../contract/events'
import type { RunState } from '../state/runState'
import { MAX_PATCH_ATTEMPTS, NODE_META, type ToneName } from './consts'
import { fmtSeconds } from './format'

export type NodeStatus = 'idle' | 'active' | 'ok' | 'skip' | 'fail'

export interface NodeView {
  id: NodeId
  step: string
  name: string
  role: string
  status: NodeStatus
  detail: string
  /** tooltip: the node.exit note */
  title: string
  /** CSS colour of the connector to the NEXT node; null for the last node */
  connColor: string | null
  /** the guardrail barrier sits on the analyst -> patcher connector */
  barrier: boolean
}

const ANALYST_INDEX = 3

function patcherCount(s: RunState): number {
  return s.path.filter((n) => n === 'patcher').length
}

function statusOf(s: RunState, id: NodeId): NodeStatus {
  const n = s.nodes[id]
  if (n.status === 'idle') return 'idle'
  if (n.status === 'active') return 'active'
  // Derived from events: a rejecting latest critic vote shows the critic as failed.
  const last = s.criticVotes[s.criticVotes.length - 1]
  if (id === 'critic' && last && !last.approved) return 'fail'
  return n.outcome ?? 'ok'
}

function detailOf(s: RunState, id: NodeId, status: NodeStatus): string {
  const n = s.nodes[id]
  switch (status) {
    case 'idle':
      return s.outcome !== null ? 'not reached' : 'waiting'
    case 'active':
      if (id === 'reproducer' && s.rerun) return `rerun ${s.rerun.ticks.length} / ${s.rerun.total}`
      if (id === 'patcher') return `attempt ${patcherCount(s)} / ${MAX_PATCH_ATTEMPTS}`
      return 'running…'
    case 'ok':
      return n.durationMs !== undefined ? fmtSeconds(n.durationMs) : ''
    case 'skip':
      return 'skipped' + (s.memoryHit && id === 'reproducer' ? ' · memory' : '')
    case 'fail': {
      const last = s.criticVotes[s.criticVotes.length - 1]
      if (id === 'critic' && last && !last.approved) return `rejected #${last.n}`
      return n.note ?? 'failed'
    }
  }
}

export function nodeViews(s: RunState): NodeView[] {
  const barrier = s.guardrails.protected_file?.fired === true
  const partial = NODE_IDS.map((id) => {
    const status = statusOf(s, id)
    return {
      id,
      step: NODE_META[id].step,
      name: NODE_META[id].name,
      role: NODE_META[id].role,
      status,
      detail: detailOf(s, id, status),
      title: s.nodes[id].note ?? '',
    }
  })
  return partial.map((n, i) => {
    const next = partial[i + 1]
    let connColor: string | null = null
    if (next) {
      connColor = 'var(--border-strong)'
      if (n.status !== 'idle' && next.status !== 'idle') {
        connColor = next.status === 'active' ? 'var(--info)' : 'var(--brand)'
      }
      if (i === ANALYST_INDEX && barrier) connColor = 'var(--danger)'
    }
    return { ...n, connColor, barrier: i === ANALYST_INDEX && barrier }
  })
}

export interface ArcView {
  /** 0-based node index where the arc starts; it spans grid columns from+1 .. from+span */
  from: number
  span: number
  on: boolean
  tone: ToneName
  label: string
  show: boolean
}

export function arcViews(s: RunState): { loop: ArcView; bypass: ArcView; esc: ArcView } {
  const count = patcherCount(s)
  const loopOn = count >= 2
  const loop: ArcView = {
    from: 4,
    span: 2,
    on: loopOn,
    tone: 'info',
    label: loopOn ? `Critic → Patcher · attempt ${count} / ${MAX_PATCH_ATTEMPTS}` : 'retry if the Critic rejects',
    show: true,
  }

  const skipped = s.nodes.reproducer.outcome === 'skip'
  const bypass: ArcView = {
    from: 1,
    span: 3,
    on: skipped,
    tone: 'brand',
    label: skipped ? (s.memoryHit ? `skipped · memory hit #${s.memoryHit.caseRef}` : 'skipped') : 'skip on memory hit',
    show: true,
  }

  let esc: ArcView = { from: 3, span: 4, on: false, tone: 'warn', label: 'escalate if blocked', show: true }
  if (s.outcome === 'escalated' || s.outcome === 'budget_exhausted' || s.outcome === 'error') {
    const reporterAt = s.path.lastIndexOf('reporter')
    const prev = reporterAt > 0 ? s.path[reporterAt - 1] : s.path[s.path.length - 1]
    const idx = prev ? NODE_IDS.indexOf(prev) : ANALYST_INDEX
    const from = Math.min(Math.max(idx, 0), 5)
    const anyFired = Object.values(s.guardrails).some((g) => g?.fired)
    const [label, tone]: [string, ToneName] =
      s.outcome === 'error'
        ? ['error → report', 'danger']
        : s.outcome === 'budget_exhausted'
          ? ['budget exhausted → report', 'warn']
          : [anyFired ? 'escalate · guardrail' : 'escalate · no safe fix', 'warn']
    esc = { from, span: 7 - from, on: true, tone, label, show: true }
  }
  bypass.show = !esc.on || esc.from === ANALYST_INDEX

  // Once the run is over, keep only the paths that were actually taken.
  if (s.outcome !== null) {
    loop.show = loop.on
    bypass.show = bypass.on
    esc.show = esc.on
  }

  return { loop, bypass, esc }
}
