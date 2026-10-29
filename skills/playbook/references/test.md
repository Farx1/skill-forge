# Mode test : exécution à froid

But : savoir si le playbook marche sans l'historique de la conversation. Un playbook testé dans la session qui l'a écrit réussit grâce au contexte, pas grâce au fichier. L'agent `playbook-runner` part de zéro et ne lit que ce que SKILL.md cite.

## 1. Préparer

1. Trouve le chemin du playbook avec `pbf.py list --json`.
2. Prends les entrées fournies par l'utilisateur, sinon construis des entrées de démonstration réalistes et dis-le.
3. Calcule le dossier bac à sable : `<config>/playbook-forge/sandbox/<nom>/<date>/`, avec `<config>` = `CLAUDE_CONFIG_DIR` s'il est défini, sinon `~/.claude`, et `<date>` = AAAA-MM-JJ.

## 2. Lancer l'agent

Lance l'agent `playbook-runner` (nom complet `playbook-forge:playbook-runner`). Transmets-lui le chemin du playbook, les entrées et le dossier bac à sable. Il n'a pas la conversation : tout ce dont il a besoin doit être dans ce message.

## 3. Règles du bac à sable

Rappelle-les à l'agent, car un test ne doit jamais avoir d'effet réel :
- aucun envoi d'email ou de message ;
- aucune publication ;
- aucun push ;
- aucun paiement ;
- aucune écriture hors de `<config>/playbook-forge/sandbox/<nom>/<date>/`.

Si une étape exige l'une de ces actions, l'agent la simule dans le bac à sable (fichier de sortie) et le signale.

## 4. Rapport

Présente le rapport de l'agent :
- fichiers stockés utilisés ;
- éléments recréés ;
- résultat des checks (pass/fail et preuve) ;
- ce qui n'a pas pu être vérifié.

Un élément recréé alors qu'un fichier existait indique une étape qui ne le cite pas. Un check non vérifiable indique une preuve inaccessible : propose `/playbook fix`.

## 5. Consigner

Ajoute à `runs.jsonl` une ligne de type `test` :

`{"type":"test","date":"AAAA-MM-JJ","passed":5,"failed":0,"unverified":1,"failed_checks":[],"note":"..."}`

`failed_checks` contient les checks en échec. `audit` s'en sert pour repérer ceux qui échouent sur plusieurs runs.
