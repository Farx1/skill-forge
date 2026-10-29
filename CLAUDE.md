# playbook-forge

Plugin Claude Code: la commande `/playbook` transforme un job récurrent en skill rangé dans son dossier.

## Conventions

- Python 3.9+, bibliothèque standard uniquement. Aucune dépendance.
- Tous les fichiers en UTF-8, fins de ligne LF. Lecture et écriture avec `encoding="utf-8"`.
- Tests avant chaque commit : `python -m unittest discover -s tests -v`
- Textes des skills, fenêtres de questions et dashboard en français.
- Chaque SKILL.md fait moins de 500 lignes (routeur : 150 lignes maximum).
- README.md mis à jour dès qu'une commande ou une option de `scripts/pbf.py` change.
- Aucun tiret long (caractère U+2014), nulle part.
- Pas d'injection de commande `` !`...` `` dans les skills.
- Le playbook de démo `examples/relance-factures/` doit passer `python scripts/pbf.py validate examples/relance-factures` sans FAIL.
