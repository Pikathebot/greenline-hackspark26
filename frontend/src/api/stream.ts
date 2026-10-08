import type { GreenlineEvent } from '../contract/events'

export interface StreamHandlers {
  onEvent(e: GreenlineEvent): void
  /** Called before each reopen: the caller clears state, the server resends the full prefix. */
  onReset(): void
  onReconnecting(attempt: number): void
  /** After MAX_RECONNECTS failed reopen attempts. */
  onGiveUp(): void
}

export interface StreamDeps {
  EventSourceImpl?: typeof EventSource
  setTimeout?: (fn: () => void, ms: number) => unknown
  clearTimeout?: (h: unknown) => void
}

export const RECONNECT_DELAY_MS = 1000
export const MAX_RECONNECTS = 5

export function openRunStream(
  runId: string,
  h: StreamHandlers,
  deps: StreamDeps = {},
): { close(): void } {
  const ES = deps.EventSourceImpl ?? EventSource
  const setT = deps.setTimeout ?? ((fn: () => void, ms: number) => setTimeout(fn, ms))
  const clearT = deps.clearTimeout ?? ((t: unknown) => clearTimeout(t as number))

  let current: EventSource | null = null
  let timer: unknown = null
  let attempts = 0
  let finished = false // done received, gave up, or closed by the caller

  function open(): void {
    const es = new ES(`/api/runs/${runId}/stream`)
    current = es

    es.onmessage = (msg: MessageEvent) => {
      if (finished || current !== es) return
      let e: GreenlineEvent
      try {
        e = JSON.parse(msg.data as string) as GreenlineEvent
      } catch {
        console.warn('stream: ignoring malformed event', msg.data)
        return
      }
      attempts = 0
      if (e.type === 'done') {
        // Close immediately, or the browser auto-reconnects and replays the run.
        finished = true
        es.close()
      }
      h.onEvent(e)
    }

    es.onerror = () => {
      if (finished || current !== es) return
      es.close()
      attempts++
      if (attempts > MAX_RECONNECTS) {
        finished = true
        h.onGiveUp()
        return
      }
      h.onReconnecting(attempts)
      timer = setT(() => {
        timer = null
        if (finished) return
        h.onReset()
        open()
      }, RECONNECT_DELAY_MS)
    }
  }

  open()

  return {
    close() {
      finished = true
      if (timer !== null) {
        clearT(timer)
        timer = null
      }
      current?.close()
    },
  }
}
