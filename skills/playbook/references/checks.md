# Mode checks : Définition de terminé (couche 3)

But : ne plus dépendre du "ça a l'air bon". Chaque check donne une preuve que l'utilisateur peut inspecter sans faire confiance à Claude, et une condition d'échec nette.

## 1. Rédiger 5 à 10 checks

Remplace le contenu de `## Définition de terminé` dans `SKILL.md`. Base-toi sur `## Étapes`, `## Cas particuliers` et sur ce que l'utilisateur a dit d'un mauvais résultat. Choisis des checks propres à ce job, pas des généralités.

Format, une ligne par check :

`- [ ] <vérification> | Preuve : <type> | Échec si : <condition>`

Types de preuve inspectables :
- chiffre rapproché de sa source ;
- lien ouvert ;
- capture du rendu final ;
- test qui passe ;
- citation qui appuie une affirmation ;
- comptage ;
- champ comparé à un fichier de référence.

Les mots clair, professionnel, qualité, soigné sont interdits sans critère mesurable ("clair" devient "moins de 120 mots, une seule demande"). Un mot subjectif ne peut pas échouer, donc il ne vérifie rien. `validate` les signale.

## 2. Ajouter le protocole de vérification

Sous les checks, ajoute un « Protocole de vérification » :

1. Exécuter chaque check.
2. Corriger les échecs.
3. Relancer les checks.
4. Rapporter une ligne pass/fail par check avec sa preuve.
5. Lister ce qui n'a pas pu être vérifié et pourquoi, sans le marquer réussi.
6. Si 3 checks ou plus échouent au premier passage, s'arrêter et identifier l'étape du processus fautive avant de retoucher le résultat : trois échecs d'un coup signalent un défaut d'étape, pas trois défauts de résultat.

## 3. Valider

Lance `pbf.py validate <nom>`. Il exige 5 à 10 checks contenant « Preuve » et « Échec si ». Corrige les FAIL, montre la section à l'utilisateur, intègre ses retours.
