# Liste de répétition pilote sur téléphone réel — 12 septembre 2026

**Statut : BLOQUÉ/PARTIEL — aucun test sur téléphone physique n'a été réalisé.**
La vérification existante (`reports/browser_replay_check/`, Chromium sans
interface à 320 et 1280 px) est un contrôle navigateur local, **pas** un test
sur téléphone réel. Cette liste définit exactement ce qu'un opérateur humain
doit exécuter et consigner avant que K4 puisse être déclaré terminé.

## Conditions à établir

- **Appareil :** un téléphone Android d'entrée de gamme (≤ 2 Go de RAM, Android
  Go ou équivalent), navigateur Chrome réel (pas d'émulateur).
- **Réseau :** connexion limitée (throttling « Slow 4G » via les outils
  développeur à distance, ou données mobiles en zone à faible couverture).
- **Testeurs :** 1 à 2 personnes non-agriculteurs (répétition, pas le pilote).
- **Compte rendu :** aucune information personnelle des testeurs ne doit être
  enregistrée (pas de nom, numéro, photo de personne, ni localisation précise).

## Les cinq tâches pilote

Pour chaque tâche, consigner : réussite sans aide / avec aide / échec, temps
approximatif, et tout comportement inattendu.

| # | Tâche | Critère de réussite |
|---|---|---|
| T1 | Poser une question de semis (ex. « Quand semer le mil ? ») | Réponse affichée avec sources ; date de fraîcheur visible si la réponse vient du cache |
| T2 | Clarifier un problème de culture (symptômes + culture/étape, photo optionnelle) | L'application demande le contexte manquant ; pas de diagnostic certain |
| T3 | Comprendre une recommandation d'engrais | Mention explicative (doses exactes suspendues) ; avertissement de confirmation affiché |
| T4 | Retrouver un conseil hors ligne | Couper le réseau, rouvrir l'application : bannière hors ligne, dernier conseil lisible avec sa date d'enregistrement |
| T5 | Noter un conseil puis enregistrer un résultat (« Avez-vous appliqué… ») | Note enregistrée ; si hors ligne, le résultat est mis en file puis envoyé au retour du réseau |

## Grille de consignation (à copier par testeur)

| Champ | À remplir |
|---|---|
| Appareil / navigateur / version | |
| Conditions réseau | |
| T1 résultat + observations | |
| T2 résultat + observations | |
| T3 résultat + observations | |
| T4 résultat + observations | |
| T5 résultat + observations | |
| Défaillances observées | |
| Corrections appliquées | |
| Résultat du nouveau test après correction | |

## Règles

- Aucun résultat ne doit être rempli sans exécution réelle sur l'appareil.
- Toute défaillance corrigée exige un nouveau passage de la tâche concernée.
- Le rapport final va dans `reports/` (daté), sans données personnelles.
- K4 ne devient « terminé » qu'avec ce rapport réel ; sinon il reste
  BLOQUÉ/PARTIEL avec cette liste comme action restante exacte.
