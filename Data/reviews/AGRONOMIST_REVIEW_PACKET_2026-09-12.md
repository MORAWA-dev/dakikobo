# Dossier de revue agronomique — 12 septembre 2026

**Statut : PRÊT POUR REVUE HUMAINE — relecteur et date à confirmer.**
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

Reconfirmation technique du 17 septembre 2026 : les deux PDF ont été de nouveau
récupérés depuis les URL pérennes ci-dessus, leurs empreintes SHA-256
revérifiées (identiques aux valeurs enregistrées) et les passages verbatim
annexés (I1, I2, I3, I4, P1) re-extraits page par page. Les cinq extraits
concordent avec les pages citées ; aucun texte n'a été modifié et aucune mention
« à reconfirmer » n'est requise. Cette étape établit la provenance ; la validité
agronomique reste votre décision.

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
| 1 | mil | Semis | Aucun candidat vérifié | Sources examinées : CILSS, MAERAH/OAPH, IITA (niébé), ProSol (fertilité) | Manque documenté, voir « Cellules sans extrait candidat » | ☐ | ☐ | ☐ | ＿＿ |
| 2 | mil | Fertilité | P1 (général ; applicabilité à confirmer) | ProSol PDF 6 (p. v), 9–10 (p. 1–2) | Synthèse interprétative | ☐ | ☐ | ☐ | ＿＿ |
| 3 | mil | Ravageurs | Aucun candidat vérifié | Sources examinées : CILSS, MAERAH/OAPH, IITA (niébé), ProSol (fertilité) | Manque documenté, voir « Cellules sans extrait candidat » | ☐ | ☐ | ☐ | ＿＿ |
| 4 | mil | Stockage | Aucun candidat vérifié | Sources examinées : CILSS, MAERAH/OAPH, IITA (niébé), ProSol (fertilité) | Manque documenté, voir « Cellules sans extrait candidat » | ☐ | ☐ | ☐ | ＿＿ |
| 5 | sorgho | Semis | Aucun candidat vérifié | Sources examinées : CILSS, MAERAH/OAPH, IITA (niébé), ProSol (fertilité) | Manque documenté, voir « Cellules sans extrait candidat » | ☐ | ☐ | ☐ | ＿＿ |
| 6 | sorgho | Fertilité | P1 (général ; applicabilité à confirmer) | ProSol PDF 6 (p. v), 9–10 (p. 1–2) | Synthèse interprétative | ☐ | ☐ | ☐ | ＿＿ |
| 7 | sorgho | Ravageurs | Aucun candidat vérifié | Sources examinées : CILSS, MAERAH/OAPH, IITA (niébé), ProSol (fertilité) | Manque documenté, voir « Cellules sans extrait candidat » | ☐ | ☐ | ☐ | ＿＿ |
| 8 | sorgho | Stockage | Aucun candidat vérifié | Sources examinées : CILSS, MAERAH/OAPH, IITA (niébé), ProSol (fertilité) | Manque documenté, voir « Cellules sans extrait candidat » | ☐ | ☐ | ☐ | ＿＿ |
| 9 | maïs | Semis | Aucun candidat vérifié | Sources examinées : CILSS, MAERAH/OAPH, IITA (niébé), ProSol (fertilité) | Manque documenté, voir « Cellules sans extrait candidat » | ☐ | ☐ | ☐ | ＿＿ |
| 10 | maïs | Fertilité | P1 (général ; applicabilité à confirmer) | ProSol PDF 6 (p. v), 9–10 (p. 1–2) | Synthèse interprétative | ☐ | ☐ | ☐ | ＿＿ |
| 11 | maïs | Ravageurs | Aucun candidat vérifié | Sources examinées : CILSS, MAERAH/OAPH, IITA (niébé), ProSol (fertilité) | Manque documenté, voir « Cellules sans extrait candidat » | ☐ | ☐ | ☐ | ＿＿ |
| 12 | maïs | Stockage | Aucun candidat vérifié | Sources examinées : CILSS, MAERAH/OAPH, IITA (niébé), ProSol (fertilité) | Manque documenté, voir « Cellules sans extrait candidat » | ☐ | ☐ | ☐ | ＿＿ |
| 13 | niébé | Semis | I1 | IITA PDF 12 (p. 6) | Paraphrase fidèle | ☐ | ☐ | ☐ | ＿＿ |
| 14 | niébé | Fertilité | I2 ; P1 | IITA PDF 29 (p. 23) ; ProSol PDF 6 (p. v), 9–10 (p. 1–2) | I2 paraphrase fidèle ; P1 interprétatif ; doses du tableau non validées | ☐ | ☐ | ☐ | ＿＿ |
| 15 | niébé | Ravageurs | I3 (règle éditoriale, pas un passage source) | IITA PDF 34 (p. 28) décrit la diversité des contraintes ; confirmation au champ non trouvée | **Non trouvé dans l'original** — règle produit, pas une citation IITA | ☐ | ☐ | ☐ | ＿＿ |
| 16 | niébé | Stockage | I4 | IITA PDF 60–61 (p. 54–55) | Paraphrase fidèle de deux pages | ☐ | ☐ | ☐ | ＿＿ |
| 17 | arachide | Semis | Aucun candidat vérifié | Sources examinées : CILSS, MAERAH/OAPH, IITA (niébé), ProSol (fertilité) | Manque documenté, voir « Cellules sans extrait candidat » | ☐ | ☐ | ☐ | ＿＿ |
| 18 | arachide | Fertilité | P1 (général ; applicabilité à confirmer) | ProSol PDF 6 (p. v), 9–10 (p. 1–2) | Synthèse interprétative | ☐ | ☐ | ☐ | ＿＿ |
| 19 | arachide | Ravageurs | Aucun candidat vérifié | Sources examinées : CILSS, MAERAH/OAPH, IITA (niébé), ProSol (fertilité) | Manque documenté, voir « Cellules sans extrait candidat » | ☐ | ☐ | ☐ | ＿＿ |
| 20 | arachide | Stockage | Aucun candidat vérifié | Sources examinées : CILSS, MAERAH/OAPH, IITA (niébé), ProSol (fertilité) | Manque documenté, voir « Cellules sans extrait candidat » | ☐ | ☐ | ☐ | ＿＿ |

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

