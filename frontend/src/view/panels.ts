import type { RailId } from '../contract/events'
import type { RunStatus } from '../state/runStore'
import type { RunState } from '../state/runState'
import { NODE_META, RAIL_ORDER, type ToneName } from './consts'
import { attemptViews, type DiffLine, type VoteView } from './patch'

export type VerdictView =
  | { kind: 'verdict'; word: string; pct: string; fillPct: number; rationale: string }
  | { kind: 'none'; title: string; sub: string; tone: ToneName }

export function verdictView(p: { s: RunState; status: RunStatus }): VerdictView {
  const { s, status } = p
  if (s.verdict) {
    return {
      kind: 'verdict',
      word: s.verdict.cls.toUpperCase(),
      pct: `${Math.round(s.verdict.confidence * 100)}%`,
      fillPct: Math.max(0, Math.min(100, Math.round(s.verdict.confidence * 100))),
      rationale: s.verdict.rationale,
    }
  }
  if (s.outcome === 'budget_exhausted') {
    const cap =
      s.budgetPreset === 'tight' && s.caps
        ? ` Tight allows ${s.caps.modelCalls} model calls and ${s.caps.toolCalls} sandbox runs.`
        : ''
    return { kind: 'none', title: 'No verdict reached', sub: `Budget exhausted.${cap}`, tone: 'warn' }
  }
  if (s.outcome === 'error') {
    const failed = [...s.path].reverse().find((n) => s.nodes[n].outcome === 'fail') ?? s.path[s.path.length - 1]
    const where = failed ? ` during ${NODE_META[failed].name}` : ''
    return { kind: 'none', title: 'No verdict reached', sub: `The run ended with an error${where}.`, tone: 'danger' }
  }
  if (s.outcome !== null) return { kind: 'none', title: 'No verdict reached', sub: '', tone: 'muted' }
  if (status === 'error') {
    return { kind: 'none', title: 'No verdict reached', sub: 'Lost the run stream.', tone: 'danger' }
  }
  if (status === 'idle' && s.runId === null) {
    return { kind: 'none', title: 'No run yet', sub: 'Pick a case and press Run.', tone: 'muted' }
  }
  return {
    kind: 'none',
    title: 'Gathering evidence…',
    sub: 'The verdict appears once the Analyst has weighed the evidence.',
    tone: 'muted',
  }
}

export type RailState = 'idle' | 'clear' | 'fired'
export interface RailView {
  id: RailId
  state: RailState
  note: string
}

export function railViews(s: RunState): { rails: RailView[]; summary: string } {
  const rails = RAIL_ORDER.map((id): RailView => {
    const g = s.guardrails[id]
    if (!g) return { id, state: 'idle', note: '' }
    return { id, state: g.fired ? 'fired' : 'clear', note: g.note }
  })
  const count = (st: RailState) => rails.filter((r) => r.state === st).length
  const summary = [
    count('fired') ? `${count('fired')} blocked` : '',
    count('clear') ? `${count('clear')} clear` : '',
    count('idle') ? `${count('idle')} not checked` : '',
  ]
    .filter(Boolean)
    .join(' · ')
  return { rails, summary }
}

export type ArtifactView =
  | { kind: 'empty'; hint: '' }
  | {
      kind: 'escalation'
      hint: 'escalation note'
      header: string
      reason: string
      reasonTone: ToneName
      title: string
      body: string
    }
  | {
      kind: 'pr'
      hint: 'draft PR'
      title: string
      body: string
      prUrl?: string
      dryRun?: boolean
      file: string
      diff: DiffLine[]
      vote: VoteView | null
    }
  | { kind: 'loop'; hint: '2 attempts max' }

export function artifactView(s: RunState): ArtifactView {
  const r = s.report
  const { attempts, acceptedN } = attemptViews(s)
  if (!r) return attempts.length > 0 ? { kind: 'loop', hint: '2 attempts max' } : { kind: 'empty', hint: '' }
  if (r.kind === 'pr') {
    const accepted = attempts.find((a) => a.n === acceptedN && !a.running)
    return {
      kind: 'pr',
      hint: 'draft PR',
      title: r.title,
      body: r.body,
      file: accepted?.file ?? '',
      diff: accepted?.diff ?? [],
      vote: accepted?.vote ?? null,
      ...(r.prUrl !== undefined && { prUrl: r.prUrl }),
      ...(r.dryRun !== undefined && { dryRun: r.dryRun }),
    }
  }
  const firedRail = RAIL_ORDER.find((id) => s.guardrails[id]?.fired)
  let reason = 'no safe fix'
  let reasonTone: ToneName = 'warn'
  if (s.outcome === 'error') {
    reason = 'error'
    reasonTone = 'danger'
  } else if (s.outcome === 'budget_exhausted') {
    reason = 'budget exhausted'
  } else if (firedRail) {
    reason = `guardrail · ${firedRail}`
    reasonTone = 'danger'
  }
  return {
    kind: 'escalation',
    hint: 'escalation note',
    header: 'Escalated to a human',
    reason,
    reasonTone,
    title: r.title,
    body: r.body,
  }
}
