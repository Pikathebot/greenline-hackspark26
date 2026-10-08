import type { BudgetCaps, BudgetPreset, NodeId, Outcome, RailId } from '../contract/events'

export const NODE_META: Record<NodeId, { name: string; role: string; step: string }> = {
  watcher: { name: 'Watcher', role: 'runs CI once', step: '01' },
  triage: { name: 'Triage', role: 'classifies the failure', step: '02' },
  reproducer: { name: 'Reproducer', role: 'reruns in sandbox', step: '03' },
  analyst: { name: 'Analyst', role: 'verdict + guardrail', step: '04' },
  patcher: { name: 'Patcher', role: 'writes the fix', step: '05' },
  critic: { name: 'Critic', role: 'reviews the fix', step: '06' },
  reporter: { name: 'Reporter', role: 'PR or escalation', step: '07' },
}

export type ToneName = 'brand' | 'info' | 'warn' | 'danger' | 'muted'
export const TONE: Record<ToneName, { c: string; bg: string; b: string }> = {
  brand: { c: 'var(--brand-ink)', bg: 'var(--brand-tint)', b: 'var(--brand)' },
  info: { c: 'var(--info)', bg: 'var(--info-tint)', b: 'var(--info)' },
  warn: { c: 'var(--warn)', bg: 'var(--warn-tint)', b: 'var(--warn)' },
  danger: { c: 'var(--danger)', bg: 'var(--danger-tint)', b: 'var(--danger)' },
  muted: { c: 'var(--muted)', bg: 'transparent', b: 'var(--border-strong)' },
}

export const OUTCOME_VIEW: Record<Outcome, { label: string; tone: ToneName }> = {
  reported: { label: 'reported', tone: 'brand' },
  escalated: { label: 'escalated', tone: 'warn' },
  budget_exhausted: { label: 'budget exhausted', tone: 'warn' },
  error: { label: 'error', tone: 'danger' },
}

export const RAIL_ORDER: RailId[] = ['protected_file', 'diff_cap', 'no_main_write', 'no_creds', 'egress_off']
export const MAX_PATCH_ATTEMPTS = 2

// DISPLAY-ONLY fallback so the meters show a denominator before run.start arrives. Mirrors
// backend/.env.example (normal 16/16/180 s, tight 4/3/60 s). run.start's caps replace it once a run starts.
export const PRESET_CAPS: Record<BudgetPreset, BudgetCaps> = {
  normal: { modelCalls: 16, toolCalls: 16, elapsedMs: 180000 },
  tight: { modelCalls: 4, toolCalls: 3, elapsedMs: 60000 },
}
