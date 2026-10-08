import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import type { StreamHandlers } from '../api/stream'
import { HERO_0142 } from './__fixtures__/sequences'
import { reduceAll } from './reducer'
import { EMPTY_STATE } from './runState'
import { createRunStore } from './runStore'

function setup(startRun = vi.fn().mockResolvedValue({ runId: 'run-1' })) {
  const handlers: StreamHandlers[] = []
  const closes: ReturnType<typeof vi.fn>[] = []
  const openStream = vi.fn((_id: string, h: StreamHandlers) => {
    handlers.push(h)
    const close = vi.fn()
    closes.push(close)
    return { close }
  })
  const onRunDone = vi.fn()
  const store = createRunStore({ api: { startRun }, openStream, onRunDone })
  return { store, startRun, openStream, onRunDone, handlers, closes }
}
const opts = { mode: 'demo', budget: 'normal' } as const

describe('runStore', () => {
  it('startRun goes starting → streaming and opens the stream', async () => {
    const { store, openStream } = setup()
    const p = store.getState().startRun('0142', opts)
    expect(store.getState().status).toBe('starting')
    await p
    expect(store.getState().status).toBe('streaming')
    expect(store.getState().connection).toBe('open')
    expect(openStream).toHaveBeenCalledWith('run-1', expect.any(Object))
  })

  it('reduces streamed events, finishes on done and calls onRunDone once', async () => {
    const { store, handlers, onRunDone } = setup()
    await store.getState().startRun('0142', opts)
    for (const e of HERO_0142) handlers[0]!.onEvent(e)
    const s = store.getState()
    expect(s.state).toEqual(reduceAll(HERO_0142))
    expect(s.events).toHaveLength(HERO_0142.length)
    expect(s.status).toBe('done')
    expect(s.connection).toBe('none')
    expect(onRunDone).toHaveBeenCalledTimes(1)
  })

  it('startRun while streaming is a no-op', async () => {
    const { store, startRun } = setup()
    await store.getState().startRun('0142', opts)
    await store.getState().startRun('0144', opts)
    expect(startRun).toHaveBeenCalledTimes(1)
  })

  it('409 → conflict problem, back to idle, no stream', async () => {
    const { store, openStream } = setup(vi.fn().mockRejectedValue(new ApiError(409, 'busy')))
    await store.getState().startRun('0142', opts)
    expect(store.getState().problem?.kind).toBe('conflict')
    expect(store.getState().status).toBe('idle')
    expect(openStream).not.toHaveBeenCalled()
  })

  it('0 → unreachable, 404 → not_found with the detail', async () => {
    const a = setup(vi.fn().mockRejectedValue(new ApiError(0, 'backend unreachable')))
    await a.store.getState().startRun('0142', opts)
    expect(a.store.getState().problem?.kind).toBe('unreachable')
    const b = setup(vi.fn().mockRejectedValue(new ApiError(404, 'no recorded demo run for case')))
    await b.store.getState().startRun('0142', opts)
    expect(b.store.getState().problem).toEqual({ kind: 'not_found', message: 'no recorded demo run for case' })
  })

  it('onReset clears state; replaying the full run gives no duplicates', async () => {
    const { store, handlers } = setup()
    await store.getState().startRun('0142', opts)
    for (const e of HERO_0142.slice(0, 12)) handlers[0]!.onEvent(e)
    handlers[0]!.onReset()
    expect(store.getState().events).toEqual([])
    expect(store.getState().state).toBe(EMPTY_STATE)
    for (const e of HERO_0142) handlers[0]!.onEvent(e)
    expect(store.getState().state).toEqual(reduceAll(HERO_0142))
  })

  it('reconnecting then the next event → open again', async () => {
    const { store, handlers } = setup()
    await store.getState().startRun('0142', opts)
    handlers[0]!.onReconnecting(1)
    expect(store.getState().connection).toBe('reconnecting')
    handlers[0]!.onEvent(HERO_0142[0]!)
    expect(store.getState().connection).toBe('open')
  })

  it('give up → error status, lost connection, stream problem', async () => {
    const { store, handlers } = setup()
    await store.getState().startRun('0142', opts)
    handlers[0]!.onGiveUp()
    const s = store.getState()
    expect(s.status).toBe('error')
    expect(s.connection).toBe('lost')
    expect(s.problem?.kind).toBe('stream')
  })

  it('attach closes the previous stream first', async () => {
    const { store, closes } = setup()
    store.getState().attach('run-a')
    store.getState().attach('run-b')
    expect(closes[0]).toHaveBeenCalledTimes(1)
    expect(closes[1]).not.toHaveBeenCalled()
    expect(store.getState().runId).toBe('run-b')
  })
})
