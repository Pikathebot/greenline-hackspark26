import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import type { Health } from '../api/types'
import { HEALTH_POLL_MS, createHealthStore } from './healthStore'

const health: Health = {
  modelServer: { url: 'u', reachable: true, model: 'qwen3-8b' },
  embedServer: { url: 'u', reachable: true },
  docker: { reachable: true, sandboxImage: true },
  fixtureRepo: { seeded: true },
  gpuVramFreeMb: 4000,
}

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('healthStore', () => {
  it('success → reachable', async () => {
    const store = createHealthStore({ api: { health: vi.fn().mockResolvedValue(health) } })
    await store.getState().check()
    expect(store.getState()).toMatchObject({ backendReachable: true, health })
  })

  it.each([0, 502, 500])('ApiError(%i) → unreachable', async (status) => {
    const store = createHealthStore({ api: { health: vi.fn().mockRejectedValue(new ApiError(status, 'x')) } })
    await store.getState().check()
    expect(store.getState().backendReachable).toBe(false)
  })

  it('polls every 3 s and stops', async () => {
    const fn = vi.fn().mockResolvedValue(health)
    const store = createHealthStore({ api: { health: fn } })
    const stop = store.getState().startPolling()
    expect(fn).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(HEALTH_POLL_MS)
    expect(fn).toHaveBeenCalledTimes(2)
    await vi.advanceTimersByTimeAsync(HEALTH_POLL_MS)
    expect(fn).toHaveBeenCalledTimes(3)
    stop()
    await vi.advanceTimersByTimeAsync(HEALTH_POLL_MS * 2)
    expect(fn).toHaveBeenCalledTimes(3)
  })
})
