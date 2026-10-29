# Mode fix : corriger une erreur (boucle)

But : qu'une erreur ne se reproduise pas. Corriger seulement le résultat fait gagner une fois, corriger la couche fautive fait gagner à chaque exécution.

## 1. Récupérer l'erreur

Prends ce qui était faux dans les arguments. Sinon demande-le en texte : ce qui était attendu, ce qui est sorti.

## 2. Désigner la couche fautive

Explique en deux phrases laquelle des trois couches a failli :
- instructions : étape absente, mauvais ordre, règle de décision non écrite ;
- outils : fichier recréé alors qu'il existait, ou fichier stocké faux ou périmé ;
- checks : aucun check n'aurait attrapé l'erreur.

## 3. Corriger au plus petit

Fais la plus petite modification durable, dans le fichier de cette couche seulement (`SKILL.md`, un fichier de `files/`, ou la section checks). Ne réécris pas le reste : une réécriture large introduit de nouvelles erreurs et efface ce qui marchait.

## 4. Bloquer la récidive

Lis `notes.md`. S'il contient déjà une erreur similaire, la correction précédente était trop vague. Écris une règle précise (condition, action, valeur) qui bloque la récidive. Jamais un simple « faire attention », qui ne change aucun comportement.

## 5. Dater et rejouer

1. Lance `pbf.py note <nom> --layer instructions|outils|checks --error "<erreur>" --fix "<correction>"`. Le script écrit la ligne datée, la plus récente en haut.
2. Relance le job à froid avec l'agent `playbook-runner` (`playbook-forge:playbook-runner`), selon `${CLAUDE_SKILL_DIR}/references/test.md`, sur les mêmes entrées que l'erreur.
3. Montre l'ancien et le nouveau résultat côte à côte.
4. Si l'erreur persiste, la couche désignée était la mauvaise : recommence à l'étape 2.
