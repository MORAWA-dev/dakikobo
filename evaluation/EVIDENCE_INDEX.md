# Index des preuves — pilotage des validations

Index d'une page des artefacts canoniques de preuve. Il pointe vers les
rapports et workflows faisant autorité ; il ne copie aucun résultat, aucun
relecteur, aucune date d'approbation. L'autorité de chaque preuve est
indiquée dans son entrée ci-dessous. Les inventaires SOURCE_ELIGIBILITY
datés sont des instantanés historiques ; SOURCE_ELIGIBILITY.md reste
l'inventaire canonique régénérable.

Légende des statuts : `automated` · `human pending` · `phone pending` ·
`agronomist pending` · `hosting pending`.

## 1. Revue des sources — `human pending` / `agronomist pending`

- Inventaire canonique : [SOURCE_ELIGIBILITY.md](../Data/reviews/SOURCE_ELIGIBILITY.md)
  (régénéré par `scripts/audit_source_eligibility.py` ; les versions datées
  `SOURCE_ELIGIBILITY_2026-09-06.md` et `SOURCE_ELIGIBILITY_2026-09-12.md`
  sont des instantanés historiques).
- Validation propriétaire déjà effectuée pour les sources MAERAH/OAPH et
  CILSS : [OWNER_SIGNOFF.md](../Data/reviews/OWNER_SIGNOFF.md).
- Dossier de revue agronomique :
  [AGRONOMIST_REVIEW_PACKET_2026-09-12.md](../Data/reviews/AGRONOMIST_REVIEW_PACKET_2026-09-12.md)
  — statut `agronomist pending` (bloc signature vierge ; aucune promotion de
  source sans signature).

## 2. Répétition navigateur — `automated`

- Workflow : [browser-rehearsal.yml](../.github/workflows/browser-rehearsal.yml).
- Compte rendu conservé sous version :
  [accessibility-2026-09-12.md](../reports/browser_replay_check/accessibility-2026-09-12.md).
- Preuve Chromium headless uniquement : elle ne remplace ni les essais sur
  téléphone physique ni la validation avec des participants.

## 3. Continuité du journal — `automated` (local) / `hosting pending` (hébergeur)

- Workflow : [docker-journal-rehearsal.yml](../.github/workflows/docker-journal-rehearsal.yml).
- État opérationnel :
  [operational_readiness_2026-09-15.md](../reports/operational_readiness_2026-09-15.md)
  — la reprise locale par montage de volume est vérifiée ; la durabilité du
  stockage de l'hébergeur reste non démontrée (`hosting pending`).

## 4. Répétition pilote sur téléphone réel — `phone pending`

- Liste de contrôle :
  [PILOT_REHEARSAL_CHECKLIST_2026-09-12.md](PILOT_REHEARSAL_CHECKLIST_2026-09-12.md)
  — aucun test sur téléphone physique réalisé ; les résultats de répétition
  restent séparés du pilote agriculteurs.

## 5. Approbation du benchmark — `agronomist pending`

- Fiche d'approbation : [BENCHMARK_APPROVAL_SHEET.md](BENCHMARK_APPROVAL_SHEET.md)
  couvrant [farmer_benchmark.json](farmer_benchmark.json) — brouillon, aucune
  décision pré-remplie ; ne peut servir de critère de mise en production tant
  que la revue agronomique n'est pas signée.

## 6. Décision de livraison — `human pending`

- Gabarit de décision : [RELEASE_DECISION_TEMPLATE.md](RELEASE_DECISION_TEMPLATE.md)
  — état REPORTÉ tant que tous les champs de preuve ne sont pas remplis.
- Autorité de processus : [PILOT_GUIDE.md](PILOT_GUIDE.md).
- Synthèse opérateur des validations humaines :
  [HUMAN_VALIDATION_CHECKLIST.md](HUMAN_VALIDATION_CHECKLIST.md).
