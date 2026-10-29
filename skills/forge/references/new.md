# Mode new : créer un skill (couche 1, étapes)

But : capter comment l'utilisateur fait vraiment le job, pour que Claude le refasse sans qu'il réexplique. Un skill écrit sur des suppositions reproduit les suppositions, pas le job. D'où l'interview avant toute écriture.

## 1. Cadrage

Pose une seule fenêtre AskUserQuestion, 4 questions :

- Portée : Perso / Ce projet.
- Fréquence : Quotidienne / Hebdomadaire / Mensuelle / À la demande.
- Type de résultat : Message à envoyer / Document ou rapport / Code / Données.
- « Le job a-t-il été fait dans cette session ? » : Oui, pars de la conversation / Non.

Le nom vient des arguments, sinon demande-le en texte. Normalise-le en kebab-case (minuscules, tirets, sans accents, 64 caractères max, jamais `synced`) : le nom est aussi le nom du dossier, et les outils le comparent tel quel.

## 2. Partir de la session

Si le job a été fait dans la session, extrais d'abord de la conversation ce qui répond déjà aux sujets de l'interview. Présente-le, fais-le confirmer ou corriger. Cela évite de reposer des questions dont la réponse est déjà là.

## 3. Interview

Pose des questions ouvertes, en texte, une seule à la fois. Attends la réponse avant la suivante : plusieurs questions d'un coup donnent des réponses courtes et superficielles.

Couvre au minimum ces 9 sujets :

1. Déclencheur et fréquence.
2. Chaque entrée et l'endroit exact où la trouver.
3. Les actions dans l'ordre où l'utilisateur les fait vraiment.
4. Chaque choix et comment il tranche.
5. Ce qu'il relit avant de considérer le job fini.
6. Les situations inhabituelles qui ont déjà posé problème.
7. Le niveau de voix ou de qualité attendu.
8. À quoi ressemble un mauvais résultat.
9. Les phrases exactes qu'il tape pour demander ce job.

Règles de conduite :
- Demande des exemples réels (un vrai message, un vrai fichier), pas des descriptions.
- Relance quand une réponse est vague ("ça dépend", "comme d'habitude"). Demande de quoi ça dépend.
- Une question qui paraît évidente cache souvent un choix fait sans y penser. Pose-la quand même, et dis-le à l'utilisateur.
- Affiche la progression après chaque réponse : « Sujets couverts : 4/9 ».

## 4. Feu vert

Quand les 9 sujets sont couverts, pose la fenêtre « Interview terminée ? » : Oui, écris le skill / Non, j'ai encore des choses à dire. N'écris aucun fichier avant « Oui » : un dossier créé trop tôt se remplit de réponses incomplètes.

## 5. Écriture

1. Lance `forge.py scaffold <nom> --scope perso|projet` (`--root CHEMIN` pour un autre emplacement). Il refuse si le dossier existe ou si le nom est invalide. S'il signale la création du dossier `skills` racine, note-le pour l'étape 7.
2. Écris `SKILL.md` dans le dossier créé, à partir de `${CLAUDE_SKILL_DIR}/assets/SKILL.template.md`. Garde l'ordre des sections et le texte fixe de `## Après chaque exécution` tel quel.
3. Rédige la `description` avec les phrases exactes de l'utilisateur (sujet 9) et une formulation ferme ("Utilise ce skill dès que..."), 1024 caractères max : c'est elle qui déclenche le skill.
4. Écris les étapes en langage courant, sans jargon, dans l'ordre réel (sujet 3). Chaque choix du sujet 4 devient une règle `Si X, alors Y` dans `## Décisions`.
5. Si les checks ne sont pas encore faits, mets une première Définition de terminé construite sur les sujets 5 et 8, marquée « à compléter avec /forge checks ».

## 6. Relecture

1. Lance `forge.py validate <nom>`. Corrige les FAIL.
2. Montre le fichier complet à l'utilisateur.
3. Demande en texte : « Qu'est-ce que j'ai mal compris ? » puis « Qu'est-ce que j'ai oublié de te dire ? ». Intègre les réponses dans SKILL.md.

## 7. Suite

Pose une fenêtre : Lancer le job maintenant / Ajouter les checks / Plus tard. Si `scaffold` a signalé la création du dossier `skills` racine, dis à l'utilisateur de redémarrer Claude Code : sans redémarrage, le nouveau dossier n'est pas surveillé et le skill n'est pas détecté.
