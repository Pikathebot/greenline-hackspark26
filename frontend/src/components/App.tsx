import { useKeyboard } from '../app/useKeyboard'
import { useRunStore } from '../state/runStore'
import { AgentGraph } from './AgentGraph'
import { ArtifactPane } from './ArtifactPane'
import { Banner } from './Banner'
import { CaseBar } from './CaseBar'
import { CaseList } from './CaseList'
import { DebugDrawer } from './DebugDrawer'
import { EvidenceFeed } from './EvidenceFeed'
import { GuardrailList } from './GuardrailList'
import { MemoryCallout } from './MemoryCallout'
import { Narration } from './Narration'
import { RunOptions } from './RunOptions'
import { RunSummary } from './RunSummary'
import { ScoreboardOverlay } from './ScoreboardOverlay'
import { TopBar } from './TopBar'
import { VerdictCard } from './VerdictCard'

export function App() {
  const done = useRunStore((s) => s.state.outcome !== null)

  useKeyboard()

  return (
    <div className="gl">
      <TopBar />
      <Banner />
      <div className="bodyg">
        <aside className="col left">
          <CaseList />
          <RunOptions />
        </aside>
        <main className="col">
          <CaseBar />
          <AgentGraph />
          {done ? <RunSummary /> : <Narration />}
          <MemoryCallout />
          <EvidenceFeed />
        </main>
        <aside className="col right">
          <VerdictCard />
          <GuardrailList />
          <ArtifactPane />
        </aside>
      </div>
      <DebugDrawer />
      <ScoreboardOverlay />
    </div>
  )
}
