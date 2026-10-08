import { useCaseStore } from '../state/caseStore'
import { useRunStore } from '../state/runStore'
import { useUiStore } from '../state/uiStore'

function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: { value: T; label: string; disabled?: boolean }[]
  onChange: (v: T) => void
}) {
  return (
    <div className="grid grid-flow-col gap-1 rounded-md border border-border bg-surface p-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          disabled={o.disabled}
          onClick={() => onChange(o.value)}
          className={`rounded-sm px-3 py-2 text-[15px] disabled:cursor-not-allowed disabled:opacity-40 ${
            value === o.value ? 'bg-surface-2 text-text' : 'text-muted'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function LeftColumn() {
  const cases = useCaseStore((s) => s.cases)
  const selectedId = useUiStore((s) => s.selectedCaseId)
  const budget = useUiStore((s) => s.budgetPreset)
  const mode = useUiStore((s) => s.mode)
  const status = useRunStore((s) => s.status)
  const selected = cases.find((c) => c.id === selectedId) ?? null
  const busy = status === 'starting' || status === 'streaming'

  return (
    <aside className="flex min-h-0 flex-col border-r border-border bg-surface">
      <div className="flex items-center justify-between px-5 py-4 text-[13px] font-semibold tracking-wider text-muted">
        <span>FAILURE CASES</span>
        <span>{cases.length}</span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-3">
        {cases.map((c) => (
          <button
            key={c.id}
            type="button"
            title={c.beat}
            onClick={() => useUiStore.getState().selectCase(c.id)}
            className={`mb-2 block w-full rounded-lg border px-3 py-3 text-left ${
              c.id === selectedId ? 'border-border-strong bg-surface-2' : 'border-transparent'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="font-mono font-semibold text-brand-ink">#{c.id}</span>
              <span className="rounded-sm border border-border px-2 text-[13px] text-muted">{c.cls}</span>
              <span className="ml-auto text-[13px] text-warn">{c.lastRun?.outcome ?? 'not run'}</span>
            </div>
            <div className="mt-1 truncate font-mono text-[15px]">{c.title}</div>
          </button>
        ))}
      </div>
      <div className="flex flex-col gap-3 border-t border-border p-4">
        <Segmented
          value={budget}
          onChange={(b) => useUiStore.getState().setBudget(b)}
          options={[
            { value: 'normal', label: 'Normal' },
            { value: 'tight', label: 'Tight' },
          ]}
        />
        <Segmented
          value={mode}
          onChange={(m) => useUiStore.getState().setMode(m)}
          options={[
            { value: 'live', label: 'Live' },
            { value: 'demo', label: 'Recorded', disabled: !selected?.hasDemoRun },
          ]}
        />
        <button
          type="button"
          disabled={!selected || busy}
          onClick={() => {
            if (selected) void useRunStore.getState().startRun(selected.id, { mode, budget })
          }}
          className="rounded-lg bg-brand px-4 py-3 text-[15px] font-semibold text-on-accent disabled:cursor-not-allowed disabled:opacity-40"
        >
          {selected ? `Run #${selected.id}` : 'Run'}
        </button>
      </div>
    </aside>
  )
}
