import { Warn } from '../design/icons'
import { useHealthStore } from '../state/healthStore'
import { useRunStore } from '../state/runStore'
import { bannerView } from '../view/chrome'

export function Banner() {
  const reachable = useHealthStore((s) => s.backendReachable)
  const runError = useRunStore((s) => s.state.error)
  const b = bannerView({ reachable, runError })
  if (!b) return null
  return (
    <div className="banner" role="alert">
      <Warn />
      <span>{b.title}</span>
      <span className="sub">{b.sub}</span>
    </div>
  )
}
