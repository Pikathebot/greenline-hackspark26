import { useHealthStore } from '../state/healthStore'
import { useRunStore } from '../state/runStore'

function Dot({ ok, label }: { ok: boolean | null; label: string }) {
  const colour = ok === null ? 'bg-muted' : ok ? 'bg-brand' : 'bg-danger'
  return (
    <span className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-1 text-[13px]">
      <span className={`h-2 w-2 rounded-full ${colour}`} />
      {label}
    </span>
  )
}

export function TopBarShell() {
  const health = useHealthStore((s) => s.health)
  const reachable = useHealthStore((s) => s.backendReachable)
  const mode = useRunStore((s) => s.state.mode)
  const model = useRunStore((s) => s.state.model)
  const status = useRunStore((s) => s.status)

  // A stale health snapshot (backend down) shows as unknown rather than green.
  const live = reachable === false ? null : health
  return (
    <header className="flex items-center gap-4 border-b border-border bg-bg px-5">
      <div className="flex items-center gap-3">
        <div className="h-7 w-7 rounded-md bg-brand" />
        <span className="text-[20px] font-semibold">Greenline</span>
      </div>
      <span className="rounded-md border border-border bg-surface px-3 py-1 font-mono text-[13px]">
        {model ?? live?.modelServer.model ?? 'model'} · local
      </span>
      <Dot label="Model" ok={live ? live.modelServer.reachable : null} />
      <Dot label="Memory" ok={live ? live.embedServer.reachable : null} />
      <Dot label="Sandbox" ok={live ? live.docker.reachable && live.docker.sandboxImage : null} />
      <div data-slot="meters" className="ml-auto" />
      {mode === 'demo' && (
        <span className="rounded-md bg-warn px-3 py-1 text-[13px] font-semibold text-on-warn">RECORDED</span>
      )}
      {status === 'streaming' && mode === 'live' && (
        <span className="flex items-center gap-2 rounded-md bg-info-tint px-3 py-1 text-[13px] font-semibold text-info">
          <span className="h-2 w-2 animate-pulse rounded-full bg-info" />
          LIVE
        </span>
      )}
    </header>
  )
}
