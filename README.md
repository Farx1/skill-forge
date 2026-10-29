# skill-forge

A Claude Code plugin that turns a recurring job into a skill: steps, tools and checks in one folder, reread by Claude on every run.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0-informational.svg)](.claude-plugin/plugin.json)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-orange.svg)](https://github.com/Farx1/skill-forge)
[![Python 3.9+ stdlib](https://img.shields.io/badge/python-3.9%2B%20stdlib%20only-3776AB.svg)](scripts/forge.py)

## Install

Inside Claude Code, run:

```
/plugin marketplace add Farx1/skill-forge
/plugin install skill-forge@skill-forge
```

Then type `/forge`. Restart Claude Code if the new `skills` folder is not detected.

<details>
<summary><strong>Prefer the terminal?</strong></summary>

```bash
claude plugin marketplace add Farx1/skill-forge
claude plugin install skill-forge@skill-forge
```

</details>

<details>
<summary><strong>Install from a local clone</strong></summary>

```bash
git clone https://github.com/Farx1/skill-forge.git
claude plugin marketplace add ./skill-forge
claude plugin install skill-forge@skill-forge
```

</details>

Requirements: Claude Code and Python 3.9 or later. No other dependency.

## What a session looks like

```
You:     /forge new relance-factures
Claude:  Scope? (Personal / This project) Frequency? Output type? Was the job done in this session?
You:     Personal, weekly, message to send, no
Claude:  When does this job start, and how often? (Topics covered: 0/9)
You:     Every Monday, for invoices unpaid 7, 30 or 60 days after the due date.
Claude:  Which inputs do you need, and where exactly do you find them? (Topics covered: 1/9)
...
Claude:  Interview finished? (Yes, write the skill / No, I have more to say)
You:     Yes, write the skill
Claude:  Created ~/.claude/skills/relance-factures/SKILL.md, validate: 0 FAIL.
         What did I misunderstand? What did I forget to tell you?
```

## How it works

Each skill is built in three layers, plus a correction loop:

1. **Steps**: an interview produces `SKILL.md` (trigger, inputs, ordered steps, decisions, edge cases).
2. **Tools**: scripts, `[placeholder]` templates, reference files and approved examples in `files/` and `examples/`, listed in `files/INDEX.md`.
3. **Checks**: a Definition of done with 5 to 10 checks. Each has an inspectable proof and a failure condition, and runs before every delivery.
4. **Loop**: when a result is wrong, find the faulty layer, make the smallest lasting fix in that layer's file, date it in `notes.md`, rerun cold.

## Commands

Type `/forge` alone to get a menu, or give the mode and the skill name.

| Command | Layer | What it does |
|---|---|---|
| `/forge new relance-factures` | Steps | Interview, then writes `SKILL.md` |
| `/forge save relance-factures` | Tools | Stores scripts, templates and approved results from the session |
| `/forge checks relance-factures` | Checks | Writes the Definition of done and the verification protocol |
| `/forge fix relance-factures` | Loop | Fixes the faulty layer, logs it in `notes.md`, reruns cold |
| `/forge test relance-factures` | Loop | Cold run in a sandbox by the `skill-runner` agent, nothing is sent or published |
| `/forge audit relance-factures` | Loop | Monthly review: uncited files, duplicates, repeated errors, skills unused for 60 days |
| `/forge dashboard` | All | Points you to `/skills-panel` and sums up the priority actions in 3 lines |
| `/forge export relance-factures` | All | Zip for upload to claude.ai |
| `/forge list` | All | Lists skills |

## Anatomy of a skill

```
relance-factures/
  SKILL.md          frontmatter (name, description, metadata) and 9 sections
  files/INDEX.md    one line per tool: name | usage | date
  files/            templates, reference files, scripts
  examples/         approved results, named by date and short label
  notes.md          dated fixes, most recent first
  runs.jsonl        one line per run, test or audit
```

`SKILL.md` sections, in order: Objectif, Quand l'utiliser, Entrées, Étapes, Décisions, Boîte à outils, Définition de terminé, Cas particuliers, Après chaque exécution.

Locations, chosen at creation:

- **Personal**: `~/.claude/skills/relance-factures/` (or `CLAUDE_CONFIG_DIR` if set), available in every project.
- **Project**: `.claude/skills/relance-factures/` at the git root, versioned with the project.

A complete demo skill lives in [`examples/relance-factures/`](examples/relance-factures). Check it with:

```bash
python scripts/forge.py validate examples/relance-factures
```

## Skills panel

Type this in Claude Code:

```
/skills-panel
```

A **Skills** pane opens beside the chat. It shows:

- 4 tiles: number of skills, runs in the last 30 days, check success rate, open alerts.
- One card per skill: scope, last run, state of the three layers (Steps, Tools, Checks), a success sparkline of the last 10 runs, number of fixes, uses in the last 30 days, and alerts (validate FAIL, audit due, failing check, repeated error, uncited file).
- Select a card to see its indexed files, its last 5 notes and the checks that fail most. Press `b` to go back, `r` to refresh.

The pane reads `python scripts/forge.py status --json` and refreshes itself when Claude writes or edits a file under a `skills` folder.

## Automatic skill detection

While you work, skill-forge watches which tools, file types, commands and dependencies come back turn after turn. Every 10 turns, if something was seen on at least 2 distinct turns, it asks Haiku whether a recurring approach is worth a skill. Existing skills and refused topics are never proposed again.

When it finds one, a band appears above the prompt with three buttons:

- **Créer le skill**: skill-forge runs `forge.py scaffold`, then a background `skill-writer` agent writes `SKILL.md` from what was observed, and skill-forge runs `forge.py validate` when it is done. When the approach only concerns some files, the skill gets a `paths` key (for example `**/*.tsx`) so it only triggers on them.
- **Plus tard**: hides the proposal for this session.
- **Jamais**: never proposes this topic again.

After a skill-forge skill runs, if your next messages look like a correction ("non", "faux", "il manque", "instead"), Haiku classifies it and the band offers **Intégrer**: a `skill-writer` agent applies the smallest fix in the faulty layer, then skill-forge logs it with `forge.py note` and runs `forge.py validate`. **Ignorer** dismisses it.

Nothing is written without a click. The `skill-writer` agent has no shell: it can read files, and skill-forge refuses any write it attempts outside the skill folder. What you typed and what Haiku answered reach it as data it is told never to follow.

Secrets are masked before anything is stored or sent to a model: values after `password`, `token`, `secret`, `api_key` or `authorization`, `Bearer` tokens, JWTs, keys starting with `sk-`, `ghp_`, `gho_`, `AKIA` or `xox`, and any run of 32 or more token characters.

Commands:

```
/skill-watch
/skill-watch now
/skill-watch on
/skill-watch off
```

`/skill-watch` shows the status (signals collected, turns until the next analysis, refused topics, pending proposal). `now` runs an analysis immediately, `off` stops the detection and closes any pending band, `on` turns it back on.

## The forge.py CLI

The skill drives `scripts/forge.py`. You can run it yourself from the repo folder:

```bash
python scripts/forge.py doctor
python scripts/forge.py list
python scripts/forge.py list --json
python scripts/forge.py scaffold relance-factures --scope perso
python scripts/forge.py scaffold relance-factures --scope projet --root .claude/skills
python scripts/forge.py validate examples/relance-factures
python scripts/forge.py validate examples/relance-factures --json
python scripts/forge.py index relance-factures --file echelle-relance.md --purpose "paliers J+7, J+30, J+60"
python scripts/forge.py note relance-factures --layer checks --error "formule interdite non détectée" --fix "ajout d'un check de recherche des formules"
python scripts/forge.py audit relance-factures
python scripts/forge.py audit --all
python scripts/forge.py status
python scripts/forge.py status --json
python scripts/forge.py export relance-factures
python scripts/forge.py export relance-factures --out .
python scripts/forge.py config --add-root examples
python scripts/forge.py config --show
python scripts/forge.py selftest
```

| Subcommand | Purpose | Flags |
|---|---|---|
| `doctor` | Checks the environment | none |
| `list` | Lists skills | `--json` |
| `scaffold` | Creates an empty skill folder | `--scope perso\|projet`, `--root` |
| `validate` | Checks a skill folder | `--json` |
| `index` | Adds a line to `files/INDEX.md` | `--file`, `--purpose`, `--date` |
| `note` | Logs a dated fix in `notes.md` | `--layer instructions\|outils\|checks`, `--error`, `--fix`, `--date` |
| `audit` | Reviews one skill or all of them | `--all`, `--json` |
| `status` | Prints a summary of all skills, or with `--json` the data of the Skills panel | `--json` |
| `export` | Zips a skill for claude.ai (drops `runs.jsonl` and the Claude Code only `paths` key) | `--out` |
| `config` | Adds or shows skill roots | `--add-root`, `--show` |
| `selftest` | Runs the built-in self-test | none |

Usage data is optional: if `logs/skill-usage.tsv` exists in the Claude config folder (`~/.claude`, or `CLAUDE_CONFIG_DIR` if set), with tab-separated lines of ISO date, skill name and working directory (`plugin:skill` names are matched on the part after the last colon), `status` and the Skills panel report `uses_30d` and `last_used`, and `audit` flags skills unused for 60 days.

Exit codes: `0` ok, `1` at least one FAIL, `2` usage error.

## Windows, macOS, Linux

The interpreter name differs by system. The skill tries `python`, then `python3`, then `py -3`.

- Windows: `python` or `py -3`
- macOS: `python3`
- Linux: `python3` (or `python` on some distributions)

Check which one works:

```bash
python --version
python3 --version
py -3 --version
```

Files are read and written as UTF-8 with LF line endings on every system.

## Uninstall

```bash
claude plugin uninstall skill-forge@skill-forge
claude plugin marketplace remove skill-forge
```

Your skills in `~/.claude/skills/` and `.claude/skills/` are not deleted.

## Development

Run the test suites from the repo folder:

```bash
python -m unittest discover -s tests -v
python scripts/forge.py selftest
claude plugin validate .
claude plugin test .
```

`claude plugin test .` runs the tests of the panel and detection modules in `hooks/`.

## Credits

The method is inspired by a guide from the Distribb team on agent playbooks. Skills follow Anthropic's [Agent Skills](https://github.com/anthropics/skills) format.

## License

MIT, see [LICENSE](LICENSE).
