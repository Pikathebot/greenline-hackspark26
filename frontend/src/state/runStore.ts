import { create } from 'zustand'
import { api, ApiError, type Api } from '../api/client'
import { openRunStream } from '../api/stream'
import type { StartRunOptions } from '../api/types'
import type { GreenlineEvent } from '../contract/events'
import { useCaseStore } from './caseStore'
import { reduce } from './reducer'
import { EMPTY_STATE, type RunState } from './runState'

export type RunStatus = 'idle' | 'starting' | 'streaming' | 'done' | 'error'
export type Connection = 'none' | 'open' | 'reconnecting' | 'lost'
export interface RunProblem {
  kind: 'conflict' | 'not_found' | 'unreachable' | 'http' | 'stream'
  message: string
}

export interface RunStoreState {
  status: RunStatus
  connection: Connection
  runId: string | null
  /** For debugging only; render from `state`. */
  events: GreenlineEvent[]
  /** reduce() output: the only run data components read. */
  state: RunState
  problem: RunProblem | null
  startRun(caseId: string, opts: StartRunOptions): Promise<void>
  attach(runId: string): void
  receive(e: GreenlineEvent): void
  reset(): void
  clearProblem(): void
}

export function createRunStore(deps: {
  api: Pick<Api, 'startRun'>
  openStream: typeof openRunStream
  onRunDone: () => void
}) {
  let handle: { close(): void } | null = null

  const initial = {
    status: 'idle' as RunStatus,
    connection: 'none' as Connection,
    runId: null as string | null,
    events: [] as GreenlineEvent[],
    state: EMPTY_STATE,
    problem: null as RunProblem | null,
  }

  return create<RunStoreState>()((set, get) => ({
    ...initial,

    async startRun(caseId, opts) {
      const { status } = get()
      if (status === 'starting' || status === 'streaming') return // one GPU, one run
      const previous = status
      set({ status: 'starting', problem: null })
      try {
        const { runId } = await deps.api.startRun(caseId, opts)
        get().attach(runId)
      } catch (err) {
        let problem: RunProblem
        if (err instanceof ApiError) {
          if (err.status === 409) problem = { kind: 'conflict', message: 'A run is already in progress' }
          else if (err.status === 404) problem = { kind: 'not_found', message: err.message }
          else if (err.status === 0) problem = { kind: 'unreachable', message: err.message }
          else problem = { kind: 'http', message: err.message }
        } else {
          problem = { kind: 'http', message: err instanceof Error ? err.message : String(err) }
        }
        set({ status: previous === 'done' ? 'done' : 'idle', problem })
      }
    },

    attach(runId) {
      handle?.close()
      set({
        runId,
        events: [],
        state: EMPTY_STATE,
        status: 'streaming',
        connection: 'open',
        problem: null,
      })
      handle = deps.openStream(runId, {
        onEvent: (e) => {
          if (get().connection === 'reconnecting') set({ connection: 'open' })
          get().receive(e)
        },
        onReset: () => set({ events: [], state: EMPTY_STATE }),
        onReconnecting: () => set({ connection: 'reconnecting' }),
        onGiveUp: () =>
          set({
            status: 'error',
            connection: 'lost',
            problem: { kind: 'stream', message: 'Lost the run stream after 5 retries' },
          }),
      })
    },

    receive(e) {
      const s = get()
      const next = reduce(s.state, e)
      if (e.type === 'done') {
        set({ events: [...s.events, e], state: next, status: 'done', connection: 'none' })
        deps.onRunDone()
      } else {
        set({ events: [...s.events, e], state: next })
      }
    },

    clearProblem() {
      set({ problem: null })
    },

    reset() {
      handle?.close()
      handle = null
      set({ ...initial })
    },
  }))
}

export const useRunStore = createRunStore({
  api,
  openStream: openRunStream,
  onRunDone: () => void useCaseStore.getState().refresh(),
})
