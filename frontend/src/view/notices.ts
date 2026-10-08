import type { Connection, RunProblem, RunStatus } from '../state/runStore'

export interface NoticeView {
  title: string
  sub: string
  tone: 'danger' | 'warn'
  autoDismiss: boolean
}

/** Picks the single banner to show; first match wins. */
export function noticeView(p: {
  reachable: boolean | null
  connection: Connection
  problem: RunProblem | null
  runError: string | null
  status: RunStatus
}): NoticeView | null {
  const { reachable, connection, problem, runError } = p
  if (reachable === false) {
    return {
      title: 'Backend offline: start uvicorn on :8000',
      sub: 'Retrying every 3 s. Nothing below is live until it answers.',
      tone: 'danger',
      autoDismiss: false,
    }
  }
  if (connection === 'reconnecting') {
    return {
      title: 'Reconnecting to the run stream…',
      sub: 'The server replays the whole run once the link is back.',
      tone: 'warn',
      autoDismiss: false,
    }
  }
  if (problem?.kind === 'stream') {
    return {
      title: 'Lost the run stream',
      sub: `${problem.message}. Press Enter to run again.`,
      tone: 'danger',
      autoDismiss: false,
    }
  }
  if (problem?.kind === 'conflict') {
    return {
      title: 'A run is already in progress',
      sub: 'Wait for it to finish, then run again.',
      tone: 'warn',
      autoDismiss: true,
    }
  }
  if (problem?.kind === 'not_found') {
    return { title: "Can't start that run", sub: problem.message, tone: 'danger', autoDismiss: false }
  }
  if (problem?.kind === 'unreachable' || problem?.kind === 'http') {
    return { title: "Couldn't start the run", sub: problem.message, tone: 'danger', autoDismiss: false }
  }
  if (runError) {
    return {
      title: `Run error: ${runError}`,
      sub: 'The run ended with outcome error.',
      tone: 'danger',
      autoDismiss: false,
    }
  }
  return null
}
