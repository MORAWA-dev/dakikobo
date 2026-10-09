# Phase 1 : preuves sources et évaluation — 9 octobre 2026

**Statut : préparation technique ; validation agronomique et droits en attente.**

## Défaut reproduit et correction

Le déploiement antérieur (`56edbfdcd73cf50b8ce2a8700b3427add87f5144`, GitHub
`b5817a11adfb5d5f263ca7f90b8a9b3204a974d0`) pouvait citer la synthèse
institutionnelle OAPH pour prescrire une profondeur ou une quantité de semences
de mil. Les pages d'orientation ne justifient pas ces chiffres. Le score vectoriel
et la présence d'une culture dans les métadonnées ne constituent pas une preuve.

La nouvelle règle exclut les deux synthèses institutionnelles des questions de
terrain avant l'appel au modèle. Elles restent accessibles pour les questions
institutionnelles ; une question mixte comme « Selon OAPH, quand semer le mil ? »
reste insuffisamment étayée. Les mots techniques contenus dans un avertissement
ne débloquent pas la génération. Le filtre adventices existant est conservé.
Cette règle ciblée n'est pas une preuve universelle d'implication entre texte et
réponse. La revue des assertions reste nécessaire après toute promotion.

## Questions et passages à faire examiner

| Questions d'évaluation | Candidat à examiner | Résultat exigé aujourd'hui |
|---|---|---|
| Quand semer le mil ? Profondeur / semences par hectare ? | Aucun extrait mil approuvé ; OAPH exclu | Refus sans source ni fiche d'action |
| Quand semer ? avec contexte mil/Kaya | Même manque, le contexte ne crée pas de preuve | Refus |
| Stocker le niébé contre les bruches | I4, IITA PDF 60–61 (p. 54–55), dossier existant | Refus tant que non approuvé |
| Désherber le niébé | IITA PDF 30 (p. 24), addendum | Refus tant que non approuvé |
| Adventices de l'arachide | Passages ProSol nouvellement repérés, addendum et limites de vérification | Refus tant que non approuvé |
| Réussir l'arachide ; rotation niébé-céréales | Examiner les passages pertinents, sans étendre la portée d'I1/I2/I4/P1 | Refus |
| Préparer du compost ; conserver l'humidité pour le sorgho | P1 et autres passages ProSol à délimiter par culture/sol | Refus tant que non approuvé |
| Signes sur les feuilles de maïs | Aucun passage maïs approuvé ; I3 n'est pas une citation IITA | Refus et prudence diagnostique |
| Signification OAPH ; rôle CILSS | Synthèses institutionnelles déjà éligibles | Réponse institutionnelle avec source |
| Fumure sorgho, y compris français simple | Outil déterministe, chiffres non validés | Chiffres suspendus, confirmation locale |

Le [dossier historique](../Data/reviews/AGRONOMIST_REVIEW_PACKET_2026-09-12.md)
et l'[addendum](../Data/reviews/PHASE1_REVIEW_ADDENDUM_2026-10-09.md) indiquent les
originaux, empreintes, pages, formulations proposées, limites et décisions vierges.
Ces documents de revue restent hors du corpus Markdown éligible.

## Mesure avant modification

La suite renforcée de 19 cas a été exécutée sur le déploiement antérieur :
**10/19 cas réussis (53 %), 9 échecs, sortie stricte 1**, avec 18 avertissements
indicatifs. Rapport temporaire : `/private/tmp/dakikobo-phase1-before.md`.
L'ancien résultat 14/14 portait sur des critères structurels plus faibles : il
ne validait pas l'ancrage agronomique. Le nouveau résultat n'est donc pas une
régression causée par la correction ; c'est la mise en évidence du défaut connu.

Les refus sont obligatoires individuellement : une moyenne supérieure au seuil
ne masque pas un échec de sécurité. Un refus doit contenir une réponse non vide,
`answer_kind=refusal`, confiance faible, aucune source et aucune fiche d'action.
Les tests utilisent aussi les vrais textes des deux synthèses, ainsi que des
contre-exemples : un guide technique pertinent reste disponible ; une question
institutionnelle reste possible. Les doublures HTTP vérifient l'absence d'appel
au modèle lorsque seuls des documents d'orientation sont retrouvés.

## Après déploiement et décision humaine

Consulter la dernière entrée SESSION pour les résultats après fusion/déploiement
et la correspondance exacte des SHA. Ne pas préremplir un succès futur ici.

La phase complète reste en attente d'un **dossier de revue signé** : décisions
par formulation, culture et zone, corrections/limites, identité/date du relecteur
et disposition des droits de réutilisation. Un silence ou une signature générale
ne valide ni tous les chapitres ni les doses. Après cette décision : créer des
fiches limitées aux passages autorisés, actualiser la matrice et l'éligibilité,
reconstruire l'index et comparer les réponses aux extraits approuvés avant de
modifier les attentes de refus. Aucun statut de source ni dose n'a été modifié.
