import { describe, expect, it, vi } from 'vitest'
import type { Scoreboard } from '../api/types'
import { createScoreboardStore } from './scoreboardStore'

const sb = { sampleSize: 3 } as Scoreboard

describe('scoreboardStore', () => {
  it('refresh loads the scoreboard', async () => {
    const store = createScoreboardStore({ api: { scoreboard: vi.fn().mockResolvedValue(sb) } })
    expect(store.getState().status).toBe('idle')
    await store.getState().refresh()
    expect(store.getState()).toMatchObject({ status: 'ready', data: sb })
  })

  it('a failed refresh keeps the old data and flags the error', async () => {
    const scoreboard = vi.fn().mockResolvedValueOnce(sb).mockRejectedValueOnce(new Error('down'))
    const store = createScoreboardStore({ api: { scoreboard } })
    await store.getState().refresh()
    await store.getState().refresh()
    expect(store.getState()).toMatchObject({ status: 'error', data: sb })
  })
})
