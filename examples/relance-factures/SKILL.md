---
name: relance-factures
description: Relance les factures clients impayées à J+7, J+30 et J+60 après l'échéance, avec un email adapté au palier. Utilise ce skill dès que je dis « relance les impayés », « relance la facture de [client] », « prépare les relances du mois », « qui n'a pas payé ? » ou « envoie un rappel de paiement ». Il choisit le palier selon l'ancienneté, retrouve le contact, applique le ton prévu et prépare un brouillon, sans jamais l'envoyer sans mon accord.
metadata:
  skill-forge: "1"
  created: "2026-09-15"
---

## Objectif

Préparer pour chaque facture échue le brouillon d'email de relance du bon palier (J+7, J+30 ou J+60), prêt à être validé par moi.

## Quand l'utiliser

- Une facture est impayée 7 jours ou plus après son échéance.
- Je demande les relances du mois ou la relance d'un client précis.
- Ne pas l'utiliser pour une facture contestée par le client : voir Cas particuliers.

## Entrées

- Liste des factures impayées : export du logiciel de facturation, fichier `impayes.csv` dans le dossier courant (colonnes client, numéro, montant, échéance).
- Contact du client : `files/contacts-clients.md`.
- Date du jour : date du système.

## Étapes

1. Lire `impayes.csv` et calculer pour chaque facture le nombre de jours écoulés depuis l'échéance.
2. Ouvrir `files/echelle-relance.md` et retenir le palier : J+7, J+30 ou J+60. Ignorer les factures à moins de 7 jours.
3. Chercher le client dans `files/contacts-clients.md` pour l'adresse email, le prénom du contact et le tutoiement ou vouvoiement.
4. Rédiger le brouillon avec le gabarit du palier dans `files/echelle-relance.md`, en citant le numéro de facture, le montant et la date d'échéance.
5. Relire le brouillon avec `files/regles-ton.md` et retirer toute formule interdite.
6. Exécuter la Définition de terminé, puis me présenter les brouillons un par un. Ne rien envoyer.

## Décisions

- Si la facture a 7 à 29 jours de retard, alors utiliser le gabarit J+7 (rappel courtois).
- Si la facture a 30 à 59 jours de retard, alors utiliser le gabarit J+30 et demander une date de paiement.
- Si la facture a 60 jours de retard ou plus, alors utiliser le gabarit J+60, mettre la comptabilité en copie et me prévenir avant toute suite.
- Si le client est absent de `files/contacts-clients.md`, alors me demander l'adresse au lieu d'en deviner une.
- Si le montant dépasse 5 000 EUR, alors me le signaler en tête de réponse.

## Boîte à outils

| Fichier | Usage | Quand ne pas l'utiliser |
|---|---|---|
| `files/echelle-relance.md` | Paliers et gabarits d'email J+7, J+30, J+60 | Facture contestée |
| `files/contacts-clients.md` | Adresse, prénom et registre de chaque client | Client absent du fichier : demander |
| `files/regles-ton.md` | Formules autorisées et interdites par palier | Jamais à ignorer |

## Définition de terminé

- [ ] Montant du brouillon égal au montant de `impayes.csv` | Preuve : chiffre comparé à la ligne source | Échec si : écart supérieur à 0,01 EUR
- [ ] Palier correspond à l'ancienneté | Preuve : calcul date du jour moins échéance | Échec si : le gabarit utilisé n'est pas celui du palier de `files/echelle-relance.md`
- [ ] Adresse du destinataire issue du carnet | Preuve : champ comparé à `files/contacts-clients.md` | Échec si : adresse absente du fichier ou différente
- [ ] Numéro de facture et date d'échéance cités | Preuve : citation relevée dans le brouillon | Échec si : l'un des deux manque
- [ ] Aucune formule interdite | Preuve : recherche des formules de `files/regles-ton.md` dans le brouillon | Échec si : au moins une occurrence
- [ ] Longueur du corps | Preuve : comptage des mots | Échec si : plus de 150 mots
- [ ] Aucun envoi effectué | Preuve : statut du brouillon dans la réponse | Échec si : un message est parti sans mon accord écrit

### Protocole de vérification

1. Exécuter chaque check.
2. Corriger les échecs.
3. Relancer les checks.
4. Rapporter une ligne pass/fail par check avec sa preuve.
5. Lister ce qui n'a pas pu être vérifié et pourquoi, sans le marquer réussi.
6. Si 3 checks ou plus échouent au premier passage, s'arrêter et identifier l'étape du processus fautive avant de retoucher le résultat.

## Cas particuliers

- Facture contestée par le client : ne pas relancer, me le signaler.
- Paiement partiel : relancer uniquement le solde et citer le montant déjà reçu.
- Plusieurs factures échues pour un même client : un seul email, une ligne par facture, palier de la plus ancienne.
- Jour férié ou week-end : préparer le brouillon quand même, noter que l'envoi attendra le jour ouvré.

## Après chaque exécution

1. Exécuter le protocole de vérification de la Définition de terminé.
2. Ajouter une ligne à `${CLAUDE_SKILL_DIR}/runs.jsonl` au format `{"type":"run","date":"AAAA-MM-JJ","passed":5,"failed":0,"unverified":1,"failed_checks":[],"note":"..."}`.
3. Si je corrige le résultat, proposer `/forge fix relance-factures`.
4. Si aucun outil d'écriture de fichiers n'est disponible (par exemple sur claude.ai), le dire, donner le texte complet du fichier modifié et son chemin exact, et rappeler de remplacer l'ancien upload au lieu d'en garder deux versions.
