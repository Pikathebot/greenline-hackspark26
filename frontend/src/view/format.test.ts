import { describe, expect, it } from 'vitest'
import { fmtClock, fmtClockTenths, fmtMeterSeconds, fmtSeconds, formatModel } from './format'

describe('format', () => {
  it('fmtClock floors to whole seconds', () => {
    expect(fmtClock(6200)).toBe('00:06')
    expect(fmtClock(0)).toBe('00:00')
    expect(fmtClock(34000)).toBe('00:34')
    expect(fmtClock(61000)).toBe('01:01')
  })
  it('fmtClockTenths floors to the tenth', () => {
    expect(fmtClockTenths(33950)).toBe('00:33.9')
    expect(fmtClockTenths(34000)).toBe('00:34.0')
    expect(fmtClockTenths(300)).toBe('00:00.3')
  })
  it('fmtSeconds / fmtMeterSeconds', () => {
    expect(fmtSeconds(4120)).toBe('4.1s')
    expect(fmtMeterSeconds(180000)).toBe('180s')
    expect(fmtMeterSeconds(999)).toBe('0s')
  })
  it('formatModel', () => {
    expect(formatModel('qwen3-8b')).toBe('Qwen3-8B')
  })
})
