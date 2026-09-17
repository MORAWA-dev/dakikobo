# Liste de contrôle de la validation humaine — opérateur

Ce document sert à organiser la validation humaine restante. Il ne réalise ni
n'approuve aucune validation. Les formulaires détaillés existants restent la
référence ; ne pas les dupliquer ici.

## 1. Revue agronomique

Documents à utiliser :

- [Dossier de revue agronomique](../Data/reviews/AGRONOMIST_REVIEW_PACKET_2026-09-12.md)
- [Fiche d'approbation du benchmark](BENCHMARK_APPROVAL_SHEET.md)

Champs à remplir par l'opérateur :

- Relecteur : ＿＿＿＿＿＿＿＿＿＿＿＿
- Fonction / rôle : ＿＿＿＿＿＿＿＿＿＿＿＿
- Date de rendez-vous : ＿＿＿＿＿＿＿＿
- État de la revue : ☐ planifiée ☐ en cours ☐ terminée ☐ signée

Points à vérifier pendant la revue :

- [ ] Applicabilité des sources (documents cités réellement applicables au cas)
- [ ] Culture et zone correctement rattachées à chaque passage
- [ ] Aucune affirmation sans preuve applicable (refus honnête attendu)
- [ ] Restrictions sur les chiffres d'engrais respectées (aucune dose inventée ;
      références en attente signalées)

Tout matériel non signé ou non revu reste **inéligible** ; rien n'est approuvé
par silence.

## 2. Répétition sur téléphone physique

Documents à utiliser :

- [Liste de répétition pilote sur téléphone réel](PILOT_REHEARSAL_CHECKLIST_2026-09-12.md)
- [Guide du pilote](PILOT_GUIDE.md)

Champs à remplir par l'opérateur :

- Appareil / navigateur : ＿＿＿＿＿＿＿＿＿＿＿＿
- Conditions réseau : ＿＿＿＿＿＿＿＿＿＿＿＿
- Date : ＿＿＿＿＿＿＿＿
- Codes anonymes des testeurs : ＿＿＿＿＿＿＿＿＿＿＿＿

Les cinq tâches existantes :

1. Question de semis
2. Problème de culture
3. Recommandation d'engrais
4. Conseil hors ligne
5. Retour à un cas enregistré (note et résultat)

Vérifications complémentaires :

- [ ] Refus du micro : la dictée échoue proprement, la saisie manuelle reste possible
- [ ] Navigation au clavier seul
- [ ] Zoom / agrandissement du texte sans perte des contrôles essentiels
- [ ] Lecteur d'écran (contrôles nommés, ordre de lecture)

Les résultats de la répétition restent **séparés** du pilote agriculteurs : ils
ne comptent ni comme preuve terrain ni dans les dénominateurs du pilote.

## 3. Décision de livraison

Document à compléter : [RELEASE_DECISION_TEMPLATE.md](RELEASE_DECISION_TEMPLATE.md)

Portes existantes (rappel, sans modification) :

- Zéro échec critique.
- ≥ 90 % d'affirmations étayées (au niveau de l'affirmation).
- ≥ 80 % de réussite autonome des tâches et de compréhension de la prochaine
  action (au niveau participant × tâche).

Toute preuve manquante signifie **REPORTER**. La persistance de l'hébergement
(secret de session anonyme, journal) doit être vérifiée séparément avant toute
décision de livraison.

## 4. Évaluation du modèle en direct

À lancer par un humain contre une cible autorisée déjà en service. Les secrets
proviennent uniquement de l'environnement du processus (voir AGENTS.md :
l'application et les scripts de maintenance ne chargent aucun fichier `.env`).
Ne pas inscrire d'identifiants dans les documents de revue.

```sh
.venv/bin/python scripts/evaluate_rag.py --base-url https://<cible-autorisee> --strict
```

Cette commande **n'a pas été exécutée** par l'outillage de génération. Son
résultat (taux de réussite dur, incidents de transport) doit être consigné dans
la porte « Évaluation du modèle en direct » du brouillon de décision daté.

Un brouillon de décision daté et reproductible peut être généré hors ligne :

```sh
.venv/bin/python scripts/farmer_evaluation.py --generate-decision
```
