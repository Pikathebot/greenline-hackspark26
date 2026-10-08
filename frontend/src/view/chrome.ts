import type { CaseSummary } from '../contract/case'
import type { NodeId } from '../contract/events'
import type { RunStatus } from '../state/runStore'
import type { RunState } from '../state/runState'
import { OUTCOME_VIEW, type ToneName } from './consts'
import { fmtClock, fmtClockTenths } from './format'

export { formatModel } from './format'

/** The slice of GET /api/health the top bar needs (structural, so view code never imports api/). */
export interface HealthInput {
  modelServer: { reachable: boolean; url: string }
  embedServer: { reachable: boolean; url: string }
  docker: { reachable: boolean; sandboxImage: boolean }
}

export interface HealthChip {
  label: 'Model' | 'Memory' | 'Sandbox'
  /** null = unknown (muted dot) */
  ok: boolean | null
  tip: string
}

export function healthViews(health: HealthInput | null, reachable: boolean | null): HealthChip[] {
  const raw: [HealthChip['label'], boolean | undefined, string][] = [
    ['Model', health?.modelServer.reachable, health?.modelServer.url ?? ''],
    ['Memory', health?.embedServer.reachable, health?.embedServer.url ?? ''],
    ['Sandbox', health ? health.docker.reachable && health.docker.sandboxImage : undefined, ''],
  ]
  return raw.map(([label, ok, url]) => {
    const value: boolean | null = reachable === false ? false : reachable === null || ok === undefined ? null : ok
    const state = value === null ? 'unknown' : value ? 'reachable' : 'unreachable'
    return { label, ok: value, tip: `${label}: ${state}${url ? ` (${url})` : ''}` }
  })
}

export function bannerView(p: { reachable: boolean | null; runError: string | null }): { title: string; sub: string } | null {
  if (p.reachable === false) {
    return {
      title: 'Backend offline: start uvicorn on :8000',
      sub: 'Retrying every 3 s. Nothing below is live until it answers.',
    }
  }
  if (p.runError) return { title: `Run error: ${p.runError}`, sub: 'The run ended with outcome error.' }
  return null
}

export function narrationView(p: {
  s: RunState
  status: RunStatus
  reachable: boolean | null
  selectedCase: CaseSummary | null
}): { tag: NodeId | null; text: string } {
  const { s, status, reachable, selectedCase } = p
  if (reachable === false) return { tag: null, text: 'Waiting for the backend on :8000…' }
  if (status === 'streaming' || status === 'starting') {
    return { tag: s.activeNode, text: s.narration ?? 'Starting…' }
  }
  if (selectedCase) {
    const beat = selectedCase.beat
    return {
      tag: null,
      text: `Ready: #${selectedCase.id}. ${beat}${beat.endsWith('.') ? '' : '.'} Press Enter to run.`,
    }
  }
  return { tag: null, text: 'Pick a case to begin.' }
}

export interface SummaryView {
  outcomeLabel: string
  tone: ToneName
  text: string
  duration: string
  modelCalls: number
  sandboxRuns: number
}

export function summaryView(s: RunState): SummaryView | null {
  if (s.outcome === null) return null
  const o = OUTCOME_VIEW[s.outcome]
  return {
    outcomeLabel: o.label,
    tone: o.tone,
    text: s.report?.title ?? '',
    duration: fmtClockTenths(s.lastT),
    modelCalls: s.budget.modelCalls,
    sandboxRuns: s.budget.toolCalls,
  }
}

export interface CaseRow {
  id: string
  cls: string
  title: string
  beat: string
  pillLabel: string
  pillTone: ToneName
  meta: string
  selected: boolean
}

export function caseRows(cases: CaseSummary[], selectedId: string | null): CaseRow[] {
  return cases.map((c) => ({
    id: c.id,
    cls: c.cls,
    title: c.title,
    beat: c.beat,
    pillLabel: c.lastRun ? OUTCOME_VIEW[c.lastRun.outcome].label : 'not run',
    pillTone: c.lastRun ? OUTCOME_VIEW[c.lastRun.outcome].tone : 'muted',
    meta: c.lastRun ? `last live run · ${fmtClock(c.lastRun.durationMs)}` : 'no live run yet',
    selected: c.id === selectedId,
  }))
}

export function runButtonView(p: {
  reachable: boolean | null
  status: RunStatus
  caseId: string | null
}): { label: string; enabled: boolean } {
  if (p.reachable === false) return { label: 'Backend offline', enabled: false }
  if (p.status === 'starting' || p.status === 'streaming') {
    return { label: `Running #${p.caseId ?? '—'}…`, enabled: false }
  }
  return { label: `Run #${p.caseId ?? '—'}`, enabled: p.caseId !== null }
}
