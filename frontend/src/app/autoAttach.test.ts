import { describe, expect, it } from 'vitest'
import { shouldAttachActive } from './autoAttach'

describe('shouldAttachActive', () => {
  it('attaches to a run this page is not showing', () => {
    expect(shouldAttachActive({ status: 'idle', currentRunId: null, activeRunId: 'run-7001-a' })).toBe(true)
    expect(shouldAttachActive({ status: 'done', currentRunId: 'run-0142-a', activeRunId: 'run-7001-a' })).toBe(true)
    expect(shouldAttachActive({ status: 'error', currentRunId: 'run-0142-a', activeRunId: 'run-7001-a' })).toBe(true)
  })

  it('does nothing without an active run', () => {
    expect(shouldAttachActive({ status: 'idle', currentRunId: null, activeRunId: null })).toBe(false)
  })

  it('never interrupts a run this page is already following', () => {
    expect(shouldAttachActive({ status: 'streaming', currentRunId: 'run-a', activeRunId: 'run-b' })).toBe(false)
    expect(shouldAttachActive({ status: 'starting', currentRunId: null, activeRunId: 'run-b' })).toBe(false)
    expect(shouldAttachActive({ status: 'done', currentRunId: 'run-b', activeRunId: 'run-b' })).toBe(false)
  })
})
