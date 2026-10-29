# Mode audit : revue mensuelle

But : empêcher qu'un skill s'encombre ou dérive. Les fichiers non cités, les doublons et les erreurs répétées s'accumulent sans bruit.

## 1. Lancer

Lance `forge.py audit <nom>`, ou `forge.py audit --all` pour tous les skills (`--json` pour exploiter la sortie). Le script détecte :
- fichiers non cités ;
- doublons probables ;
- erreurs répétées dans `notes.md` (même couche et texte proche, ou même numéro d'étape, 2 fois ou plus) ;
- dernier audit vieux de plus de 30 jours ;
- checks qui échouent dans plusieurs des 5 derniers runs ;
- skill jamais utilisé depuis 60 jours (journal `logs/skill-usage.tsv` du dossier de config présent, skill créé il y a plus de 60 jours, 0 usage sur 60 jours).

## 2. Une question par constat

Pour chaque constat, pose une question AskUserQuestion : Supprimer / Garder / Fusionner, selon ce qui s'applique (fusionner n'existe que pour les doublons et les skills jamais utilisés, à fusionner dans un skill voisin). Ne supprime jamais rien sans réponse : un fichier qui paraît mort peut servir à un cas rare. Après « Supprimer » ou « Fusionner », mets à jour `files/INDEX.md` et les étapes de `SKILL.md` qui le citaient, puis lance `forge.py validate <nom>`.

## 3. Erreurs répétées

Une erreur répétée dans `notes.md` prouve qu'une règle écrite ne suffit pas. Propose un script ou un outil dédié qui rend l'erreur impossible, et rédige-le avec `${CLAUDE_SKILL_DIR}/references/save.md` si l'utilisateur accepte.

## 4. Déclenchement

Si l'utilisateur dit que le skill se déclenche mal (jamais, ou à tort), propose une nouvelle `description` construite avec ses phrases exactes. Signale le plugin officiel skill-creator pour mesurer le déclenchement :

`/plugin install skill-creator@claude-plugins-official`

## 5. Consigner

Ajoute à `runs.jsonl` une ligne de type `audit` :

`{"type":"audit","date":"AAAA-MM-JJ","passed":0,"failed":0,"unverified":0,"failed_checks":[],"note":"constats traités"}`

Cette ligne remet à zéro l'alerte « audit dû ».
