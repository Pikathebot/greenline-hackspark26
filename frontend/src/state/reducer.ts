import type { GreenlineEvent } from '../contract/events'
import { EMPTY_STATE, type RunState } from './runState'

export { EMPTY_STATE }
export type { RunState }

/** Close the active node as failed (error/done/overlapping enter), keeping everything else. */
function failActive(state: RunState, t: number): RunState {
  const id = state.activeNode
  if (id === null) return state
  const prev = state.nodes[id]
  return {
    ...state,
    activeNode: null,
    nodes: {
      ...state.nodes,
      [id]: {
        status: 'done',
        outcome: 'fail',
        durationMs: t - (prev.enteredAt ?? t),
        ...(prev.enteredAt !== undefined && { enteredAt: prev.enteredAt }),
      },
    },
  }
}

export function reduce(state: RunState, e: GreenlineEvent): RunState {
  if (e.type === 'run.start') {
    return {
      ...EMPTY_STATE,
      runId: e.runId,
      caseId: e.caseId,
      mode: e.mode,
      model: e.model,
      budgetPreset: e.budgetPreset,
      caps: { ...e.caps },
      lastT: e.t,
    }
  }
  const s: RunState = { ...state, lastT: Math.max(state.lastT, e.t) }

  switch (e.type) {
    case 'node.enter': {
      const closed = s.activeNode !== null && s.activeNode !== e.node ? failActive(s, e.t) : s
      return {
        ...closed,
        nodes: { ...closed.nodes, [e.node]: { status: 'active', enteredAt: e.t } },
        activeNode: e.node,
        path: [...closed.path, e.node],
      }
    }
    case 'node.exit': {
      const prev = s.nodes[e.node]
      return {
        ...s,
        nodes: {
          ...s.nodes,
          [e.node]: {
            status: 'done',
            outcome: e.status,
            durationMs: e.durationMs,
            ...(prev.enteredAt !== undefined && { enteredAt: prev.enteredAt }),
            ...(e.note !== undefined && { note: e.note }),
          },
        },
        activeNode: s.activeNode === e.node ? null : s.activeNode,
      }
    }
    case 'log':
      return {
        ...s,
        logs: [...s.logs, { t: e.t, node: e.node, level: e.level, text: e.text }],
        narration: e.level === 'info' ? e.text : s.narration,
      }
    case 'evidence':
      return {
        ...s,
        evidence: [
          ...s.evidence,
          {
            t: e.t,
            node: e.node,
            kind: e.kind,
            text: e.text,
            ...(e.ref !== undefined && { ref: e.ref }),
          },
        ],
      }
    case 'rerun.tick':
      return {
        ...s,
        rerun: {
          total: e.total,
          ticks: [...(s.rerun?.ticks ?? []), { n: e.n, passed: e.passed, durationMs: e.durationMs }],
        },
      }
    case 'memory.hit':
      return { ...s, memoryHit: { caseRef: e.caseRef, similarity: e.similarity, summary: e.summary } }
    case 'verdict':
      return { ...s, verdict: { cls: e.cls, confidence: e.confidence, rationale: e.rationale } }
    case 'patch.attempt':
      return {
        ...s,
        patchAttempts: [
          ...s.patchAttempts,
          { n: e.n, file: e.file, diff: e.diff, source: e.source, result: e.result },
        ],
      }
    case 'critic.vote':
      return {
        ...s,
        criticVotes: [
          ...s.criticVotes,
          {
            n: e.n,
            samples: [...e.samples],
            deterministic: e.deterministic.map((c) => ({ ...c })),
            approved: e.approved,
          },
        ],
      }
    case 'budget':
      return { ...s, budget: { modelCalls: e.modelCalls, toolCalls: e.toolCalls, elapsedMs: e.elapsedMs } }
    case 'guardrail':
      return { ...s, guardrails: { ...s.guardrails, [e.rail]: { fired: e.fired, note: e.note, t: e.t } } }
    case 'report':
      return {
        ...s,
        report: {
          kind: e.kind,
          title: e.title,
          body: e.body,
          ...(e.prUrl !== undefined && { prUrl: e.prUrl }),
          ...(e.dryRun !== undefined && { dryRun: e.dryRun }),
        },
      }
    case 'error':
      return { ...failActive(s, e.t), error: e.message }
    case 'done':
      return { ...failActive(s, e.t), outcome: e.outcome }
    default: {
      const _x: never = e
      return _x
    }
  }
}

export function reduceAll(events: readonly GreenlineEvent[], from: RunState = EMPTY_STATE): RunState {
  return events.reduce(reduce, from)
}
