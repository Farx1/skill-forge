import { expect, test } from 'claude-code/testing'

import { plural, shortAlert, shortDate, spark } from './panel'

const PANE = {
  plugin: 'skill-forge',
  component: 'Pane',
  requestId: 'skill-forge',
  props: {
    title: 'Skills',
    isFocused: false,
    bodyColumns: 80,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 30 },
    view: {},
  },
} as const

const DATA = {
  generated: '2026-10-29',
  stats: { skills: 1, runs30: 3, rate: 80, alerts: 1 },
  skills: [
    {
      name: 'relance-factures', scope: 'perso', path: '/s/relance-factures',
      layers: { 'Étapes': 'fait', Outils: 'partiel', Checks: 'à faire' },
      last_run: '2026-10-20', spark: [0, 0.5, 1], notes_count: 2,
      alerts: ['audit dû'], index: [['a.md', 'modèle', '2026-01-01']],
      notes: [{ date: '2026-10-01', layer: 'outils', error: 'oubli', fix: 'ajout' }],
      top_failing: [['check X', 3]], uses_30d: 12, last_used: '2026-10-28',
    },
  ],
}

const RUN = {
  command: 'skills-panel',
  args: '',
  origin: { kind: 'composer' },
  presentation: { isFullscreen: true, columns: 120 },
} as const

const ran = (stdout: string, exitCode = 0) => ({
  value: { exitCode, stdout, stderr: exitCode ? 'boom' : '', isStdoutTruncated: false, isStderrTruncated: false },
})

test('sparkline', () => {
  expect(spark([0, 0.5, 1])).toBe('▁▅█')
  expect(plural(1, 'alerte', 'alertes')).toBe('1 alerte')
  expect(plural(2, 'alerte', 'alertes')).toBe('2 alertes')
  expect(shortDate('2026-10-20')).toBe('20 oct.')
  expect(shortAlert('audit dû : dernier repère 2026-09-15 (44 jours)')).toBe('audit dû depuis 44 jours')
})

test('le panneau liste un skill et ouvre son détail', async ($, on) => {
  on('command.register', () => ({ value: { command: 'skills-panel' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  const argv: string[][] = []
  on('process.run', (_, e) => (argv.push([...e.argv]), ran(JSON.stringify(DATA))))

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  await $.command.run(RUN)
  // forge.py est pris dans le plugin installé, pas dans .claude-plugin/.
  expect(argv[0]?.[1]).toMatch(/^(?!.*\.claude-plugin).*[\\/]scripts[\\/]forge\.py$/)

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Button', key: '/s/relance-factures' }))?.text).toMatch(/relance-factures/)
    await ui.unmount()
  }

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /12 utilisations \/ 30 j/ })).toBeDefined()
  await ui.press({ key: '/s/relance-factures' })
  expect(await ui.find({ type: 'Text', text: /check X/ })).toBeDefined()
  await ui.unmount()
})

test("une erreur de process s'affiche sans crash", async ($, on) => {
  on('command.register', () => ({ value: { command: 'skills-panel' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('process.run', () => ran('', 1))

  await $.command.run(RUN)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /Erreur/ })).toBeDefined()
  await ui.unmount()
})
