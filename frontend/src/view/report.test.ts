import { describe, expect, it } from 'vitest'
import { EMPTY_STATE } from '../state/runState'
import { reduceAll } from '../state/reducer'
import { HERO_0142, PATCH_LOOP_0137, TIGHT_0128 } from '../state/__fixtures__/sequences'
import { buildReportMarkdown, canDownload, reportFilename } from './report'

const info = { id: '0142', title: 'test_settlement_reconciles_at_eod', repo: 'acme/ledger-core', branch: 'case/0142-flaky-settlement' }
const hero = reduceAll(HERO_0142)

describe('canDownload / reportFilename', () => {
  it('needs a report and a finished run', () => {
    expect(canDownload(EMPTY_STATE)).toBe(false)
    expect(canDownload({ ...hero, outcome: null })).toBe(false)
    expect(canDownload({ ...hero, report: null })).toBe(false)
    expect(canDownload(hero)).toBe(true)
  })
  it('names the file after the case and outcome', () => {
    expect(reportFilename(hero)).toBe('greenline-0142-escalated.md')
  })
})

describe('buildReportMarkdown', () => {
  it('HERO has every section in order', () => {
    const md = buildReportMarkdown(hero, info)
    const heads = ['# Greenline report: #0142', '## Verdict', '## Guardrails', '## Reruns', '## Evidence', '## Escalation:']
    const at = heads.map((h) => md.indexOf(h))
    expect(at.every((i) => i >= 0)).toBe(true)
    expect([...at].sort((a, b) => a - b)).toEqual(at)
    expect(md).toContain('# Greenline report: #0142 test_settlement_reconciles_at_eod')
    expect(md).toContain('- Case: #0142 · acme/ledger-core · case/0142-flaky-settlement')
    expect(md).toContain('FLAKY, 95% confidence')
    expect(md).toContain('protected_file: BLOCKED.')
    expect(md).toContain('no_creds: clear.')
    expect(md).toContain('diff_cap: not checked yet')
    expect(md).toContain('7 pass / 3 fail across 10 isolated reruns (PPFPPFPPFP)')
    expect(md).toContain('Outcome: escalated')
    expect(md).not.toContain('\r')
    expect(md.endsWith('\n')).toBe(true)
  })
  it('says LIVE or RECORDED', () => {
    expect(buildReportMarkdown(hero, info)).toContain('> LIVE run')
    expect(buildReportMarkdown({ ...hero, mode: 'demo' }, info)).toContain('> RECORDED: re-streamed real run')
  })
  it('without case info the title is just the id', () => {
    const md = buildReportMarkdown(hero, null)
    expect(md.split('\n')[0]).toBe('# Greenline report: #0142')
    expect(md).not.toContain('- Case:')
  })
  it('a run without a verdict', () => {
    const md = buildReportMarkdown(reduceAll(TIGHT_0128), null)
    expect(md).toContain('No verdict reached.')
    expect(md).toContain('Outcome: budget exhausted')
  })
  it('a PR run carries the url and the last green patch', () => {
    const md = buildReportMarkdown(reduceAll(PATCH_LOOP_0137), null)
    expect(md).toContain('## Draft PR:')
    expect(md).toContain('PR: https://example.test/pr/1 (dry-run)')
    expect(md).toContain('## Patch')
    expect(md).toContain('File: src/rollup.py (attempt 2, source model)')
    expect(md).toContain('```diff\n-a\n+c\n```')
  })
  it('an empty run still renders placeholders', () => {
    const md = buildReportMarkdown(EMPTY_STATE, null)
    expect(md).toContain('No reruns.')
    expect(md).toContain('No evidence recorded.')
  })
})
