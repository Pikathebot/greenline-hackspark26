import { describe, expect, it, vi } from 'vitest'
import type { CaseSummary } from '../contract/case'
import { createCaseStore } from './caseStore'

const c = (id: string) =>
  ({ id, title: 't', repo: 'r', branch: 'b', cls: 'flaky', detectedAt: '', ciRunUrl: '', beat: '',
     lastRun: null, hasDemoRun: true }) satisfies CaseSummary

describe('caseStore', () => {
  it('refresh stores cases', async () => {
    const store = createCaseStore({ api: { cases: vi.fn().mockResolvedValue([c('0142')]) } })
    await store.getState().refresh()
    expect(store.getState()).toMatchObject({ loaded: true, error: null })
    expect(store.getState().cases).toHaveLength(1)
  })

  it('a failed refresh keeps the old cases and records the error', async () => {
    const cases = vi.fn().mockResolvedValueOnce([c('0142')]).mockRejectedValueOnce(new Error('boom'))
    const store = createCaseStore({ api: { cases } })
    await store.getState().refresh()
    await store.getState().refresh()
    expect(store.getState().cases).toHaveLength(1)
    expect(store.getState().error).toBe('boom')
  })
})
