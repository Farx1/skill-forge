import { atom, read, update } from 'claude-code'
import type { Args, EngineInterface, Register } from 'claude-code'

import type { SkillForgeSkill, SkillForgeStatus } from '../types'

const PANE = 'skill-forge'
const TITLE = 'Skills'
const PYTHONS = [['python'], ['py', '-3'], ['python3']]

const status = atom(
  { plugin: 'skill-forge', key: 'status' } as const,
  {} as { data?: SkillForgeStatus; error?: string },
  { shape: 'status-1' },
)
const selected = atom({ plugin: 'skill-forge', key: 'selected' } as const, '')

const BARS = '▁▂▃▄▅▆▇█'
const LAYER_COLOR: Record<string, string> = { fait: 'success', partiel: 'warning' }
const NOTE_COLOR: Record<string, string> = { instructions: 'suggestion', outils: 'permission', checks: 'warning' }
const MONTHS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']
// Messages de forge.py (audit_pb, validate_pb) raccourcis pour une ligne de carte.
const SHORT: [RegExp, string][] = [
  [/^audit dû : .*\((\d+) jours\)$/, 'audit dû depuis $1 jours'],
  [/^check en échec dans (\d+) des 5 derniers runs : (.*)$/, '$2 échoue ($1/5 runs)'],
  [/^erreur répétée \([^)]*\) : (.*?) ;.*$/, 'erreur répétée : $1'],
  [/^fichier non cité dans SKILL\.md : /, 'non cité : '],
  [/^validate : /, ''],
]

export const spark = (values: number[]) =>
  values.map(v => BARS[Math.round(Math.max(0, Math.min(1, v)) * (BARS.length - 1))]).join('')
export const rateColor = (v: number) => (v >= 0.9 ? 'success' : v >= 0.6 ? 'warning' : 'error')
export const plural = (n: number, one: string, many: string) => `${n} ${n > 1 ? many : one}`
export const shortAlert = (a: string) => SHORT.reduce((s, [re, to]) => s.replace(re, to), a)
export const shortDate = (d: string) => {
  const [, m, day] = d.split('-')
  return m && day ? `${Number(day)} ${MONTHS[Number(m) - 1] ?? m}` : d
}

// Un seul forge.py à la fois, et au plus un rafraîchissement en attente après des écritures.
let refreshing = false
let queued = false

async function refresh($: EngineInterface) {
  if (refreshing) return
  refreshing = true
  try {
    await runStatus($)
  } finally {
    refreshing = false
  }
}

async function runStatus($: EngineInterface) {
  let error = 'aucun interpréteur Python trouvé'
  for (const py of PYTHONS) {
    try {
      const r = await $.process.run([...py, `${$.plugin.root}/scripts/forge.py`, 'status', '--json'], { timeoutMs: 60_000 })
      if (r.exitCode === 0) {
        const data = JSON.parse(r.stdout) as SkillForgeStatus
        await update($, status, () => ({ data }))
        return
      }
      error = `${py.join(' ')} a échoué (code ${r.exitCode}) : ${(r.stderr || r.stdout).trim().slice(0, 400)}`
    } catch (err) {
      error = `${py.join(' ')} : ${String(err).slice(0, 400)}`
    }
  }
  await update($, status, old => ({ ...old, error }))
}

// Appelés par register.tsx : un seul hook session.start et tool.call sans matcher par plugin.
export async function panelStart($: EngineInterface) {
  await $.command.register({ name: 'skills-panel', description: 'Ouvre le panneau Skills de skill-forge' })
}

export async function panelAfterTool($: EngineInterface, e: Args<'tool.call'>) {
  const input = e as { file_path?: string; command?: string }
  if (queued || !['Write', 'Edit', 'Bash'].includes(String(e.tool)) || !(input.file_path ?? input.command ?? '').includes('skills')) return
  if (!(await $.ui.panes()).some(p => p.id === PANE && p.isPlaced)) return
  queued = true
  $.clock.after(2_000, () => {
    queued = false
    void refresh($).catch(() => undefined)
  })
}

