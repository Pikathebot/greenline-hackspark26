import { describe, expect, it } from 'vitest'
import type { GreenlineEvent } from '../contract/events'
import { reduceAll } from '../state/reducer'
import { HERO_0142, TIGHT_0128 } from '../state/__fixtures__/sequences'
import { buildFeed, type FeedItem } from './feed'
import { stateAfter } from './testHelpers'

type Grid = Extract<FeedItem, { kind: 'grid' }>
const grid = (items: FeedItem[]) => items.find((i): i is Grid => i.kind === 'grid')
const rows = (items: FeedItem[]) => items.filter((i) => i.kind === 'row')

describe('buildFeed', () => {
  it('HERO final: all rows + a 10-cell grid summarising 7 pass / 3 fail', () => {
    const s = reduceAll(HERO_0142)
    const { items, lineCount } = buildFeed(s, false)
    expect(lineCount).toBe(s.evidence.length)
    expect(rows(items)).toHaveLength(s.evidence.length)
    const g = grid(items)!
    expect(g.cells).toHaveLength(10)
    expect(g.summary).toBe('7 pass / 3 fail')
    expect(g.cellMin).toBe('1fr')
  })

  it('grid goes before the first reproducer row when there is no reproducer command', () => {
    const { items } = buildFeed(reduceAll(HERO_0142), false)
    const at = items.findIndex((i) => i.kind === 'grid')
    expect(items[at + 1]).toMatchObject({ kind: 'row', node: 'reproducer' })
    expect(items[at - 1]).toMatchObject({ kind: 'row', node: 'watcher' })
  })

  it('grid goes right after the reproducer command row when there is one', () => {
    const cmd: GreenlineEvent = { t: 2200, type: 'evidence', node: 'reproducer', kind: 'command', text: 'pytest ×10' }
    const seq = [...HERO_0142]
    const at = seq.findIndex((e) => e.type === 'rerun.tick')
    seq.splice(at, 0, cmd)
    const { items } = buildFeed(reduceAll(seq), false)
    const g = items.findIndex((i) => i.kind === 'grid')
    expect(items[g - 1]).toMatchObject({ kind: 'row', node: 'reproducer', glyph: '›' })
  })

  it('marks the analyst line before a fired guardrail as danger', () => {
    const base = reduceAll(HERO_0142)
    const fired = base.guardrails.protected_file!.t
    const withNear: GreenlineEvent[] = HERO_0142.map((e) => e)
    const idx = withNear.findIndex((e) => e.type === 'verdict')
    withNear.splice(idx + 1, 0, {
      t: fired - 50, type: 'evidence', node: 'analyst', kind: 'observation', text: 'fix target is protected',
    } as GreenlineEvent)
    const danger = rows(buildFeed(reduceAll(withNear), false).items).filter((r) => r.kind === 'row' && r.style === 'danger')
    expect(danger).toHaveLength(1)
    expect(danger[0]).toMatchObject({ text: 'fix target is protected' })
    // an observation far from the guardrail stays normal
    const plain = rows(buildFeed(base, false).items).filter((r) => r.kind === 'row' && r.style === 'danger')
    expect(plain).toHaveLength(0)
  })

  it('mid-run: partial grid with pending cells and a progress suffix', () => {
    const s = stateAfter(HERO_0142, 'rerun.tick', 6)
    const g = grid(buildFeed(s, true).items)!
    expect(g.summary).toBe('4 pass / 2 fail  ·  6 / 10')
    expect(g.cells.filter((c) => c.state === 'pending')).toHaveLength(4)
  })

  it('budget exhausted: remaining cells are cap, summary says stopped at cap', () => {
    const g = grid(buildFeed(reduceAll(TIGHT_0128), false).items)!
    expect(g.cells.map((c) => c.state)).toEqual(['fail', 'fail', 'cap'])
    expect(g.summary.endsWith('stopped at cap')).toBe(true)
    expect(g.cellMin).toBe('96px')
  })

  it('no rerun, no grid', () => {
    expect(grid(buildFeed(reduceAll(HERO_0142.slice(0, 8)), true).items)).toBeUndefined()
  })

  it('the last row is highlighted while running', () => {
    const { items } = buildFeed(reduceAll(HERO_0142.slice(0, 8)), true)
    const r = rows(items)
    expect(r[r.length - 1]).toMatchObject({ style: 'newest' })
  })
})
