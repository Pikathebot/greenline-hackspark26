export const NODE_IDS = ['watcher', 'triage', 'reproducer', 'analyst', 'patcher', 'critic', 'reporter'] as const
export type NodeId = (typeof NODE_IDS)[number]
export const FAILURE_CLASSES = ['flaky', 'dependency', 'env', 'lint', 'regression'] as const
export type FailureClass = (typeof FAILURE_CLASSES)[number]
export const RAIL_IDS = ['protected_file', 'diff_cap', 'no_main_write', 'no_creds', 'egress_off'] as const
export type RailId = (typeof RAIL_IDS)[number]
export type RunMode = 'live' | 'demo'
export type BudgetPreset = 'normal' | 'tight'
export type Outcome = 'reported' | 'escalated' | 'budget_exhausted' | 'error'
export type NodeExitStatus = 'ok' | 'skip' | 'fail'
export type LogLevel = 'info' | 'warn' | 'error'
export type EvidenceKind = 'command' | 'observation' | 'citation'
export type PatchSource = 'model' | 'tool'
export type PatchResult = 'green' | 'red' | 'vetoed'
export type CriticSample = 'approve' | 'reject'
export type ReportKind = 'pr' | 'escalation'
export interface CheckResult { name: string; passed: boolean; detail?: string }
export interface BudgetCaps { modelCalls: number; toolCalls: number; elapsedMs: number }

export interface RunStartEvent {
  t: number; type: 'run.start'
  runId: string; caseId: string; mode: RunMode; model: string
  budgetPreset: BudgetPreset; caps: BudgetCaps
}
export interface NodeEnterEvent { t: number; type: 'node.enter'; node: NodeId }
export interface NodeExitEvent {
  t: number; type: 'node.exit'; node: NodeId
  durationMs: number; status: NodeExitStatus; note?: string
}
export interface LogEvent { t: number; type: 'log'; node: NodeId; level: LogLevel; text: string }
export interface EvidenceEvent {
  t: number; type: 'evidence'; node: NodeId; kind: EvidenceKind; text: string; ref?: string
}
export interface RerunTickEvent {
  t: number; type: 'rerun.tick'; n: number; total: number; passed: boolean; durationMs: number
}
export interface MemoryHitEvent {
  t: number; type: 'memory.hit'; caseRef: string; similarity: number; summary: string
}
export interface VerdictEvent {
  t: number; type: 'verdict'; cls: FailureClass; confidence: number; rationale: string
}
export interface PatchAttemptEvent {
  t: number; type: 'patch.attempt'; n: number; file: string; diff: string
  source: PatchSource; result: PatchResult
}
export interface CriticVoteEvent {
  t: number; type: 'critic.vote'; n: number; samples: CriticSample[]
  deterministic: CheckResult[]; approved: boolean
}
export interface BudgetEvent {
  t: number; type: 'budget'; modelCalls: number; toolCalls: number; elapsedMs: number
}
export interface GuardrailEvent {
  t: number; type: 'guardrail'; rail: RailId; fired: boolean; note: string
}
export interface ReportEvent {
  t: number; type: 'report'; kind: ReportKind; title: string; body: string
  prUrl?: string; dryRun?: boolean
}
export interface ErrorEvent { t: number; type: 'error'; node?: NodeId; message: string }
export interface DoneEvent { t: number; type: 'done'; outcome: Outcome }

export type GreenlineEvent =
  | RunStartEvent | NodeEnterEvent | NodeExitEvent | LogEvent | EvidenceEvent
  | RerunTickEvent | MemoryHitEvent | VerdictEvent | PatchAttemptEvent | CriticVoteEvent
  | BudgetEvent | GuardrailEvent | ReportEvent | ErrorEvent | DoneEvent

export type EventType = GreenlineEvent['type']
export const EVENT_TYPES = [
  'run.start', 'node.enter', 'node.exit', 'log', 'evidence', 'rerun.tick',
  'memory.hit', 'verdict', 'patch.attempt', 'critic.vote', 'budget', 'guardrail',
  'report', 'error', 'done',
] as const satisfies readonly EventType[]

// compile-time: every EventType is listed
type _MissingType = Exclude<EventType, (typeof EVENT_TYPES)[number]>
const _allTypesListed: [_MissingType] extends [never] ? true : never = true
void _allTypesListed

export type EventOf<K extends EventType> = Extract<GreenlineEvent, { type: K }>
