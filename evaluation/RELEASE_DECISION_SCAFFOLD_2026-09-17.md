# Décision de livraison DakiKobo — brouillon daté

**État :** REPORTÉE tant que tous les champs de preuve humaine, agronomique et opérationnelle ne sont pas remplis.

Ce document est un brouillon reproductible généré hors ligne à partir de l'état du dépôt. Il ne réalise ni n'approuve aucune évaluation humaine ou en direct. Les champs humains restent vides tant qu'un relecteur ne les a pas complétés dans les formulaires de référence.

## Version évaluée

- Commit : `a41c842d6febbdf38d1cf771875ed59102094a2b`
- Date de génération du brouillon (UTC) : 2026-09-17
- Environnement d'exécution mesuré : ＿＿＿＿＿＿＿＿＿＿＿＿ (à remplir par l'opérateur)
- Révision de politique de sécurité : `safety-2026-09-09.c625b9b546ba`
- Modèle de conversation : `openai/gpt-oss-120b`
- Modèle Vision : `gemini-2.5-flash`
- Modèle d'embarquement (embeddings) : `paraphrase-multilingual-MiniLM-L12-v2`
- Empreinte du corpus : `11391cefa86f9f32` (2 document(s), type Markdown, embeddings paraphrase-multilingual-MiniLM-L12-v2)
- Documents et statuts de revue : voir Data/reviews/ (inchangés ; aucun statut d'éligibilité modifié)

## Portes de décision

| Porte | Dénominateur | Résultat | Seuil | Décision |
|---|---:|---:|---:|---|
| Sécurité critique | Cas critiques revus | À mesurer | 0 échec | REPORTÉE |
| Affirmations étayées | Affirmations substantielles revues | À mesurer | ≥ 90 % | REPORTÉE |
| Réussite autonome | Participant × tâche | À mesurer | ≥ 80 % | REPORTÉE |
| Prochaine action comprise | Participant × tâche | À mesurer | ≥ 80 % | REPORTÉE |

Une moyenne ne peut pas annuler un échec de sécurité critique. Les réponses sans preuve applicable doivent rester des refus honnêtes et apparaître dans les résultats, pas être retirées du dénominateur.

## Portes humaines et opérationnelles non résolues

Chaque porte reste **en attente**. Aucun relecteur, participant, résultat, date ni approbation n'est renseigné ici : ces champs se remplissent dans les formulaires de référence cités.

### Revue agronomique

- État : ☐ en attente
- Relecteur : ＿＿＿＿＿＿＿＿＿＿＿＿
- Fonction / rôle : ＿＿＿＿＿＿＿＿＿＿＿＿
- Date de la revue : ＿＿＿＿＿＿＿＿
- Référence : evaluation/HUMAN_VALIDATION_CHECKLIST.md, evaluation/BENCHMARK_APPROVAL_SHEET.md

### Répétition sur téléphone physique

- État : ☐ en attente
- Appareil / navigateur : ＿＿＿＿＿＿＿＿＿＿＿＿
- Conditions réseau : ＿＿＿＿＿＿＿＿＿＿＿＿
- Date : ＿＿＿＿＿＿＿＿
- Observateur : ＿＿＿＿＿＿＿＿＿＿＿＿
- Référence : evaluation/PILOT_REHEARSAL_CHECKLIST_2026-09-12.md

### Observations des participants (pilote téléphone)

- État : ☐ en attente
- Codes anonymes des participants : ＿＿＿＿＿＿＿＿＿＿＿＿
- Nombre de cultivateurs : ＿＿＿ / agents agricoles : ＿＿＿
- Observations : ＿＿＿＿＿＿＿＿＿＿＿＿
- Référence : evaluation/PILOT_GUIDE.md (résultats consignés séparément, jamais dans ce brouillon)

### Évaluation du modèle en direct

- État : ☐ en attente (non exécutée)
- Cible autorisée : ＿＿＿＿＿＿＿＿＿＿＿＿
- Date d'exécution : ＿＿＿＿＿＿＿＿
- Taux de réussite dur observé : ＿＿＿＿＿＿＿＿
- Voir la commande documentée ci-dessous.

### Vérification de l'hébergement et de la durabilité

- État : ☐ en attente
- Persistance du secret de session anonyme : ＿＿＿＿＿＿＿＿
- Persistance du journal : ＿＿＿＿＿＿＿＿
- Incidents de disponibilité : ＿＿＿＿＿＿＿＿
- Vérificateur : ＿＿＿＿＿＿＿＿＿＿＿＿

## Évaluation en direct à exécuter par un humain

La commande ci-dessous doit être lancée par un humain contre une cible autorisée déjà en service. Les secrets proviennent uniquement de l'environnement du processus (voir AGENTS.md : l'application et les scripts de maintenance ne chargent aucun fichier `.env`). Ne pas inscrire d'identifiants dans ce document.

```sh
.venv/bin/python scripts/evaluate_rag.py --base-url https://<cible-autorisee> --strict
```

**Cette commande n'a PAS été exécutée lors de la génération de ce brouillon.** Son résultat doit être consigné dans la porte « Évaluation du modèle en direct » ci-dessus une fois lancée.

## Décision

- [ ] LIVRER — toutes les portes obligatoires sont satisfaites.
- [ ] RÉDUIRE LE PÉRIMÈTRE — périmètre et refus compensatoires documentés.
- [x] REPORTER — preuve humaine, agronomique ou opérationnelle manquante.

Responsable de la décision : ＿＿＿＿＿＿＿＿＿＿＿＿

Date : ＿＿＿＿＿＿＿＿

Justification et prochaines actions : ＿＿＿＿＿＿＿＿＿＿＿＿
