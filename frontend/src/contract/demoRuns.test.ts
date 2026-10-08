import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { reduceAll } from '../state/reducer'
import type { GreenlineEvent } from './events'
import { checkInvariants } from './invariants'

// Reads Person B's recorded runs (backend/demo_runs/*.json) as test data only.
const DIR = join(process.cwd(), '..', 'backend', 'demo_runs')
const files = readdirSync(DIR).filter((f) => f.endsWith('.json'))

describe('backend/demo_runs', () => {
  it('has at least one recording', () => {
    expect(files.length).toBeGreaterThan(0)
  })
  it.each(files)('%s satisfies the stream invariants', (f) => {
    const events = JSON.parse(readFileSync(join(DIR, f), 'utf8')) as GreenlineEvent[]
    expect(checkInvariants(events)).toEqual([])
  })
  it.each(files)('%s reduces to a finished run', (f) => {
    const events = JSON.parse(readFileSync(join(DIR, f), 'utf8')) as GreenlineEvent[]
    const s = reduceAll(events)
    expect(s.outcome).not.toBeNull()
    expect(s.activeNode).toBeNull()
  })
})
