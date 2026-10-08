import type { RunState } from '../state/runState'
import { MAX_PATCH_ATTEMPTS } from './consts'

export interface DiffLine {
  kind: 'hunk' | 'add' | 'del' | 'ctx'
  text: string
}

const HEADER = /^(diff |index |--- |\+\+\+ )/

/** Tolerant unified-diff parser: header lines (before the first hunk) are dropped, unknown lines become context. */
export function parseDiff(diff: string): DiffLine[] {
  if (!diff) return []
  const raw = diff.split('\n')
  if (raw[raw.length - 1] === '') raw.pop()
  const out: DiffLine[] = []
  let inBody = false
  for (const line of raw) {
    if (!inBody && HEADER.test(line)) continue
    if (line.startsWith('\\')) continue
    if (line.startsWith('@@')) {
      inBody = true
      out.push({ kind: 'hunk', text: line })
    } else if (line.startsWith('+')) out.push({ kind: 'add', text: line })
    else if (line.startsWith('-')) out.push({ kind: 'del', text: line })
    else out.push({ kind: 'ctx', text: line.startsWith(' ') ? line : ` ${line}` })
  }
  return out
}

export interface CheckView {
  name: string
  passed: boolean
  detail: string
}

export interface VoteView {
  n: number
  approvals: number
  total: number
  samples: ('approve' | 'reject')[]
  approved: boolean
  text: string
  checks: CheckView[]
}

/** The critic vote for attempt n (the latest one if several), else null. */
export function voteView(s: RunState, n: number): VoteView | null {
  const votes = s.criticVotes.filter((v) => v.n === n)
  const v = votes[votes.length - 1]
  if (!v) return null
  const approvals = v.samples.filter((x) => x === 'approve').length
  const total = v.samples.length
  const text =
    total > 0
      ? v.approved
        ? `approved ${approvals} / ${total}`
        : `rejected ${total - approvals} / ${total}`
      : v.approved
        ? 'approved by deterministic checks'
        : 'rejected by deterministic checks'
  return {
    n,
    approvals,
    total,
    samples: [...v.samples],
    approved: v.approved,
    text,
    checks: v.deterministic.map((c) => ({ name: c.name, passed: c.passed, detail: c.detail ?? '' })),
  }
}

export interface AttemptView {
  n: number
  file: string
  source: 'model' | 'tool'
  state: 'green' | 'red' | 'vetoed' | 'running'
  /** muted text after the result chip */
  note: string
  diff: DiffLine[]
  vote: VoteView | null
  /** true only for the in-progress card */
  running: boolean
  /** running card text */
  body: string
}

export function attemptViews(s: RunState): { attempts: AttemptView[]; acceptedN: number | null } {
  const attempts: AttemptView[] = s.patchAttempts.map((p) => {
    const vote = voteView(s, p.n)
    let note: string
    if (p.result === 'vetoed') note = 'blocked by a guardrail'
    else if (p.result === 'red' || vote?.approved === false) note = 'rejected by Critic'
    else if (vote?.approved) note = 'approved by Critic'
    else note = 'awaiting Critic'
    return {
      n: p.n,
      file: p.file,
      source: p.source,
      state: p.result,
      note,
      diff: parseDiff(p.diff),
      vote,
      running: false,
      body: '',
    }
  })

  const patcherEntries = s.path.filter((id) => id === 'patcher').length
  if (s.outcome === null && s.activeNode === 'patcher' && patcherEntries > s.patchAttempts.length) {
    attempts.push({
      n: patcherEntries,
      file: '',
      source: 'model',
      state: 'running',
      note: `${patcherEntries} / ${MAX_PATCH_ATTEMPTS}`,
      diff: [],
      vote: null,
      running: true,
      body: s.narration ?? 'Running the patched tests in the sandbox.',
    })
  }

  let acceptedN: number | null = null
  if (s.report?.kind === 'pr') {
    for (const p of s.patchAttempts) if (p.result === 'green') acceptedN = p.n
  }
  return { attempts, acceptedN }
}
