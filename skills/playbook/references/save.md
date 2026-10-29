# Mode save : garder des outils (couche 2)

But : qu'un script, un template ou un exemple approuvé ne soit plus recréé de tête à chaque exécution. Un outil recréé varie d'une fois à l'autre, un outil stocké reste identique.

## 1. Repérer

Parcours la session et liste les artefacts réutilisables : script, template, email, checklist, fichier de référence, résultat que l'utilisateur a approuvé. Pose une question AskUserQuestion à choix multiples, par lots de 4 : lesquels garder.

## 2. Exclure

Écarte, même si l'utilisateur les a cochés sans y penser :
- les résultats à usage unique ;
- les brouillons non approuvés ;
- tout ce qui contient un mot de passe, un token ou une clé d'API. Un secret stocké dans un playbook est copié, exporté et versionné avec lui. Dis ce que tu as écarté et pourquoi.

## 3. Ranger chaque artefact gardé

1. Place-le dans `files/` avec un nom qui dit son rôle (`relance-template.md`), sans date ni numéro de version : le nom reste valable quand le contenu évolue.
2. Remplace les détails de l'utilisateur par des `[placeholders]` et ajoute dessous un exemple rempli. Pour un script, utilise des paramètres ou un fichier de config plutôt que des crochets.
3. Modifie l'étape concernée de `SKILL.md` pour citer le fichier et dire quand l'utiliser ou non. Un fichier non cité n'est jamais ouvert par Claude, et `validate` le signale. Mets aussi à jour `## Boîte à outils`.
4. Inscris-le : `pbf.py index <nom> --file <fichier> --purpose "<usage>"`.
5. Un résultat final approuvé va dans `examples/AAAA-MM-JJ-<court>.md`.

## 4. Vérifier

Lance `pbf.py validate <nom>` et corrige les FAIL (fichier non indexé, non cité, nom daté, secret).

Puis relance le job à froid avec l'agent `playbook-runner` (`playbook-forge:playbook-runner`), selon `${CLAUDE_SKILL_DIR}/references/test.md`. Rapporte :
- les fichiers stockés utilisés ;
- les éléments recréés ;
- pour chaque élément recréé, s'il vaut la peine d'en garder une copie et quel fichier ajouter ensuite.

Si l'agent a recréé un outil qui existait déjà, l'étape ne le cite pas assez clairement : corrige l'étape.
