import { describe, expect, it } from 'vitest'
import { keyAction, type KeyContext, type KeyEventLike } from './useKeyboard'

const IDS = ['0142', '0144', '0139', '0131', '0137', '0128']
const ctx = (over: Partial<KeyContext> = {}): KeyContext => ({
  caseIds: IDS, selectedId: '0142', status: 'idle', reachable: true, hasReport: false,
  selectedHasDemoRun: true, mode: 'live', scoreboardOpen: false, debugOpen: false, ...over,
})
const ev = (key: string, over: Partial<KeyEventLike> = {}): KeyEventLike => ({
  key, code: `Key${key.toUpperCase()}`, ctrlKey: false, metaKey: false, altKey: false, repeat: false, target: null, ...over,
})
const act = (key: string, c: Partial<KeyContext> = {}, e: Partial<KeyEventLike> = {}) => keyAction(ev(key, e), ctx(c))

describe('keyAction', () => {
  it('digits select cases in the fixed demo order', () => {
    expect(act('1')).toEqual({ name: 'selectCase', caseId: '0142' })
    expect(act('2')).toEqual({ name: 'selectCase', caseId: '0144' })
    expect(act('6')).toEqual({ name: 'selectCase', caseId: '0128' })
  })
  it('a case the backend does not list is ignored; digits ignored while a run is going', () => {
    expect(act('3', { caseIds: ['0142'] }).name).toBe('none')
    expect(act('1', { status: 'streaming' }).name).toBe('none')
    expect(act('1', { status: 'starting' }).name).toBe('none')
  })
  it('Enter and R run only when idle, online and a case is selected', () => {
    expect(act('Enter').name).toBe('run')
    expect(act('r').name).toBe('run')
    expect(act('R').name).toBe('run')
    expect(act('Enter', { reachable: false }).name).toBe('none')
    expect(act('Enter', { selectedId: null }).name).toBe('none')
    expect(act('Enter', { status: 'starting' }).name).toBe('none')
    expect(act('r', { status: 'streaming' }).name).toBe('none')
    expect(act('Enter', { reachable: null }).name).toBe('run')
  })
  it('T toggles the budget, D toggles the mode (not into a missing recording)', () => {
    expect(act('t').name).toBe('toggleBudget')
    expect(act('T').name).toBe('toggleBudget')
    expect(act('d').name).toBe('toggleMode')
    expect(act('d', { mode: 'live', selectedHasDemoRun: false }).name).toBe('none')
    expect(act('d', { mode: 'demo', selectedHasDemoRun: false }).name).toBe('toggleMode')
    expect(act('t', { status: 'streaming' }).name).toBe('none')
    expect(act('d', { status: 'streaming' }).name).toBe('none')
  })
  it('S toggles the scoreboard', () => {
    expect(act('s').name).toBe('toggleScoreboard')
  })
  it('L toggles the theme, even mid-run, but not while typing or with a modifier', () => {
    expect(act('l').name).toBe('toggleTheme')
    expect(act('L').name).toBe('toggleTheme')
    expect(act('l', { status: 'streaming' }).name).toBe('toggleTheme')
    expect(act('l', {}, { target: { tagName: 'INPUT' } }).name).toBe('none')
    expect(act('l', {}, { ctrlKey: true }).name).toBe('none')
  })
  it('E downloads only when there is a finished report', () => {
    expect(act('e').name).toBe('none')
    expect(act('e', { hasReport: true }).name).toBe('download')
  })
  it('Escape and Backquote', () => {
    expect(act('Escape').name).toBe('escape')
    expect(act('`', {}, { code: 'Backquote' }).name).toBe('toggleDebug')
  })
  it('modifiers, repeats and typing targets are ignored', () => {
    expect(act('1', {}, { ctrlKey: true }).name).toBe('none')
    expect(act('1', {}, { metaKey: true }).name).toBe('none')
    expect(act('1', {}, { altKey: true }).name).toBe('none')
    expect(act('Enter', {}, { repeat: true }).name).toBe('none')
    expect(act('1', {}, { target: { tagName: 'INPUT' } }).name).toBe('none')
    expect(act('1', {}, { target: { tagName: 'textarea' } }).name).toBe('none')
    expect(act('1', {}, { target: { tagName: 'DIV', isContentEditable: true } }).name).toBe('none')
    expect(act('1', {}, { target: { tagName: 'BUTTON' } }).name).toBe('selectCase')
  })
  it('unknown keys do nothing', () => {
    expect(act('x').name).toBe('none')
    expect(act('7').name).toBe('none')
  })
})