## Annexes — extraits des pages sources

**Note sur les droits :** les passages ci-dessous sont reproduits uniquement pour
la revue agronomique interne. Ils ne font pas partie de l'application publiée et
les documents originaux conservent leurs licences et droits d'origine (guide
IITA via la notice CGIAR ; catalogue ProSol via Inter-réseaux). Si le relecteur
souhaite une diffusion plus large, les conditions de réutilisation de chaque
source doivent d'abord être confirmées.

Chaque extrait indique : l'identifiant du candidat, la source, l'empreinte
SHA-256 du PDF contrôlé, la page physique (PDF) et le numéro imprimé (p.),
puis le passage verbatim. La note de fidélité reprend le rapprochement déjà
établi le 12 septembre 2026.

### I1 — Semis niébé — IITA, PDF 12 (p. 6)

Source : *Guide sur la production du niébé en Afrique de l'Ouest* (IITA).
SHA-256 : `a3c823be2a118f153bae16f6fa8d5e727beb193154c05ca9ff32a779042a47a3`.
Fidélité : **paraphrase fidèle**.

> « Choisissez des semences en bon état (Fig. 2a) exemptes de trous
> d'infestation ou de rides (Fig. 2b) pour le semis. Des semences bien stockées
> dans des conditions optimales auront une bonne germination. »

