import { describe, expect, it } from 'vitest'
import { shouldResetRun } from './runReset'

describe('shouldResetRun', () => {
  it('clears a finished run when another case is picked', () => {
    expect(shouldResetRun({ status: 'done', runCaseId: '0137', selectedCaseId: '0128' })).toBe(true)
    expect(shouldResetRun({ status: 'error', runCaseId: '0137', selectedCaseId: '0128' })).toBe(true)
  })

  it('keeps the run when the same case is still selected', () => {
    expect(shouldResetRun({ status: 'done', runCaseId: '0137', selectedCaseId: '0137' })).toBe(false)
  })

  it('never clears a run in flight, or when nothing has run', () => {
    expect(shouldResetRun({ status: 'streaming', runCaseId: '0137', selectedCaseId: '0128' })).toBe(false)
    expect(shouldResetRun({ status: 'starting', runCaseId: null, selectedCaseId: '0128' })).toBe(false)
    expect(shouldResetRun({ status: 'idle', runCaseId: null, selectedCaseId: '0128' })).toBe(false)
  })
})
