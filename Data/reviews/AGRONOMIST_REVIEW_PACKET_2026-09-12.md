# Dossier de revue agronomique — 12 septembre 2026

**Objet :** validation des 20 cellules de la matrice de couverture cultures × thèmes.
**Document de référence :** `Data/reviews/CROP_COVERAGE_MATRIX_2026-09-09.md`
**Durée visée :** environ 2 heures.

## Ce qu'est DakiKobo

DakiKobo est une application web en français qui donne des conseils agricoles aux
petits exploitants du Burkina Faso (mil, sorgho, maïs, niébé, arachide). Elle
répond à partir de documents locaux indexés (RAG), cite ses sources et refuse de
répondre quand la preuve manque. Elle n'invente ni dose d'engrais ni certitude
de diagnostic.

## Ce qui vous est demandé

Vous êtes la dernière étape humaine avant que des passages de deux documents
candidats — le guide IITA sur le niébé et le catalogue ProSol — puissent entrer
dans le corpus de réponses. Pour chacune des 20 cellules du tableau ci-dessous,
vous décidez si l'extrait candidat est agronomiquement acceptable pour être servi
aux agriculteurs :

- **Approuvé** : le passage peut être utilisé tel quel pour cette culture et ce
  thème.
- **Corrigé** : utilisable seulement avec la correction que vous inscrivez
  (formulation, zone, conditions d'application, limite).
- **Rejeté** : ne doit pas être utilisé.

La vérification technique (provenance des PDF, pages, empreintes) est déjà faite
et indiquée ci-dessous. Elle établit que les passages cités existent bien dans
les originaux ; **elle ne juge pas leur validité agronomique** — c'est votre rôle.

## Règle de déblocage

Les cellules que vous n'atteignez pas **restent inéligibles**. Rien n'est
approuvé par silence. Une cellule sans décision signée reste hors du corpus,
exactement comme aujourd'hui. Il vaut mieux signer 8 cellules que d'en laisser
planer 20.

## Identité des originaux contrôlés (12 septembre 2026)

| Code | Document | Pages | Empreinte SHA-256 |
|---|---|---|---|
| IITA | *Guide sur la production du niébé en Afrique de l'Ouest* — notice : https://cgspace.cgiar.org/items/26504a5f-1844-4773-ad7d-6f86b8bead17 — PDF : https://cgspace.cgiar.org/server/api/core/bitstreams/b8b60cb6-a792-4cfb-8ec6-28ee1e4266ae/content | 67 pages PDF | `a3c823be2a118f153bae16f6fa8d5e727beb193154c05ca9ff32a779042a47a3` |
| ProSol | *Catalogue de fiches techniques des mesures d'amélioration de la fertilité des sols* — PDF : https://www.inter-reseaux.org/wp-content/uploads/Catalogue-AFS-ProSol-04-12-2020.pdf | 77 pages PDF | `e0e45222a0f182ec53d612b29ce591c161578cbfc3e2b76d478f2ee494057bb0` |

Convention : « PDF » = page physique du fichier, « p. » = numéro imprimé
(le décalage vient des pages liminaires en chiffres romains).

Notes de fidélité établies par la vérification technique (à confirmer par vous) :

- **I1, I2, I4** : paraphrases fidèles des passages IITA cités.
- **P1** : **synthèse interprétative, non textuelle.** Le catalogue présente la
  fumure organique parmi cinq thèmes ; il n'emploie pas l'expression « levier
  central ». Données économiques notamment Houet/Tuy ; la transposition à
  chaque culture et sol reste à examiner.
- **I3** : **non trouvé dans le guide IITA.** C'est une règle de prudence
  ajoutée par la synthèse locale, à garder comme règle produit sans la citer
  comme recommandation IITA.

## Tableau de revue — 20 cellules (5 cultures × 4 thèmes)

Pour chaque cellule : cochez une seule décision, apposez vos initiales, et
inscrivez la correction ou la limite si la décision est « Corrigé ».

| # | Culture | Thème | Extrait candidat | Source et pages | Note de fidélité | Approuvé | Corrigé (correction ci-dessous) | Rejeté | Initiales |
|---|---|---|---|---|---|---|---|---|---|
| 1 | mil | Semis | Aucun extrait sélectionné | à vérifier | — | ☐ | ☐ | ☐ | ＿＿ |
| 2 | mil | Fertilité | P1 (général ; applicabilité à confirmer) | ProSol PDF 6 (p. v), 9–10 (p. 1–2) | Synthèse interprétative | ☐ | ☐ | ☐ | ＿＿ |
| 3 | mil | Ravageurs | Aucun extrait sélectionné | à vérifier | — | ☐ | ☐ | ☐ | ＿＿ |
| 4 | mil | Stockage | Aucun extrait sélectionné | à vérifier | — | ☐ | ☐ | ☐ | ＿＿ |
| 5 | sorgho | Semis | Aucun extrait sélectionné | à vérifier | — | ☐ | ☐ | ☐ | ＿＿ |
| 6 | sorgho | Fertilité | P1 (général ; applicabilité à confirmer) | ProSol PDF 6 (p. v), 9–10 (p. 1–2) | Synthèse interprétative | ☐ | ☐ | ☐ | ＿＿ |
| 7 | sorgho | Ravageurs | Aucun extrait sélectionné | à vérifier | — | ☐ | ☐ | ☐ | ＿＿ |
| 8 | sorgho | Stockage | Aucun extrait sélectionné | à vérifier | — | ☐ | ☐ | ☐ | ＿＿ |
| 9 | maïs | Semis | Aucun extrait sélectionné | à vérifier | — | ☐ | ☐ | ☐ | ＿＿ |
| 10 | maïs | Fertilité | P1 (général ; applicabilité à confirmer) | ProSol PDF 6 (p. v), 9–10 (p. 1–2) | Synthèse interprétative | ☐ | ☐ | ☐ | ＿＿ |
| 11 | maïs | Ravageurs | Aucun extrait sélectionné | à vérifier | — | ☐ | ☐ | ☐ | ＿＿ |
| 12 | maïs | Stockage | Aucun extrait sélectionné | à vérifier | — | ☐ | ☐ | ☐ | ＿＿ |
| 13 | niébé | Semis | I1 | IITA PDF 12 (p. 6) | Paraphrase fidèle | ☐ | ☐ | ☐ | ＿＿ |
| 14 | niébé | Fertilité | I2 ; P1 | IITA PDF 29 (p. 23) ; ProSol PDF 6 (p. v), 9–10 (p. 1–2) | I2 paraphrase fidèle ; P1 interprétatif ; doses du tableau non validées | ☐ | ☐ | ☐ | ＿＿ |
| 15 | niébé | Ravageurs | I3 (règle éditoriale, pas un passage source) | IITA PDF 34 (p. 28) décrit la diversité des contraintes ; confirmation au champ non trouvée | **Non trouvé dans l'original** — règle produit, pas une citation IITA | ☐ | ☐ | ☐ | ＿＿ |
| 16 | niébé | Stockage | I4 | IITA PDF 60–61 (p. 54–55) | Paraphrase fidèle de deux pages | ☐ | ☐ | ☐ | ＿＿ |
| 17 | arachide | Semis | Aucun extrait sélectionné | à vérifier | — | ☐ | ☐ | ☐ | ＿＿ |
| 18 | arachide | Fertilité | P1 (général ; applicabilité à confirmer) | ProSol PDF 6 (p. v), 9–10 (p. 1–2) | Synthèse interprétative | ☐ | ☐ | ☐ | ＿＿ |
| 19 | arachide | Ravageurs | Aucun extrait sélectionné | à vérifier | — | ☐ | ☐ | ☐ | ＿＿ |
| 20 | arachide | Stockage | Aucun extrait sélectionné | à vérifier | — | ☐ | ☐ | ☐ | ＿＿ |

## Formulations locales rattachées aux extraits (pour mémoire)

| ID | Formulation locale | Zone déclarée ; limite |
|---|---|---|
| P1 | « La fumure organique est un levier central » | Burkina Faso ; données économiques notamment Houet/Tuy, transposition à chaque culture et sol à examiner |
| I1 | « Les semences doivent être en bon état » | Afrique de l'Ouest ; niébé, variété et commune à préciser |
| I2 | « Le phosphore est important pour la nodulation » | Afrique de l'Ouest ; besoins de la parcelle non établis |
| I3 | « Les maladies et ravageurs doivent être confirmés au champ » | Aucune identification certaine ni traitement validé ; homologation actuelle non vérifiée |
| I4 | « Les graines doivent être triées, bien séchées et propres » | Afrique de l'Ouest ; protocole local et mesure de l'humidité à faire confirmer |

## Corrections et observations du relecteur

Pour chaque cellule corrigée ou rejetée, merci de consigner : page PDF et numéro
imprimé, passage original, culture, zone/commune, conditions d'application,
limites, et la raison de la décision.

| Cellule n° | Correction / observation |
|---|---|
| ＿＿ | ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿ |
| ＿＿ | ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿ |
| ＿＿ | ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿ |
| ＿＿ | ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿ |
| ＿＿ | ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿ |
| ＿＿ | ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿ |

## Signature

Je confirme avoir examiné les cellules cochées ci-dessus. Les cellules non
atteintes restent inéligibles au corpus de DakiKobo ; aucune approbation n'est
implicite.

**Nom :** ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿
**Fonction / rôle :** ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿
**Date :** ＿＿＿＿＿＿＿＿＿＿
**Signature :** ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿
**Modalité :** ☐ revue en présentiel ☐ revue à distance — durée effective : ＿＿＿＿

*(Modèle vierge — aucune signature ni décision n'est pré-remplie.)*
