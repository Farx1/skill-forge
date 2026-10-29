# playbook-forge

A Claude Code plugin. One command, `/playbook`, turns a recurring job into a playbook: a skill stored in its own folder, which Claude rereads on every run instead of you explaining the job again.

## What happens when you type /playbook

```
You:     /playbook new relance-factures
Claude:  Scope? (Personal / This project) Frequency? Output type? Was the job done in this session?
You:     Personal, weekly, message to send, no
Claude:  When does this job start, and how often? (Topics covered: 0/9)
You:     Every Monday, for invoices unpaid 7, 30 or 60 days after the due date.
Claude:  Which inputs do you need, and where exactly do you find them? (Topics covered: 1/9)
...
Claude:  Interview finished? (Yes, write the playbook / No, I have more to say)
You:     Yes, write the playbook
Claude:  Created ~/.claude/skills/relance-factures/SKILL.md, validate: 0 FAIL.
         What did I misunderstand? What did I forget to tell you?
```

The playbook is built in three layers, plus a loop:

1. Steps: an interview produces `SKILL.md` (trigger, inputs, ordered steps, decisions, edge cases).
2. Tools: scripts, `[placeholder]` templates, reference files and approved examples in `files/` and `examples/`, listed in `files/INDEX.md`.
3. Checks: a Definition of done with 5 to 10 checks, each with an inspectable proof and a failure condition, run before every delivery.
4. Loop: when a result is wrong, find the faulty layer, make the smallest lasting fix in that layer's file, date it in `notes.md`, rerun cold.

## Installation

Requirements: Claude Code, Python 3.9 or later. No other dependency.

From a local clone:

```
claude plugin marketplace add E:/claude-projects/playbook-forge
claude plugin install playbook-forge@playbook-forge
```

From GitHub:

```
claude plugin marketplace add Farx1/playbook-forge
claude plugin install playbook-forge@playbook-forge
```

From inside a Claude Code session:

```
/plugin marketplace add Farx1/playbook-forge
/plugin install playbook-forge@playbook-forge
```

Restart Claude Code if the new `skills` folder is not detected.

## Usage by mode

Type `/playbook` alone to get a menu, or give the mode and the playbook name.

| Command | Layer | What it does |
|---|---|---|
| `/playbook new relance-factures` | Steps | Interview, then writes SKILL.md |
| `/playbook save relance-factures` | Tools | Stores scripts, templates and approved results from the session |
| `/playbook checks relance-factures` | Checks | Writes the Definition of done and the verification protocol |
| `/playbook fix relance-factures` | Loop | Fixes the faulty layer, logs it in `notes.md`, reruns cold |
| `/playbook test relance-factures` | Loop | Cold run in a sandbox by the `playbook-runner` agent, nothing is sent or published |
| `/playbook audit relance-factures` | Loop | Monthly review: uncited files, duplicates, repeated errors |
| `/playbook dashboard` | All | Generates the HTML dashboard |
| `/playbook export relance-factures` | All | Zip for upload to claude.ai |
| `/playbook list` | All | Lists playbooks |

## The pbf.py script

The skill runs `scripts/pbf.py`. You can run it yourself from the repo folder:

```
python scripts/pbf.py doctor
python scripts/pbf.py list
python scripts/pbf.py list --json
python scripts/pbf.py scaffold relance-factures --scope perso
python scripts/pbf.py scaffold relance-factures --scope projet --root E:/claude-projects/playbook-forge
python scripts/pbf.py validate examples/relance-factures
python scripts/pbf.py index relance-factures --file echelle-relance.md --purpose "paliers J+7, J+30, J+60"
python scripts/pbf.py note relance-factures --layer checks --error "formule interdite non détectée" --fix "ajout d'un check de recherche des formules"
python scripts/pbf.py audit relance-factures
python scripts/pbf.py audit --all
python scripts/pbf.py dashboard
python scripts/pbf.py dashboard --out dashboard.html --no-open
python scripts/pbf.py export relance-factures
python scripts/pbf.py export relance-factures --out .
python scripts/pbf.py config --add-root E:/claude-projects/playbook-forge/examples
python scripts/pbf.py config --show
python scripts/pbf.py selftest
```

Exit codes: 0 ok, 1 at least one FAIL, 2 usage error. Run the test suite with:

```
python -m unittest discover -s tests -v
```

## Anatomy of a playbook

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
python scripts/pbf.py validate examples/relance-factures
```

Locations, chosen at creation:

- personal: `~/.claude/skills/relance-factures/` (or `CLAUDE_CONFIG_DIR` if set), available in every project;
- project: `.claude/skills/relance-factures/` at the git root, versioned with the project.

## Dashboard

`python scripts/pbf.py dashboard` writes a single self-contained HTML file (inline CSS and JS, no external resource) and opens it in your browser. It shows one card per playbook with the state of the three layers, the last run, a success-rate curve and alerts.

A sample generated from the demo playbook: [docs/dashboard-demo.html](docs/dashboard-demo.html).

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
claude plugin uninstall playbook-forge@playbook-forge
claude plugin marketplace remove playbook-forge
```

Your playbooks in `~/.claude/skills/` and `.claude/skills/` are not deleted.

## Credits

The method is inspired by a guide from the Distribb team on agent playbooks. Playbooks follow Anthropic's Agent Skills format.

## License

MIT, see [LICENSE](LICENSE).
