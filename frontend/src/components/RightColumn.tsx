import type { ReactNode } from 'react'
import { useRunStore } from '../state/runStore'

function Card({ slot, title, children }: { slot: string; title: string; children: ReactNode }) {
  return (
    <section data-slot={slot} className="rounded-lg border border-border bg-surface p-4">
      <div className="text-[13px] font-semibold tracking-wider text-muted">{title}</div>
      <div className="mt-2 text-[15px]">{children}</div>
    </section>
  )
}

export function RightColumn() {
  const run = useRunStore((s) => s.state)
  const railsChecked = Object.values(run.guardrails).filter((g) => g !== undefined).length

  return (
    <aside className="flex min-h-0 flex-col gap-3 overflow-y-auto border-l border-border bg-bg p-4">
      <Card slot="verdict" title="VERDICT">
        {run.verdict ? run.verdict.cls : 'No verdict yet'}
      </Card>
      <Card slot="guardrails" title="GUARDRAILS">
        {railsChecked} of 5 checked
      </Card>
      <Card slot="artifact" title="ARTIFACT">
        {run.report ? run.report.kind : 'No report yet'}
      </Card>
    </aside>
  )
}
