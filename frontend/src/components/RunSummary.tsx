import { useRunStore } from '../state/runStore'
import { TONE } from '../view/consts'
import { summaryView } from '../view/chrome'

export function RunSummary() {
  const sum = summaryView(useRunStore((s) => s.state))
  if (!sum) return null
  return (
    <div className="sum">
      <div className="grow" style={{ minWidth: 0 }}>
        <div className="sum-o" style={{ color: TONE[sum.tone].c }}>
          {sum.outcomeLabel}
        </div>
        <div className="sum-t">{sum.text}</div>
      </div>
      <div className="stat">
        <span className="lbl">Duration</span>
        <span className="stat-v mono">{sum.duration}</span>
      </div>
      <div className="stat">
        <span className="lbl">Model calls</span>
        <span className="stat-v mono">{sum.modelCalls}</span>
      </div>
      <div className="stat">
        <span className="lbl">Sandbox runs</span>
        <span className="stat-v mono">{sum.sandboxRuns}</span>
      </div>
    </div>
  )
}
