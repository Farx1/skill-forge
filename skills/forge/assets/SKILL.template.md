---
name: [nom]
description: "[Ce que fait le skill, en une phrase. Utilise ce skill dès que je dis « [phrase exacte 1] » ou « [phrase exacte 2] ».]"
metadata:
  skill-forge: "1"
  created: "[AAAA-MM-JJ]"
---

# [Titre du skill]

## Objectif

[Une phrase : ce que le job produit et pour qui.]

## Quand l'utiliser

[Déclencheur, fréquence, et cas où ce skill ne s'applique pas.]

## Entrées

- [Entrée 1] : [endroit exact où la trouver]
- [Entrée 2] : [endroit exact où la trouver]

## Étapes

1. [Première action, dans l'ordre réel.]
2. [Deuxième action.]
3. [Troisième action. Citer le fichier de `files/` utilisé, s'il y en a un.]

## Décisions

- Si [X], alors [Y].

## Boîte à outils

| Fichier | Usage | Quand ne pas l'utiliser |
|---------|-------|-------------------------|
| [fichier] | [à quoi il sert] | [cas où il ne convient pas] |

## Définition de terminé

[À compléter avec /forge checks. Chaque check suit le format `- [ ] vérification | Preuve : type | Échec si : condition`, 5 à 10 checks.]

## Cas particuliers

- [Situation inhabituelle déjà rencontrée] : [ce qu'il faut faire]

## Après chaque exécution

1. Exécuter le protocole de vérification de la section « Définition de terminé ».
2. Ajouter une ligne à `${CLAUDE_SKILL_DIR}/runs.jsonl` au format `{"type":"run","date":"AAAA-MM-JJ","passed":5,"failed":0,"unverified":1,"failed_checks":[],"note":"..."}`.
3. Si je corrige le résultat, proposer `/forge fix [nom]`.
4. Si aucun outil d'écriture de fichiers n'est disponible (par exemple sur claude.ai), le dire, donner le texte complet du fichier modifié et son chemin exact, et rappeler de remplacer l'ancien upload au lieu d'en garder deux versions.
