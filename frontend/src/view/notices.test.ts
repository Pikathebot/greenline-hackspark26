import { describe, expect, it } from 'vitest'
import type { RunProblem } from '../state/runStore'
import { noticeView } from './notices'

const clear = { reachable: true, connection: 'none' as const, problem: null, runError: null, status: 'idle' as const }
const problem = (kind: RunProblem['kind'], message = 'msg'): RunProblem => ({ kind, message })

describe('noticeView', () => {
  it('nothing to say when all is clear (or the backend has not been checked yet)', () => {
    expect(noticeView(clear)).toBeNull()
    expect(noticeView({ ...clear, reachable: null })).toBeNull()
  })
  it('offline', () => {
    expect(noticeView({ ...clear, reachable: false })).toMatchObject({
      title: 'Backend offline: start uvicorn on :8000', tone: 'danger', autoDismiss: false,
    })
  })
  it('reconnecting is amber', () => {
    expect(noticeView({ ...clear, connection: 'reconnecting' })).toMatchObject({
      title: 'Reconnecting to the run stream…', tone: 'warn',
    })
  })
  it('lost stream', () => {
    expect(noticeView({ ...clear, problem: problem('stream', 'Lost the run stream after 5 retries') })).toMatchObject({
      title: 'Lost the run stream', sub: 'Lost the run stream after 5 retries. Press Enter to run again.', tone: 'danger',
    })
  })
  it('conflict is amber and auto-dismisses; nothing else does', () => {
    const c = noticeView({ ...clear, problem: problem('conflict') })!
    expect(c).toMatchObject({ title: 'A run is already in progress', tone: 'warn', autoDismiss: true })
    for (const k of ['stream', 'not_found', 'unreachable', 'http'] as const) {
      expect(noticeView({ ...clear, problem: problem(k) })!.autoDismiss).toBe(false)
    }
    expect(noticeView({ ...clear, runError: 'x' })!.autoDismiss).toBe(false)
  })
  it('start failures', () => {
    expect(noticeView({ ...clear, problem: problem('not_found', 'no recorded demo run') })).toMatchObject({
      title: "Can't start that run", sub: 'no recorded demo run', tone: 'danger',
    })
    expect(noticeView({ ...clear, problem: problem('unreachable', 'backend unreachable') })).toMatchObject({
      title: "Couldn't start the run", sub: 'backend unreachable',
    })
    expect(noticeView({ ...clear, problem: problem('http', 'Internal Server Error') })!.title).toBe("Couldn't start the run")
  })
  it('run error', () => {
    expect(noticeView({ ...clear, runError: 'model server unreachable' })).toMatchObject({
      title: 'Run error: model server unreachable', sub: 'The run ended with outcome error.', tone: 'danger',
    })
  })
  it('precedence: offline > reconnecting > stream > conflict > not_found > runError', () => {
    const all = { reachable: false as boolean | null, connection: 'reconnecting' as const, problem: problem('stream'), runError: 'x', status: 'idle' as const }
    expect(noticeView(all)!.title).toMatch(/^Backend offline/)
    expect(noticeView({ ...all, reachable: true })!.title).toMatch(/^Reconnecting/)
    expect(noticeView({ ...all, reachable: true, connection: 'open' })!.title).toBe('Lost the run stream')
    expect(noticeView({ ...all, reachable: true, connection: 'open', problem: problem('conflict') })!.title).toMatch(/already in progress/)
    expect(noticeView({ ...all, reachable: true, connection: 'open', problem: null })!.title).toMatch(/^Run error/)
  })
})
