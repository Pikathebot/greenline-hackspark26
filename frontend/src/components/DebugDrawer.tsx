import { checkInvariants } from '../contract/invariants'
import { useRunStore } from '../state/runStore'
import { useUiStore } from '../state/uiStore'

export function DebugDrawer() {
  const open = useUiStore((s) => s.debugOpen)
  const run = useRunStore()

  return (
    <>
      <button
        type="button"
        onClick={() => useUiStore.getState().toggleDebug()}
        className="fixed bottom-3 right-3 z-40 rounded-md border border-border-strong bg-surface px-3 py-1 font-mono text-[13px]"
      >
        Debug
      </button>
      {open && (
        <aside className="fixed inset-y-0 right-0 z-30 w-[560px] overflow-auto border-l border-border bg-surface p-4 font-mono text-[13px]">
          <div>status: {run.status}</div>
          <div>connection: {run.connection}</div>
          <div>runId: {run.runId ?? 'none'}</div>
          <div>problem: {run.problem ? `${run.problem.kind}: ${run.problem.message}` : 'none'}</div>
          <div>events: {run.events.length}</div>
          {run.status === 'done' && <div>invariants: {JSON.stringify(checkInvariants(run.events))}</div>}
          <pre className="mt-3 whitespace-pre-wrap">{JSON.stringify(run.state, null, 2)}</pre>
          <div className="mt-3 text-muted">last 20 events</div>
          {run.events.slice(-20).map((e, i) => (
            <div key={i} className="break-all">
              {JSON.stringify(e)}
            </div>
          ))}
        </aside>
      )}
    </>
  )
}
