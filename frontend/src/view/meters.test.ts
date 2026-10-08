import { describe, expect, it } from 'vitest'
import { EMPTY_STATE } from '../state/runState'
import { reduceAll } from '../state/reducer'
import { HERO_0142, TIGHT_0128 } from '../state/__fixtures__/sequences'
import { meterViews } from './meters'

const base = { status: 'idle' as const, preset: 'normal' as const, elapsedMs: 0, available: true }
const pair = (m: ReturnType<typeof meterViews>) => m.map((x) => `${x.val}/${x.cap}`)

describe('meterViews', () => {
  it('idle uses the preset caps', () => {
    expect(pair(meterViews({ ...base, s: EMPTY_STATE }))).toEqual(['0/16', '0/16', '0s/180s'])
    expect(pair(meterViews({ ...base, s: EMPTY_STATE, preset: 'tight' }))).toEqual(['0/4', '0/3', '0s/60s'])
  })
  it('unavailable shows dashes', () => {
    expect(pair(meterViews({ ...base, s: EMPTY_STATE, available: false }))).toEqual(['–/–', '–/–', '–/–'])
  })
  it('HERO final uses run caps and budget', () => {
    const s = reduceAll(HERO_0142)
    const m = meterViews({ ...base, s, status: 'done', elapsedMs: s.lastT })
    expect(pair(m)).toEqual(['1/16', '1/16', `${Math.floor(s.lastT / 1000)}s/180s`])
    expect(m[0]!.valColor).toBe('var(--text)')
  })
  it('running is blue', () => {
    const m = meterViews({ ...base, s: reduceAll(HERO_0142.slice(0, 5)), status: 'streaming' })
    expect(m[0]!.valColor).toBe('var(--info)')
  })
  it('budget exhausted raises the alarm', () => {
    const s = reduceAll(TIGHT_0128)
    const m = meterViews({ ...base, s, status: 'done', elapsedMs: s.lastT })
    expect(m[1]).toMatchObject({ val: '3', cap: '3', pct: 100, alarm: true, valColor: 'var(--danger)' })
  })
  it('>= 80% alarms', () => {
    const s = { ...reduceAll(HERO_0142.slice(0, 1)), budget: { modelCalls: 13, toolCalls: 0, elapsedMs: 0 } }
    expect(meterViews({ ...base, s })[0]!.alarm).toBe(true)
  })
})
