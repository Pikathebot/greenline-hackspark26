import { describe, expect, it } from 'vitest'
import fixture from '../state/__fixtures__/allVariants.json'
import { EVENT_TYPES, FAILURE_CLASSES, NODE_IDS, RAIL_IDS } from './events'

const REQUIRED: Record<string, string[]> = {
  'run.start': ['t', 'type', 'runId', 'caseId', 'mode', 'model', 'budgetPreset', 'caps'],
  'node.enter': ['t', 'type', 'node'],
  'node.exit': ['t', 'type', 'node', 'durationMs', 'status'],
  log: ['t', 'type', 'node', 'level', 'text'],
  evidence: ['t', 'type', 'node', 'kind', 'text'],
  'rerun.tick': ['t', 'type', 'n', 'total', 'passed', 'durationMs'],
  'memory.hit': ['t', 'type', 'caseRef', 'similarity', 'summary'],
  verdict: ['t', 'type', 'cls', 'confidence', 'rationale'],
  'patch.attempt': ['t', 'type', 'n', 'file', 'diff', 'source', 'result'],
  'critic.vote': ['t', 'type', 'n', 'samples', 'deterministic', 'approved'],
  budget: ['t', 'type', 'modelCalls', 'toolCalls', 'elapsedMs'],
  guardrail: ['t', 'type', 'rail', 'fired', 'note'],
  report: ['t', 'type', 'kind', 'title', 'body'],
  error: ['t', 'type', 'message'],
  done: ['t', 'type', 'outcome'],
}
const OPTIONAL: Record<string, string[]> = {
  'node.exit': ['note'],
  evidence: ['ref'],
  report: ['prUrl', 'dryRun'],
  error: ['node'],
}
const data = fixture as unknown as Record<string, Record<string, unknown>>

describe('allVariants.json vs contract', () => {
  it('has exactly the 15 event types', () => {
    expect(new Set(Object.keys(data))).toEqual(new Set(EVENT_TYPES))
    expect(EVENT_TYPES).toHaveLength(15)
  })
  it.each(EVENT_TYPES)('%s: type matches its key', (k) => {
    expect(data[k]!.type).toBe(k)
  })
  it.each(EVENT_TYPES)('%s: required keys present, no unknown keys', (k) => {
    const keys = Object.keys(data[k]!)
    const allowed = [...REQUIRED[k]!, ...(OPTIONAL[k] ?? [])]
    for (const r of REQUIRED[k]!) expect(keys, `missing ${r}`).toContain(r)
    for (const key of keys) expect(allowed, `unknown ${key}`).toContain(key)
  })
  it('enum lists match docs/04', () => {
    expect(NODE_IDS).toEqual(['watcher', 'triage', 'reproducer', 'analyst', 'patcher', 'critic', 'reporter'])
    expect(RAIL_IDS).toEqual(['protected_file', 'diff_cap', 'no_main_write', 'no_creds', 'egress_off'])
    expect(FAILURE_CLASSES).toEqual(['flaky', 'dependency', 'env', 'lint', 'regression'])
  })
})
