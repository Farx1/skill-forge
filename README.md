# skill-forge

A Claude Code plugin. One command, `/forge`, turns a recurring job into a skill, stored in its own folder, which Claude rereads on every run instead of you explaining the job again.

## What happens when you type /forge

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

The skill is built in three layers, plus a loop:

1. Steps: an interview produces `SKILL.md` (trigger, inputs, ordered steps, decisions, edge cases).
2. Tools: scripts, `[placeholder]` templates, reference files and approved examples in `files/` and `examples/`, listed in `files/INDEX.md`.
3. Checks: a Definition of done with 5 to 10 checks, each with an inspectable proof and a failure condition, run before every delivery.
4. Loop: when a result is wrong, find the faulty layer, make the smallest lasting fix in that layer's file, date it in `notes.md`, rerun cold.

## Installation

Requirements: Claude Code, Python 3.9 or later. No other dependency.

From a local clone:

```
claude plugin marketplace add E:/claude-projects/skill-forge
claude plugin install skill-forge@skill-forge
```

From GitHub:

```
claude plugin marketplace add Farx1/skill-forge
claude plugin install skill-forge@skill-forge
```

From inside a Claude Code session:

```
/plugin marketplace add Farx1/skill-forge
/plugin install skill-forge@skill-forge
```

Restart Claude Code if the new `skills` folder is not detected.

## Usage by mode

Type `/forge` alone to get a menu, or give the mode and the skill name.

| Command | Layer | What it does |
|---|---|---|
| `/forge new relance-factures` | Steps | Interview, then writes SKILL.md |
| `/forge save relance-factures` | Tools | Stores scripts, templates and approved results from the session |
| `/forge checks relance-factures` | Checks | Writes the Definition of done and the verification protocol |
| `/forge fix relance-factures` | Loop | Fixes the faulty layer, logs it in `notes.md`, reruns cold |
| `/forge test relance-factures` | Loop | Cold run in a sandbox by the `skill-runner` agent, nothing is sent or published |
| `/forge audit relance-factures` | Loop | Monthly review: uncited files, duplicates, repeated errors |
| `/forge dashboard` | All | Generates the HTML dashboard |
| `/forge export relance-factures` | All | Zip for upload to claude.ai |
| `/forge list` | All | Lists skills |

## The forge.py script

The skill runs `scripts/forge.py`. You can run it yourself from the repo folder:

```
python scripts/forge.py doctor
python scripts/forge.py list
python scripts/forge.py list --json
python scripts/forge.py scaffold relance-factures --scope perso
python scripts/forge.py scaffold relance-factures --scope projet --root E:/claude-projects/skill-forge
python scripts/forge.py validate examples/relance-factures
python scripts/forge.py index relance-factures --file echelle-relance.md --purpose "paliers J+7, J+30, J+60"
python scripts/forge.py note relance-factures --layer checks --error "formule interdite non détectée" --fix "ajout d'un check de recherche des formules"
python scripts/forge.py audit relance-factures
python scripts/forge.py audit --all
python scripts/forge.py dashboard
python scripts/forge.py dashboard --out dashboard.html --no-open
python scripts/forge.py export relance-factures
python scripts/forge.py export relance-factures --out .
python scripts/forge.py config --add-root E:/claude-projects/skill-forge/examples
python scripts/forge.py config --show
python scripts/forge.py selftest
```

Exit codes: 0 ok, 1 at least one FAIL, 2 usage error. Run the test suite with:

```
python -m unittest discover -s tests -v
```

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

A complete demo is in `examples/relance-factures/`. Check it with:

```
python scripts/forge.py validate examples/relance-factures
```

Locations, chosen at creation:

- personal: `~/.claude/skills/relance-factures/` (or `CLAUDE_CONFIG_DIR` if set), available in every project;
- project: `.claude/skills/relance-factures/` at the git root, versioned with the project.

## Dashboard

`python scripts/forge.py dashboard` writes a single self-contained HTML file (inline CSS and JS, no external resource) and opens it in your browser. It shows one card per skill with the state of the three layers, the last run, a success-rate curve and alerts.

A sample generated from the demo skill: [docs/dashboard-demo.html](docs/dashboard-demo.html).

## Windows, macOS, Linux

The interpreter name differs by system. The skill tries `python`, then `python3`, then `py -3`.

- Windows: `python` or `py -3`
- macOS: `python3`
- Linux: `python3` (or `python` on some distributions)

Check which one works:

```
python --version
python3 --version
py -3 --version
```

Files are read and written as UTF-8 with LF line endings on every system.

## Uninstall

```
claude plugin uninstall skill-forge@skill-forge
claude plugin marketplace remove skill-forge
```

Your skills in `~/.claude/skills/` and `.claude/skills/` are not deleted.

## Credits

The method is inspired by a guide from the Distribb team on agent playbooks. Skills follow Anthropic's Agent Skills format.

## License

MIT, see [LICENSE](LICENSE).
