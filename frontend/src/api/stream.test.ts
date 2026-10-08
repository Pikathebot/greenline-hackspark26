import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { GreenlineEvent } from '../contract/events'
import { MAX_RECONNECTS, RECONNECT_DELAY_MS, openRunStream, type StreamHandlers } from './stream'

class FakeEventSource {
  static instances: FakeEventSource[] = []
  closed = false
  onmessage: ((m: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  constructor(public url: string) {
    FakeEventSource.instances.push(this)
  }
  close() {
    this.closed = true
  }
  emit(obj: unknown) {
    this.onmessage?.({ data: typeof obj === 'string' ? obj : JSON.stringify(obj) })
  }
  fail() {
    this.onerror?.()
  }
}

const log = (t: number): GreenlineEvent => ({ t, type: 'log', node: 'watcher', level: 'info', text: 'x' })
const done = (t: number): GreenlineEvent => ({ t, type: 'done', outcome: 'escalated' })

function setup() {
  const h = {
    onEvent: vi.fn(),
    onReset: vi.fn(),
    onReconnecting: vi.fn(),
    onGiveUp: vi.fn(),
  } satisfies StreamHandlers
  const handle = openRunStream('run-1', h, {
    EventSourceImpl: FakeEventSource as unknown as typeof EventSource,
  })
  const latest = () => FakeEventSource.instances[FakeEventSource.instances.length - 1]!
  return { h, handle, latest }
}

beforeEach(() => {
  FakeEventSource.instances = []
  vi.useFakeTimers()
})
afterEach(() => {
  vi.useRealTimers()
})

describe('openRunStream', () => {
  it('opens the run stream and forwards parsed events in order', () => {
    const { h, latest } = setup()
    expect(latest().url).toBe('/api/runs/run-1/stream')
    latest().emit(log(1))
    latest().emit(log(2))
    expect(h.onEvent.mock.calls.map((c) => (c[0] as GreenlineEvent).t)).toEqual([1, 2])
  })

  it('closes on done and ignores everything after', () => {
    const { h, latest } = setup()
    const es = latest()
    es.emit(done(5))
    expect(es.closed).toBe(true)
    expect(h.onEvent).toHaveBeenCalledTimes(1)
    es.emit(log(6))
    es.fail()
    vi.advanceTimersByTime(RECONNECT_DELAY_MS * 2)
    expect(h.onEvent).toHaveBeenCalledTimes(1)
    expect(h.onReconnecting).not.toHaveBeenCalled()
    expect(FakeEventSource.instances).toHaveLength(1)
  })

  it('reconnects after an error: resets state, then opens a new source', () => {
    const { h, latest } = setup()
    const first = latest()
    first.fail()
    expect(h.onReconnecting).toHaveBeenCalledWith(1)
    expect(first.closed).toBe(true)
    expect(FakeEventSource.instances).toHaveLength(1)
    vi.advanceTimersByTime(RECONNECT_DELAY_MS)
    expect(h.onReset).toHaveBeenCalledTimes(1)
    expect(FakeEventSource.instances).toHaveLength(2)
  })

  it('gives up after MAX_RECONNECTS failed reopens', () => {
    const { h, latest } = setup()
    for (let i = 0; i < MAX_RECONNECTS; i++) {
      latest().fail()
      vi.advanceTimersByTime(RECONNECT_DELAY_MS)
    }
    expect(FakeEventSource.instances).toHaveLength(MAX_RECONNECTS + 1)
    latest().fail()
    expect(h.onGiveUp).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(RECONNECT_DELAY_MS * 2)
    expect(FakeEventSource.instances).toHaveLength(MAX_RECONNECTS + 1)
  })

  it('a successfully parsed event resets the attempt counter', () => {
    const { h, latest } = setup()
    latest().fail()
    vi.advanceTimersByTime(RECONNECT_DELAY_MS)
    latest().emit(log(1))
    latest().fail()
    expect(h.onReconnecting).toHaveBeenLastCalledWith(1)
  })

  it('close() during the wait cancels the reopen', () => {
    const { h, handle, latest } = setup()
    latest().fail()
    handle.close()
    vi.advanceTimersByTime(RECONNECT_DELAY_MS * 2)
    expect(h.onReset).not.toHaveBeenCalled()
    expect(FakeEventSource.instances).toHaveLength(1)
  })

  it('ignores malformed data', () => {
    const { h, latest } = setup()
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    expect(() => latest().emit('not json')).not.toThrow()
    expect(h.onEvent).not.toHaveBeenCalled()
    warn.mockRestore()
  })
})
