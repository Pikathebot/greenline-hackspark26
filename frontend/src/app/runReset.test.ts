import { beforeEach, describe, expect, it } from 'vitest'
import { EMPTY_STATE } from '../state/runState'
import { forgetRuns, recallRun, rememberRun } from './runCache'
import { caseSwitchAction } from './runReset'

const base = { runCaseId: '0137', selectedCaseId: '0128', hasCached: false }

describe('caseSwitchAction', () => {
  it('clears a finished run of another case that has nothing cached', () => {
    expect(caseSwitchAction({ ...base, status: 'done' })).toBe('reset')
    expect(caseSwitchAction({ ...base, status: 'error' })).toBe('reset')
  })

  it('restores the picked case when it finished earlier this session', () => {
    expect(caseSwitchAction({ ...base, status: 'done', hasCached: true })).toBe('restore')
    expect(caseSwitchAction({ ...base, status: 'error', hasCached: true })).toBe('restore')
    expect(caseSwitchAction({ ...base, status: 'idle', runCaseId: null, hasCached: true })).toBe('restore')
  })

  it('keeps the run when it already belongs to the picked case', () => {
    expect(caseSwitchAction({ ...base, status: 'done', selectedCaseId: '0137', hasCached: true })).toBe('keep')
  })

  it('never touches a run in flight', () => {
    expect(caseSwitchAction({ ...base, status: 'streaming', hasCached: true })).toBe('keep')
    expect(caseSwitchAction({ ...base, status: 'starting' })).toBe('keep')
  })

  it('keeps an empty screen empty', () => {
    expect(caseSwitchAction({ ...base, status: 'idle', runCaseId: null })).toBe('keep')
  })
})

describe('run cache', () => {
  beforeEach(() => forgetRuns())

  it('remembers the last finished run per case', () => {
    expect(recallRun('0137')).toBeNull()
    rememberRun('0137', { runId: 'a', events: [], state: EMPTY_STATE })
    rememberRun('0137', { runId: 'b', events: [], state: EMPTY_STATE })
    expect(recallRun('0137')?.runId).toBe('b')
    expect(recallRun('0128')).toBeNull()
    expect(recallRun(null)).toBeNull()
  })
})
