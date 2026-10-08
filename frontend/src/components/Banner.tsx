import { useEffect } from 'react'
import { Warn } from '../design/icons'
import { useHealthStore } from '../state/healthStore'
import { useRunStore } from '../state/runStore'
import { noticeView } from '../view/notices'

const AUTO_DISMISS_MS = 6000

export function Banner() {
  const reachable = useHealthStore((s) => s.backendReachable)
  const connection = useRunStore((s) => s.connection)
  const problem = useRunStore((s) => s.problem)
  const status = useRunStore((s) => s.status)
  const runError = useRunStore((s) => s.state.error)
  const notice = noticeView({ reachable, connection, problem, runError, status })
  const autoDismiss = notice?.autoDismiss ?? false

  useEffect(() => {
    if (!autoDismiss) return
    const id = setTimeout(() => useRunStore.getState().clearProblem(), AUTO_DISMISS_MS)
    return () => clearTimeout(id)
  }, [autoDismiss, problem])

  if (!notice) return null
  return (
    <div
      className="banner"
      role="alert"
      style={notice.tone === 'warn' ? { background: 'var(--warn)', color: 'var(--on-warn)' } : undefined}
    >
      <Warn />
      <span>{notice.title}</span>
      <span className="sub">{notice.sub}</span>
    </div>
  )
}
