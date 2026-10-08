import { useCaseStore } from '../state/caseStore'
import { useRunStore } from '../state/runStore'
import { useUiStore } from '../state/uiStore'

export function CenterColumn() {
  const selectedId = useUiStore((s) => s.selectedCaseId)
  const selected = useCaseStore((s) => s.cases.find((c) => c.id === selectedId) ?? null)
  const run = useRunStore((s) => s.state)

  return (
    <main className="flex min-h-0 flex-col bg-bg">
      <div className="border-b border-border px-6 py-4 font-mono text-[17px]">
        {selected ? `#${selected.id} ${selected.title}` : 'No case selected'}
      </div>
      <div data-slot="agent-graph" className="h-60 border-b border-border px-6 py-4 text-[15px]">
        <div className="text-[13px] text-muted">Agent graph (A4)</div>
        <div className="mt-2 font-mono">{run.path.join(' → ') || 'waiting'}</div>
        <div className="mt-1 text-muted">active: {run.activeNode ?? 'none'}</div>
      </div>
      <div className="flex h-24 items-center border-b border-border px-6 text-[22px]">
        {run.narration ?? 'Ready.'}
      </div>
      <div data-slot="evidence" className="min-h-0 flex-1 overflow-y-auto px-6 py-4 text-[15px] text-muted">
        Evidence feed (A5): {run.evidence.length} items
      </div>
    </main>
  )
}
