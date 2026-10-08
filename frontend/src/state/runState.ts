import {
  NODE_IDS,
  RAIL_IDS,
  type BudgetCaps,
  type BudgetPreset,
  type CriticVoteEvent,
  type EvidenceEvent,
  type LogEvent,
  type MemoryHitEvent,
  type NodeExitStatus,
  type NodeId,
  type Outcome,
  type PatchAttemptEvent,
  type RailId,
  type RerunTickEvent,
  type ReportEvent,
  type RunMode,
  type VerdictEvent,
} from '../contract/events'

export interface NodeRunState {
  status: 'idle' | 'active' | 'done'
  outcome?: NodeExitStatus
  durationMs?: number
  note?: string
  enteredAt?: number
}
export type LogEntry = Omit<LogEvent, 'type'>
export type EvidenceEntry = Omit<EvidenceEvent, 'type'>
export type RerunTick = Omit<RerunTickEvent, 't' | 'type' | 'total'>
export type MemoryHit = Omit<MemoryHitEvent, 't' | 'type'>
export type Verdict = Omit<VerdictEvent, 't' | 'type'>
export type PatchAttempt = Omit<PatchAttemptEvent, 't' | 'type'>
export type CriticVote = Omit<CriticVoteEvent, 't' | 'type'>
export type GuardrailState = { fired: boolean; note: string; t: number }
export type Report = Omit<ReportEvent, 't' | 'type'>

export interface RunState {
  runId: string | null
  caseId: string | null
  mode: RunMode | null
  model: string | null
  budgetPreset: BudgetPreset | null
  caps: BudgetCaps | null
  nodes: Record<NodeId, NodeRunState>
  activeNode: NodeId | null
  path: NodeId[]
  narration: string | null
  logs: LogEntry[]
  evidence: EvidenceEntry[]
  rerun: { total: number; ticks: RerunTick[] } | null
  memoryHit: MemoryHit | null
  verdict: Verdict | null
  patchAttempts: PatchAttempt[]
  criticVotes: CriticVote[]
  guardrails: Record<RailId, GuardrailState | undefined>
  budget: { modelCalls: number; toolCalls: number; elapsedMs: number }
  report: Report | null
  error: string | null
  outcome: Outcome | null
  lastT: number
}

function deepFreeze<T>(o: T): T {
  if (o && typeof o === 'object' && !Object.isFrozen(o)) {
    Object.freeze(o)
    for (const v of Object.values(o as object)) deepFreeze(v)
  }
  return o
}

const idleNodes = Object.fromEntries(NODE_IDS.map((n) => [n, { status: 'idle' }])) as Record<
  NodeId,
  NodeRunState
>
const emptyRails = Object.fromEntries(RAIL_IDS.map((r) => [r, undefined])) as Record<
  RailId,
  GuardrailState | undefined
>

export const EMPTY_STATE: RunState = deepFreeze({
  runId: null,
  caseId: null,
  mode: null,
  model: null,
  budgetPreset: null,
  caps: null,
  nodes: idleNodes,
  activeNode: null,
  path: [],
  narration: null,
  logs: [],
  evidence: [],
  rerun: null,
  memoryHit: null,
  verdict: null,
  patchAttempts: [],
  criticVotes: [],
  guardrails: emptyRails,
  budget: { modelCalls: 0, toolCalls: 0, elapsedMs: 0 },
  report: null,
  error: null,
  outcome: null,
  lastT: 0,
})
