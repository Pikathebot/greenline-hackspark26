import { describe, expect, it } from 'vitest'
import { interpolateElapsed } from './useElapsed'

describe('interpolateElapsed', () => {
  it('adds the wall time since the last event', () => {
    expect(interpolateElapsed(5000, 1000, 1750)).toBe(5750)
  })
  it('never goes backwards', () => {
    expect(interpolateElapsed(5000, 2000, 1000)).toBe(5000)
  })
})
