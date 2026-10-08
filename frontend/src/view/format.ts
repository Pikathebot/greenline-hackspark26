const pad2 = (n: number) => String(n).padStart(2, '0')

/** MM:SS (floor seconds). */
export function fmtClock(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000))
  return `${pad2(Math.floor(total / 60))}:${pad2(total % 60)}`
}

/** MM:SS.t (floor to the tenth). */
export function fmtClockTenths(ms: number): string {
  const tenths = Math.max(0, Math.floor(ms / 100))
  const total = Math.floor(tenths / 10)
  return `${pad2(Math.floor(total / 60))}:${pad2(total % 60)}.${tenths % 10}`
}

/** One decimal + s: 4120 -> 4.1s */
export function fmtSeconds(ms: number): string {
  return `${(ms / 1000).toFixed(1)}s`
}

/** Whole seconds for the time meter: 180000 -> 180s */
export function fmtMeterSeconds(ms: number): string {
  return `${Math.floor(ms / 1000)}s`
}

/** qwen3-8b -> Qwen3-8B */
export function formatModel(name: string): string {
  if (!name) return name
  return (name[0]!.toUpperCase() + name.slice(1)).replace(/(\d)b\b/i, '$1B')
}
