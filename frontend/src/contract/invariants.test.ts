import { describe, expect, it } from 'vitest'
import { ALL_SEQUENCES, ERROR_RUN } from '../state/__fixtures__/sequences'
import type { GreenlineEvent } from './events'
import { checkInvariants } from './invariants'

const ev = (o: object) => o as GreenlineEvent
const start = ev({ t: 0, type: 'run.start', runId: 'r', caseId: '1', mode: 'live', model: 'm', budgetPreset: 'normal', caps: { modelCalls: 1, toolCalls: 1, elapsedMs: 1 } })
const done = (t = 10, outcome = 'error') => ev({ t, type: 'done', outcome })
const enter = (t: number, node: string) => ev({ t, type: 'node.enter', node })
const exit = (t: number, node: string) => ev({ t, type: 'node.exit', node, durationMs: 1, status: 'ok' })
const verdict = (t: number) => ev({ t, type: 'verdict', cls: 'flaky', confidence: 1, rationale: '' })
const tick = (t: number, n: number, total = 3) => ev({ t, type: 'rerun.tick', n, total, passed: true, durationMs: 1 })

const has = (events: GreenlineEvent[], id: string) =>
  checkInvariants(events).some((m) => m.startsWith(`${id}:`))

describe('checkInvariants', () => {
  it.each(Object.entries(ALL_SEQUENCES))('%s is valid', (_n, s) => {
    expect(checkInvariants(s)).toEqual([])
  })
  it('error run with an unexited node is valid', () => {
    expect(checkInvariants(ERROR_RUN)).toEqual([])
  })
  it('I1: first event not run.start', () => {
    expect(has([enter(0, 'watcher'), done()], 'I1')).toBe(true)
  })
  it('I1: run.start t != 0', () => {
    expect(has([{ ...start, t: 5 } as GreenlineEvent, done(10)], 'I1')).toBe(true)
  })
  it('I1: two dones', () => {
    expect(has([start, done(1), done(2)], 'I1')).toBe(true)
  })
  it('I1: missing done', () => {
    expect(has([start], 'I1')).toBe(true)
  })
  it('I2: t going backwards', () => {
    expect(has([start, enter(50, 'watcher'), exit(20, 'watcher'), done(60)], 'I2')).toBe(true)
  })
  it('I3: enter while another active', () => {
    expect(has([start, enter(1, 'watcher'), enter(2, 'triage'), done(3)], 'I3')).toBe(true)
  })
  it('I3: exit of a non-active node', () => {
    expect(has([start, enter(1, 'watcher'), exit(2, 'triage'), done(3)], 'I3')).toBe(true)
  })
  it('I4: two verdicts', () => {
    expect(has([start, verdict(1), verdict(2), done(3)], 'I4')).toBe(true)
  })
  it('I5: ticks 1,3', () => {
    expect(has([start, tick(1, 1), tick(2, 3), done(3)], 'I5')).toBe(true)
  })
  it('I5: n > total', () => {
    expect(has([start, tick(1, 1, 0), done(3)], 'I5')).toBe(true)
  })
  it('I6: escalated without report', () => {
    expect(has([start, done(1, 'escalated')], 'I6')).toBe(true)
  })
})
