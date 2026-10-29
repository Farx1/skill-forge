export type SkillForgeSkill = {
  name: string
  scope: string
  path: string
  layers: Record<string, string>
  last_run: string
  spark: number[]
  notes_count: number
  alerts: string[]
  index: string[][]
  notes: { date: string; layer: string; error: string; fix: string }[]
  top_failing: [string, number][]
  uses_30d?: number | null
  last_used?: string
}

export type SkillForgeStatus = {
  generated: string
  skills: SkillForgeSkill[]
  stats: { skills: number; runs30: number; rate: number | null; alerts: number }
}

// Signal: [nombre de tours distincts où il a été vu, dernier tour vu].
export type SkillWatchSeen = Record<string, [number, number]>

export type SkillWatchSignals = {
  turn: number
  sinceLast: number
  fresh: boolean
  cwd: string
  tools: SkillWatchSeen
  exts: SkillWatchSeen
  cmds: SkillWatchSeen
  deps: string[]
  prompts: string[]
}

export type SkillWatchOffer =
  | { kind: 'new'; name: string; title: string; why: string; scope: 'perso' | 'projet'; evidence: string[]; paths: string[] }
  | { kind: 'fix'; skill: string; dir: string; layer: string; error: string; fix: string }

// Sous-agent skill-writer en cours : dossier qu'il peut écrire (root : chemin réel), note à ajouter après.
export type SkillWatchJob = {
  done: string
  dir: string
  root: string
  note?: { layer: string; error: string; fix: string }
}

declare module 'claude-code' {
  interface PluginState {
    'skill-forge': {
      // panneau Skills (hooks/panel.tsx)
      status: Shaped<{ data?: SkillForgeStatus; error?: string }>
      selected: string
      // détection d'approches récurrentes (hooks/watch.tsx)
      sig: Shaped<SkillWatchSignals>
      offer: Shaped<SkillWatchOffer | null>
      hidden: string[]
      watch: { skill: string; dir: string; left: number } | null
      jobs: Shaped<Record<string, SkillWatchJob>>
    }
  }
}
