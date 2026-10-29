---
name: forge
description: Transforme un job récurrent en skill Claude Code relu à chaque exécution. Utilise ce skill dès que l'utilisateur parle de playbook, de skill à créer, de tâche récurrente, de job hebdo, de "transformer en skill", de "documenter ma façon de faire", de "garder ce script ou ce template", d'"ajouter des checks", de "corriger le skill", de "tester le skill" ou de "dashboard des skills". Turns a recurring job into a reusable skill with steps, tools and checks. Use it for skill, playbook, recurring task, weekly job, save this script or template, add checks, fix the skill, test the skill, skill dashboard.
argument-hint: "[new|save|checks|fix|test|audit|dashboard|export|list] [nom]"
allowed-tools:
  - 'Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/forge.py" *)'
  - 'Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/forge.py" *)'
  - 'Bash(py -3 "${CLAUDE_PLUGIN_ROOT}/scripts/forge.py" *)'
  - 'PowerShell(python "${CLAUDE_PLUGIN_ROOT}/scripts/forge.py" *)'
  - 'PowerShell(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/forge.py" *)'
  - 'PowerShell(py -3 "${CLAUDE_PLUGIN_ROOT}/scripts/forge.py" *)'
---

# /forge

Un skill = un dossier, en 3 couches (Étapes, Outils, Checks) plus une boucle de correction. Ce routeur choisit le mode, puis charge une seule référence.

## Commande du script

Lance toujours :

`python "${CLAUDE_PLUGIN_ROOT}/scripts/forge.py" <sous-commande>`

Si `python` n'existe pas, essaie `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/forge.py" <sous-commande>`, puis `py -3 "${CLAUDE_PLUGIN_ROOT}/scripts/forge.py" <sous-commande>`. Garde l'interpréteur qui a marché pour la suite. En cas d'erreur d'interpréteur, lance `doctor`.

## Choisir le mode

Prends la première source qui donne un mode :

1. `$ARGUMENTS` : le premier mot est le mode (`new`, `save`, `checks`, `fix`, `test`, `audit`, `dashboard`, `export`, `list`), le reste est le nom du skill.
2. L'intention visible dans la conversation (ex. "garde ce template" donne `save`, "le résultat est faux" donne `fix`).
3. Sinon le menu ci-dessous. Deux niveaux, 4 options maximum par question : AskUserQuestion refuse davantage.

Niveau 1, question « Que veux-tu faire ? » :
- Créer un skill : mode `new`.
- Améliorer un skill : niveau 2a.
- Tester ou auditer : niveau 2b.
- Voir le dashboard : mode `dashboard`.

Niveau 2a, question « Quelle amélioration ? » :
- Sauver un outil : mode `save`.
- Ajouter les checks : mode `checks`.
- Corriger une erreur : mode `fix`.

Niveau 2b, question « Quelle vérification ? » :
- Test à froid : mode `test`.
- Audit mensuel : mode `audit`.
- Exporter pour claude.ai : mode `export`.

## Choisir le skill

Les modes `save`, `checks`, `fix`, `test`, `audit` et `export` ont besoin d'un nom. S'il n'est pas dans `$ARGUMENTS` :

1. Lance `forge.py list --json`.
2. Pose une question AskUserQuestion « Quel skill ? » avec les 4 plus récents. L'option « Autre » permet de taper un nom.
3. Aucun skill trouvé : propose le mode `new`.

Le mode `new` n'a pas besoin de skill existant : le nom vient des arguments ou de la première étape de sa référence.

## Charger le mode

Lis uniquement le fichier du mode choisi, jamais les autres. Cela garde le contexte court et évite de mélanger des consignes :

- `new` : `${CLAUDE_SKILL_DIR}/references/new.md`
- `save` : `${CLAUDE_SKILL_DIR}/references/save.md`
- `checks` : `${CLAUDE_SKILL_DIR}/references/checks.md`
- `fix` : `${CLAUDE_SKILL_DIR}/references/fix.md`
- `test` : `${CLAUDE_SKILL_DIR}/references/test.md`
- `audit` : `${CLAUDE_SKILL_DIR}/references/audit.md`

Suis ensuite ce fichier à la lettre. Les modes suivants n'ont pas de fichier.

## Mode dashboard

1. Lance `forge.py dashboard` (ajoute `--no-open` si le navigateur ne doit pas s'ouvrir, `--out CHEMIN` pour choisir le fichier).
2. Résume en 3 lignes les actions prioritaires : alertes validate en FAIL, audit dû, erreurs répétées, fichiers non cités, secrets possibles.
3. Donne le chemin du HTML généré.

## Mode export

1. Lance `forge.py export <nom>` (`--out DOSSIER` pour choisir la destination). Le script refuse si le frontmatter contient des clés non portables.
2. Donne le chemin du zip.
3. Rappelle que sur claude.ai il faut remplacer l'ancien upload, jamais garder deux versions des mêmes instructions : deux versions se contredisent et Claude suit l'une ou l'autre au hasard.

## Mode list

Lance `forge.py list` et affiche le résultat tel quel. Ajoute `--json` seulement pour exploiter la sortie toi-même.

## Autres sous-commandes

`doctor` (diagnostic Python et racines), `config --show` ou `config --add-root CHEMIN` (racines supplémentaires de skills), `validate <nom|chemin>`, `scaffold`, `index`, `note`, `audit` : elles sont utilisées par les références, pas directement par le menu.

## Règles communes

- Réponds en français. Les fenêtres de questions aussi.
- Dis toujours quel mode tu as retenu et pourquoi, en une ligne, avant de commencer.
- N'écris jamais dans un skill sans que le mode choisi le demande.
