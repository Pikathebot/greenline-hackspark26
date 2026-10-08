import type { EventType, GreenlineEvent } from '../contract/events'
import { reduceAll } from '../state/reducer'
import type { RunState } from '../state/runState'

/** State after the n-th (1-based) event of the given type. Test helper only. */
export function stateAfter(seq: GreenlineEvent[], type: EventType, n: number, extra?: (e: GreenlineEvent) => boolean): RunState {
  let seen = 0
  for (let i = 0; i < seq.length; i++) {
    const e = seq[i]!
    if (e.type === type && (!extra || extra(e)) && ++seen === n) return reduceAll(seq.slice(0, i + 1))
  }
  throw new Error(`no ${n}th ${type}`)
}
