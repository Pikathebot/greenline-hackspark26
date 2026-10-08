import type { RunState } from '../state/runState'
import { OUTCOME_VIEW, RAIL_ORDER } from './consts'
import { GLYPH } from './feed'
import { fmtClockTenths } from './format'

export interface ReportCase {
  id: string
  title: string
  repo: string
  branch: string
}

/** The report can be exported once the run is finished and the Reporter wrote something. */
export function canDownload(s: RunState): boolean {
  return s.report !== null && s.outcome !== null
}

export function reportFilename(s: RunState): string {
  return `greenline-${s.caseId ?? 'run'}-${s.outcome ?? 'run'}.md`
}

export function buildReportMarkdown(s: RunState, c: ReportCase | null): string {
  const id = s.caseId ?? c?.id ?? '?'
  const out: string[] = []
  out.push(c ? `# Greenline report: #${id} ${c.title}` : `# Greenline report: #${id}`)
  out.push('')
  out.push(s.mode === 'demo' ? '> RECORDED: re-streamed real run' : '> LIVE run')
  out.push('')
  if (c) out.push(`- Case: #${c.id} · ${c.repo} · ${c.branch}`)
  const outcome = s.outcome ? OUTCOME_VIEW[s.outcome].label : 'unfinished'
  out.push(
    `- Outcome: ${outcome} · Duration ${fmtClockTenths(s.lastT)} · Model calls ${s.budget.modelCalls} · Sandbox runs ${s.budget.toolCalls}`,
  )

  out.push('', '## Verdict')
  out.push(
    s.verdict
      ? `${s.verdict.cls.toUpperCase()}, ${Math.round(s.verdict.confidence * 100)}% confidence. ${s.verdict.rationale}`
      : 'No verdict reached.',
  )

  out.push('', '## Guardrails')
  for (const rail of RAIL_ORDER) {
    const g = s.guardrails[rail]
    out.push(g ? `- ${rail}: ${g.fired ? 'BLOCKED' : 'clear'}. ${g.note}` : `- ${rail}: not checked yet`)
  }

  out.push('', '## Reruns')
  if (s.rerun && s.rerun.ticks.length > 0) {
    const pass = s.rerun.ticks.filter((t) => t.passed).length
    const fail = s.rerun.ticks.length - pass
    const trail = s.rerun.ticks.map((t) => (t.passed ? 'P' : 'F')).join('')
    out.push(`${pass} pass / ${fail} fail across ${s.rerun.total} isolated reruns (${trail})`)
  } else {
    out.push('No reruns.')
  }

  out.push('', '## Evidence')
  if (s.evidence.length === 0) out.push('No evidence recorded.')
  for (const e of s.evidence) {
    out.push(`- ${fmtClockTenths(e.t)} [${e.node}] ${GLYPH[e.kind]} ${e.text}${e.ref ? ` (${e.ref})` : ''}`)
  }

  if (s.report) {
    out.push('', `## ${s.report.kind === 'pr' ? 'Draft PR' : 'Escalation'}: ${s.report.title}`)
    out.push(s.report.body)
    if (s.report.kind === 'pr' && s.report.prUrl) {
      out.push('', `PR: ${s.report.prUrl}${s.report.dryRun ? ' (dry-run)' : ''}`)
    }
  }

  const last = s.patchAttempts[s.patchAttempts.length - 1]
  if (last && last.result === 'green') {
    out.push('', '## Patch', `File: ${last.file} (attempt ${last.n}, source ${last.source})`)
    out.push('```diff', last.diff.replace(/\n$/, ''), '```')
  }

  return out.join('\n') + '\n'
}
