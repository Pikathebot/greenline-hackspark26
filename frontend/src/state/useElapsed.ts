import { useEffect, useRef, useState } from 'react'
import { useRunStore } from './runStore'

/** Display-only elapsed time: the latest event's t plus the wall time since it arrived. */
export function interpolateElapsed(lastT: number, lastArrivalMs: number, nowMs: number): number {
  return lastT + Math.max(0, nowMs - lastArrivalMs)
}

export function useElapsedMs(): number {
  const status = useRunStore((s) => s.status)
  const lastT = useRunStore((s) => s.state.lastT)
  const arrival = useRef(performance.now())
  const [now, setNow] = useState(() => performance.now())

  useEffect(() => {
    arrival.current = performance.now()
    setNow(arrival.current)
  }, [lastT])

  useEffect(() => {
    if (status !== 'streaming') return
    const id = setInterval(() => setNow(performance.now()), 250)
    return () => clearInterval(id)
  }, [status])

  if (status === 'streaming') return interpolateElapsed(lastT, arrival.current, now)
  if (status === 'done' || status === 'error') return lastT
  return 0
}
