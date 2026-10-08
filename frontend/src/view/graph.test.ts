import { describe, expect, it } from 'vitest'
import { EMPTY_STATE } from '../state/runState'
import { reduceAll } from '../state/reducer'
import { ERROR_RUN, HERO_0142, PATCH_LOOP_0137, TIGHT_0128, WARM_0144 } from '../state/__fixtures__/sequences'
import { arcViews, nodeViews } from './graph'
import { stateAfter } from './testHelpers'

const statuses = (s: ReturnType<typeof reduceAll>) => nodeViews(s).map((n) => n.status)

describe('nodeViews / arcViews', () => {
  it('HERO final', () => {
    const s = reduceAll(HERO_0142)
    const nodes = nodeViews(s)
    expect(statuses(s)).toEqual(['ok', 'ok', 'ok', 'ok', 'idle', 'idle', 'ok'])
    expect(nodes[4]!.detail).toBe('not reached')
    expect(nodes[5]!.detail).toBe('not reached')
    expect(nodes[3]!.barrier).toBe(true)
    expect(nodes[3]!.connColor).toBe('var(--danger)')
    expect(nodes[0]!.connColor).toBe('var(--brand)')
    expect(nodes[4]!.connColor).toBe('var(--border-strong)')
    expect(nodes[6]!.connColor).toBeNull()
    const a = arcViews(s)
    expect(a.esc).toMatchObject({ from: 3, span: 4, on: true, tone: 'warn', label: 'escalate · guardrail' })
    expect(a.bypass).toMatchObject({ show: false, on: false })
    expect(a.loop).toMatchObject({ show: false, on: false })
    expect(a.esc.show).toBe(true)
  })

  it('HERO mid-run: reproducer rerun 6 / 10 with a blue connector in', () => {
    const s = stateAfter(HERO_0142, 'rerun.tick', 6)
    const nodes = nodeViews(s)
    expect(nodes[2]).toMatchObject({ status: 'active', detail: 'rerun 6 / 10' })
    expect(nodes[1]!.connColor).toBe('var(--info)')
  })

  it('WARM final: memory skip', () => {
    const s = reduceAll(WARM_0144)
    expect(nodeViews(s)[2]).toMatchObject({ status: 'skip', detail: 'skipped · memory' })
    expect(arcViews(s).bypass).toMatchObject({ show: true, on: true, label: 'skipped · memory hit #0142' })
  })

  it('idle and mid-run keep every arc visible', () => {
    const idle = arcViews(EMPTY_STATE)
    expect([idle.loop.show, idle.bypass.show, idle.esc.show]).toEqual([true, true, true])
    const mid = arcViews(stateAfter(HERO_0142, 'rerun.tick', 6))
    expect([mid.loop.show, mid.bypass.show, mid.esc.show]).toEqual([true, true, true])
  })

  it('PATCH_LOOP mid-run: second patcher attempt, critic rejected', () => {
    const s = stateAfter(PATCH_LOOP_0137, 'node.enter', 2, (e) => e.type === 'node.enter' && e.node === 'patcher')
    const nodes = nodeViews(s)
    expect(nodes[4]).toMatchObject({ status: 'active', detail: 'attempt 2 / 2' })
    expect(nodes[5]).toMatchObject({ status: 'fail', detail: 'rejected #1' })
    expect(arcViews(s).loop).toMatchObject({ on: true, label: 'Critic → Patcher · attempt 2 / 2' })
  })

  it('PATCH_LOOP final: critic ok after an approving vote, no escalation arc', () => {
    const s = reduceAll(PATCH_LOOP_0137)
    expect(nodeViews(s)[5]!.status).toBe('ok')
    expect(arcViews(s).esc.on).toBe(false)
  })

  it('TIGHT final: budget arc from the reproducer, bypass hidden', () => {
    const a = arcViews(reduceAll(TIGHT_0128))
    expect(a.esc).toMatchObject({ from: 2, tone: 'warn', label: 'budget exhausted → report' })
    expect(a.bypass.show).toBe(false)
  })

  it('ERROR final: triage failed, error arc from triage', () => {
    const s = reduceAll(ERROR_RUN)
    expect(nodeViews(s)[1]!.status).toBe('fail')
    expect(arcViews(s).esc).toMatchObject({ from: 1, tone: 'danger', label: 'error → report' })
  })

  it('EMPTY_STATE: everything idle and waiting', () => {
    expect(statuses(EMPTY_STATE)).toEqual(Array(7).fill('idle'))
    expect(nodeViews(EMPTY_STATE).every((n) => n.detail === 'waiting')).toBe(true)
    expect(arcViews(EMPTY_STATE).esc).toMatchObject({ from: 3, on: false, label: 'escalate if blocked' })
  })
})