*(La même page décrit l'enrobage des semences avec des produits précis — ce
passage n'est pas repris comme recommandation : les produits et doses exigent
une vérification d'homologation actuelle.)*

### I2 — Fertilité niébé — IITA, PDF 29 (p. 23)

Même source et même empreinte que I1. Fidélité : **paraphrase fidèle** ; les
doses du tableau 9 ne sont **pas** validées par cette revue technique.

> « Les plants de niébé ne nécessitent pas trop d'engrais azoté car ils fixent
> leur propre azote dans l'air à l'aide des nodules des racines. […] Le niébé a
> besoin de plus de phosphore que d'azote […] pour aider la culture à bien
> produire de nodule et à fixer son propre azote dans l'air. […] Cependant, une
> analyse de sol est la meilleure façon de déterminer les niveaux d'éléments
> nutritifs du sol. »

### I3 — Ravageurs niébé — IITA, PDF 34 (p. 28)

Même source et même empreinte que I1. Fidélité : **règle de prudence ajoutée
par la synthèse locale — non trouvée comme recommandation dans l'original.**
La formulation « Les maladies et ravageurs doivent être confirmés au champ »
n'a pas de passage source correspondant ; c'est un constat de la revue, pas un
oubli. Le passage réel de la page :

> « Le niébé est sensible à un large éventail de parasites et de maladies qui
> attaquent la culture à tous les stades de croissance. Il s'agit des insectes,
> des bactéries, des champignons et des virus. Des densités d'organismes
> nuisibles élevées peuvent entraîner une perte totale de rendement en grains
> si aucune mesure de lutte n'est appliquée. »

Décision suggérée à trancher par le relecteur : conserver la phrase comme règle
produit DakiKobo sans l'attribuer à l'IITA, ou la retirer.

### I4 — Stockage niébé — IITA, PDF 60–61 (p. 54–55)

Même source et même empreinte que I1. Fidélité : **paraphrase fidèle de deux
pages**.

> PDF 60 (p. 54) : « Après la récolte, séchez les gousses sur une plateforme ou
> une bâche pour bien les sécher avant le battage (Fig. 5b). Ensuite, battez
> les gousses et vannez pour séparer les graines de la balle ou des fanes. Les
> graines sont ensuite triées pour éliminer les débris et les brisures […] »
>
> PDF 61 (p. 55) : « Nettoyez le magasin à fond avant le chargement d'une
> nouvelle récolte. […] Seules les semences bien séchées et bien nettoyées
> doivent être conservées (Fig. 7a et 7b). La teneur en humidité propice pour
> le stockage est de 7 à 8% ; les graines produisent un craquement lorsqu'elles
> sont écrasées entre les dents. […] Il existe divers matériels hermétiques
> pour le stockage ; les sacs PICS sont les plus utilisés […] »

### P1 — Fertilité (général) — ProSol, PDF 6 (p. v), 9–10 (p. 1–2)

Source : *Catalogue de fiches techniques des mesures d'amélioration de la
fertilité des sols* (ProSol / Inter-réseaux, 2020).
SHA-256 : `e0e45222a0f182ec53d612b29ce591c161578cbfc3e2b76d478f2ee494057bb0`.
Fidélité : **synthèse interprétative, non textuelle** — la formulation locale
« La fumure organique est un levier central » n'apparaît pas dans l'original ;
le catalogue présente la fumure organique comme le premier de cinq thèmes et
décrit le parc amélioré comme moyen de produire du fumier et d'amender les
champs.

> PDF 6 (p. v) : « L'une des principales contraintes à laquelle les
> agriculteurs du Burkina Faso font face, demeure la baisse de la fertilité des
> sols. […] Le projet ProSol s'est inscrit dans une dynamique de capitalisation
> et de valorisation des bonnes pratiques agricoles […] »
>
> PDF 9 (p. 1) : « Un parc amélioré est un enclos fixe, utilisé pendant toute
> l'année pour la stabulation des animaux et la production du fumier […]
> Objectifs de production : Stabuliser des animaux ; Optimiser la collecte du
> fumier ; Amender les champs ; Amélioration le rendement agricole. »
>
> PDF 10 (p. 2) : « Il est conseillé de composter les déjections et les restes
> de débris avant de l'apporter au champ. […] Avantages : Faible coût de
> production ; Amélioration de la collecte du fumier ; Recyclage des résidus de
> récolte […] Inconvénients/contraintes : Exigence de main d'œuvre […] ;
> Compétition sur la biomasse. »

### Cellules sans extrait candidat

Les 12 cellules (semis, ravageurs et stockage du mil, du sorgho, du maïs et de
l'arachide) n'ont **aucun candidat vérifié** à ce jour. Ce n'est pas un oubli :
les quatre sources du dépôt susceptibles de contenir un candidat ont été
examinées et aucune ne fournit d'extrait vérifié propre à la fois à la culture
et au thème :

- **CILSS** (`cilss_orientation_sahel_2026.md`, éligible) : synthèse
  d'orientation régionale Sahel, sans pratique de semis, de ravageurs ni de
  stockage par culture.
- **MAERAH / OAPH** (`maerah_oaph_orientation_burkina_2026.md`, éligible) :
  synthèse d'orientation gouvernementale (filières, politique), sans pratique
  culture-par-thème.
- **IITA** (`iita_niebe_afrique_ouest_2018.md`, en attente de revue humaine,
  inéligible) : guide **niébé uniquement** ; ne couvre pas le mil, le sorgho,
  le maïs ni l'arachide.
- **ProSol** (`prosol_fertilite_sols_burkina_2020.md`, en attente de revue
  humaine, inéligible) : catalogue **fertilité des sols en général**, sans
  section de semis, de ravageurs ni de stockage propre à une culture.

Il n'existe donc rien de vérifié à annexer pour ces 12 cellules. Le relecteur
peut soit les laisser en attente, soit indiquer un document de référence à
acquérir (par exemple un guide de production propre au mil, au sorgho, au maïs
ou à l'arachide). Aucun extrait n'est inventé pour combler ces manques.
