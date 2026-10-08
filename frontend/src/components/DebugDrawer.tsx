import type { CSSProperties } from 'react'
import { checkInvariants } from '../contract/invariants'
import { useRunStore } from '../state/runStore'
import { useUiStore } from '../state/uiStore'

const MONO: CSSProperties = { fontFamily: "'Geist Mono', ui-monospace, monospace", fontSize: 13 }

export function DebugDrawer() {
  const open = useUiStore((s) => s.debugOpen)
  const run = useRunStore()

  return (
    <>
      <button
        type="button"
        className="btn mono"
        onClick={() => useUiStore.getState().toggleDebug()}
        style={{ position: 'fixed', bottom: 12, right: 12, zIndex: 40, height: 28, fontSize: 13 }}
      >
        Debug
      </button>
      {open && (
        <aside
          style={{
            ...MONO,
            position: 'fixed',
            top: 0,
            bottom: 0,
            right: 0,
            width: 560,
            zIndex: 30,
            overflow: 'auto',
            padding: 16,
            background: 'var(--surface)',
            borderLeft: '1px solid var(--border)',
            color: 'var(--text)',
          }}
        >
          <div>status: {run.status}</div>
          <div>connection: {run.connection}</div>
          <div>runId: {run.runId ?? 'none'}</div>
          <div>problem: {run.problem ? `${run.problem.kind}: ${run.problem.message}` : 'none'}</div>
          <div>events: {run.events.length}</div>
          {run.status === 'done' && <div>invariants: {JSON.stringify(checkInvariants(run.events))}</div>}
          <pre style={{ ...MONO, marginTop: 12, whiteSpace: 'pre-wrap' }}>{JSON.stringify(run.state, null, 2)}</pre>
          <div style={{ marginTop: 12, color: 'var(--muted)' }}>last 20 events</div>
          {run.events.slice(-20).map((e, i) => (
            <div key={i} style={{ wordBreak: 'break-all' }}>
              {JSON.stringify(e)}
            </div>
          ))}
        </aside>
      )}
    </>
  )
}