export const register: Register = on => {
  on('command.run', { command: 'skills-panel' }, async $ => {
    await $.ui.open({ id: PANE, title: TITLE })
    await refresh($)
    return { text: 'Panneau Skills ouvert.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const { data, error } = await read($, status)
    const pick = await read($, selected)

    const tile = (value: string, label: string, color = 'text') => (
      <Box flexDirection="column" borderStyle="round" borderColor="inactive" paddingX={1}>
        <Text bold color={color}>{value}</Text>
        <Text dimColor>{label}</Text>
      </Box>
    )

    const detail = (p: SkillForgeSkill) => {
      const w = Math.max(0, ...p.index.map(r => (r[0] ?? '').length))
      return (
        <Box flexDirection="column" marginTop={1}>
          <Text dimColor>Fichiers</Text>
          {p.index.length
            ? p.index.map(([f = '', use = '', d = '']) => <Text>  {f.padEnd(w)}  {use} <Text dimColor>{shortDate(d)}</Text></Text>)
            : <Text dimColor>  aucun fichier indexé</Text>}
          <Text dimColor>Dernières notes</Text>
          {p.notes.length
            ? p.notes.map(n => (
                <Text>  <Text dimColor>{shortDate(n.date).padEnd(8)}</Text> <Text color={NOTE_COLOR[n.layer] ?? 'text'}>{n.layer.padEnd(12)}</Text> {n.error} : {n.fix}</Text>
              ))
            : <Text dimColor>  aucune note</Text>}
          <Text dimColor>Checks qui échouent</Text>
          {p.top_failing.length
            ? p.top_failing.map(([c, n]) => <Text>  <Text color="error">{String(n).padStart(3)} fois</Text>  {c}</Text>)
            : <Text dimColor>  aucun check en échec</Text>}
          <Box marginTop={1}>
            <Button key="back" hotkey="b" onPress={() => update($, selected, () => '')}>← Retour</Button>
          </Box>
        </Box>
      )
    }

    const card = (p: SkillForgeSkill) => {
      const isOpen = p.path === pick
      const rate = p.spark.length ? p.spark.reduce((a, b) => a + b, 0) / p.spark.length : undefined
      return (
        <Box
          flexDirection="column"
          borderStyle="round"
          borderColor={isOpen ? 'suggestion' : p.alerts.length ? 'warning' : 'inactive'}
          paddingX={1}
        >
          <Box flexDirection="row" justifyContent="space-between" flexWrap="wrap" columnGap={1}>
            <Button key={p.path} plain onPress={() => update($, selected, old => (old === p.path ? '' : p.path))}>
              <Text bold>{p.name}</Text> <Text dimColor>{p.scope}</Text>
            </Button>
            <Text dimColor>{p.last_run ? `dernier run ${shortDate(p.last_run)}` : 'aucun run'}</Text>
          </Box>
          <Box flexDirection="row" flexWrap="wrap" columnGap={2}>
            {Object.entries(p.layers).map(([k, v]) => (
              <Text><Text color={LAYER_COLOR[v] ?? 'inactive'}>●</Text> {k}</Text>
            ))}
          </Box>
          <Text>
            <Text dimColor>Réussite </Text>
            {p.spark.length
              ? p.spark.map(v => <Text color={rateColor(v)}>{spark([v])}</Text>)
              : <Text dimColor>aucun run</Text>}
            {rate !== undefined && <Text bold color={rateColor(rate)}> {Math.round(rate * 100)} %</Text>}
            <Text dimColor> · {plural(p.notes_count, 'correction', 'corrections')}</Text>
            {typeof p.uses_30d === 'number' && <Text dimColor> · {plural(p.uses_30d, 'utilisation', 'utilisations')} / 30 j</Text>}
          </Text>
          {p.alerts.map(a => <Text color="warning">⚠ {shortAlert(a)}</Text>)}
          {isOpen && detail(p)}
        </Box>
      )
    }

    const s = data?.stats
    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="row" justifyContent="space-between">
          <Text bold>Skills</Text>
          <Button key="refresh" hotkey="r" variant="primary" onPress={() => refresh($)}>Rafraîchir</Button>
        </Box>
        {s && (
          <Box flexDirection="row" flexWrap="wrap" columnGap={1}>
            {tile(String(s.skills), s.skills > 1 ? 'skills' : 'skill')}
            {tile(String(s.runs30), `${s.runs30 > 1 ? 'runs' : 'run'} / 30 j`)}
            {tile(s.rate === null ? 'n/a' : `${s.rate} %`, 'checks', s.rate === null ? 'inactive' : rateColor(s.rate / 100))}
            {tile(String(s.alerts), s.alerts > 1 ? 'alertes' : 'alerte', s.alerts ? 'error' : 'success')}
          </Box>
        )}
        {error && (
          <Box borderStyle="round" borderColor="error" paddingX={1}>
            <Text color="error">Erreur : {error}</Text>
          </Box>
        )}
        {!data && !error && <Text dimColor>Chargement...</Text>}
        {data?.skills.length === 0 && (
          <Box justifyContent="center">
            <Text dimColor>Aucun skill. Tape /forge new pour en créer un.</Text>
          </Box>
        )}
        {data?.skills.map(card)}
      </Box>
    )
  })
}
