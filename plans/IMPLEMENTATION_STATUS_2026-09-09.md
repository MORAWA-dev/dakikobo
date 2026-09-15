# Réception initiale du plan — 9 septembre 2026

## Réception actualisée — 15 septembre 2026

Base intégrée : `origin/main` à `e79ebfc3` (PR #5 fusionnée). Le tableau
ci-dessous remplace les états initiaux pour la décision actuelle. Le plan HTML
n'est pas entièrement réceptionné ; aucune preuve humaine n'est implicite.

| Ticket | État actuel | Preuve ou action restante |
|---|---|---|
| 01 | Réceptionné | Base, intégration et conservation des changements documentées dans SESSION. |
| 02 | Technique implémentée ; réception partielle | Régressions Vision/RAG présentes ; revue humaine de sécurité avant pilote. |
| 03 | Technique implémentée ; réception partielle | Identité de sécurité et invalidation testées ; migration sur téléphone physique à vérifier. |
| 04 | Technique implémentée et testée | Refus sans génération et erreurs fournisseur couverts par les tests de routes. |
| 05 | Partiel | Matrice et annexes prêtes ; approbation agronomique, promotion et mesure de couverture requises. |
| 06 | Technique implémentée et testée | Limites multipart, nettoyage audio, concurrence et reprise texte couverts. |
| 07 | Partiel | Restauration isolée et redémarrage HTTP local testés ; volume durable, secret stable et redémarrage/rebuild de la cible à démontrer. Rapport : `reports/operational_readiness_2026-09-15.md`. |
| 08 | Partiel | Accessibilité locale et refus microphone testables ; cinq parcours sur vrais téléphones avec participants requis. |
| 09 | Préparation implémentée ; réception ouverte | Registres et modèle de décision prêts ; jugement expert et résultats humains absents. |
| 10 | Différé conditionnel | Ne commencer qu'après confirmation du besoin par le pilote. |

Documents de travail : `evaluation/RELEASE_DECISION_TEMPLATE.md`,
`evaluation/PILOT_REHEARSAL_CHECKLIST_2026-09-12.md`,
`Data/reviews/AGRONOMIST_REVIEW_PACKET_2026-09-12.md` et `DEPLOYMENT.md`.
La décision de livraison terrain reste REPORTÉE.

## Ticket 01 : base identifiée

Le checkout local reste sur `main`, commit `17e11922`. Après récupération des
références distantes, `origin/main` est à `40bb8a85`, dix commits plus loin.
La branche de sécurité `1e44767a` est intégrée par `fc1d6623` ; le suivi hors ligne
`eea0c9c8` est intégré par `40bb8a85`. Ne pas réimplémenter ces changements.

Les modifications locales préexistantes sont conservées : durcissement HTTP,
secrets exclusivement dans l'environnement, configuration Docker/Apache,
documentation et tests de sécurité ; fichiers de compétences, attributs Git et
plan HTML non suivis. Aucun stash, remplacement du checkout, commit ou déploiement.
Cette passe ajoute uniquement ce rapport et actualise PROJECT_STATE et SESSION.

Le rapport distant `fdbcf0f7` a été lu. Sa description d'un checkout propre ne
s'applique pas à ce répertoire. Ses mentions « ALREADY SATISFIED » doivent être
distinguées de la réception complète des critères du plan.

## Vérification reproductible

| Base | Python hors test RAG réel | JavaScript |
|---|---:|---:|
| Local `17e11922` + modifications existantes | 296 réussis | 13 réussis |
| `origin/main` à `40bb8a85`, checkout isolé | 626 réussis | 20 réussis |

Python : `python -m pytest -q tests --ignore=tests/test_rag.py`, avec le Python
du virtualenv existant. Un avertissement PyPDF2 dans chaque suite.
JavaScript : `node --test tests/js/*.test.js`, avec Node du runtime Codex et
les dépendances déjà installées du projet. Le premier essai isolé ne trouvait
pas jsdom ; le même test réussit avec NODE_PATH dirigé vers ces dépendances.
Export engrais hors ligne identique au fichier suivi ; `git diff --check` réussi.
Aucun appel réel Groq/Gemini, test de navigateur interactif ou vérification du
déploiement dans cette passe. La référence HF locale `bc0670e3` n'est pas une
preuve de la version actuellement servie.

## Réception des tickets suivants

| Ticket | État observé et travail restant |
|---|---|
| 02 | Contrôle Vision/RAG et régressions présents sur origin/main. Examiner les limites et obtenir la revue humaine ; les tests ne prouvent pas la sécurité universelle. |
| 03 | Identité de sécurité serveur et navigateur présente. Vérifier explicitement identité absente/vide et migration suivie d'un passage hors ligne avant réception. Le worker compare actuellement des valeurs pouvant être vides. |
| 04 | Refus avant génération sans source et statuts d'erreur présents. Vérifier chaque scénario du plan après intégration avec le durcissement local. |
| 05 | Deux sources éligibles confirmées via core.source_policy : CILSS et MAERAH/OAPH. La matrice cinq cultures × quatre thèmes peut être préparée techniquement ; l'approbation des extraits reste humaine. |
| 06 | Marge multipart et cache audio présents. Vérifier les fichiers partiels laissés par un arrêt brutal, la concurrence et Réécouter après expiration ; la collecte actuelle parcourt seulement les MP3. |
| 07 | Durcissement présent localement. Un exercice isolé avec données synthétiques et une procédure de sauvegarde peuvent avancer ; la preuve de stockage durable sur la cible reste ouverte. |
| 08–09 | Préparation technique possible ; téléphones réels, participants et jugement agronomique restent nécessaires. |
| 10 | Conditionné au besoin confirmé par le pilote. |

## Prochain lot

Préparer une base intégrant `40bb8a85` et le durcissement local en conservant
chaque modification existante, puis exécuter les régressions de cette combinaison.
Poursuivre les critères non démontrés des tickets 02–04 et 06, et préparer la
matrice de sources du ticket 05. Aucun statut agronomique ne doit être inventé.
La livraison reste soumise aux preuves du plan, notamment revue humaine et pilote.


## Lot suivant — intégration et correction du ticket 03

- `main` avancé à `40bb8a85` ; changements locaux restaurés depuis le stash
  `codex-plan-integration-20260909`, conservé comme sauvegarde.
- Conflits résolus dans SESSION (deux historiques conservés) et app.py
  (cookie Secure et marge multipart conservés ensemble).
- Suite Python combinée : 632 réussis, un avertissement PyPDF2 ; RAG réel exclu.
- Ticket 03 : quatre reproductions échouaient avec HTTP 200 au lieu de 503.
  Le worker exige maintenant une révision non vide avant stockage et rejeu.
  En-têtes absents, vides, composés d'espaces et anciennes entrées avec marqueur
  vide sont couverts. Suite JavaScript : 24 réussis après correction.
- Export engrais inchangé ; contrôle des différences réussi.
- Fichiers de correction : static/sw.js, tests/js/frontend.test.js ; README et
  IMPLEMENTATION_PLAN synchronisés ; PROJECT_STATE et SESSION actualisés.
- Prochain travail : autres critères de migration navigateur du ticket 03,
  fichiers audio partiels et concurrence du ticket 06, matrice documentaire du
  ticket 05. Revue agronomique, stockage sur cible et pilote restent ouverts.
- Aucun nouveau commit, push ou déploiement ; modifications laissées non indexées.


## Lot audio, activation du worker et préparation documentaire

- Ticket 06 : nettoyage des `.tts-*.part` abandonnés, seuil configurable de
  3 600 secondes, verrou POSIX conservé pendant une écriture active, liens
  symboliques ignorés. Deux défauts reproduits avant correction ; test d'une
  écriture suspendue pendant le nettoyage ajouté. Le budget MP3 reste souple
  pour le fichier courant et ne couvre pas les fragments récents/actifs.
- Ticket 03 : activation d'une nouvelle version testée avec stockage partagé
  simulé, suppression des anciennes réponses puis refus hors ligne. Le cycle
  réel sur téléphone reste à vérifier.
- Ticket 05 : [matrice de 20 cellules](../Data/reviews/CROP_COVERAGE_MATRIX_2026-09-09.md)
  préparée avec extraits candidats et zones déclarées. Pages originales et
  approbation agronomique explicitement absentes. Aucune promotion de source.
- Vérification : 635 tests Python hors RAG réel, 25 tests JavaScript ; un
  avertissement PyPDF2. Contrôle des différences réussi.
- Prochain lot : message de reprise après expiration de Réécouter, autres
  scénarios d'éviction concurrente, exercice isolé de sauvegarde/restauration.
  Revue des sources et pilote demeurent des conditions humaines de livraison.


## Lot reprise audio et restauration isolée

- Ticket 06 : échec de lecture reproduit dans le chat jsdom. Message français
  accessible, texte préservé et nouvelle tentative possible ; rejet de play()
  et événement média error couverts. Le fichier supprimé n'est pas régénéré.
- Ticket 07 : exercice textuel synthétique réussi dans des processus Flask
  distincts : cookie propriétaire conservé, autre client exclu, sauvegarde SQLite
  cohérente, restauration isolée, suppression et expiration. Original et copie
  de sauvegarde restent inchangés. Procédure de stockage et retour arrière
  ajoutée dans DEPLOYMENT.md.
- Vérification : 636 tests Python hors RAG réel, 27 JavaScript ; un avertissement
  PyPDF2. Export engrais inchangé ; contrôle des différences réussi.
- Limites : clients de test Flask, pas de serveur HTTP réel, téléphone, redémarrage
  de l'hôte, photo ou volume du fournisseur. Ces preuves restent nécessaires.
- Suite : restauration des photos, budget audio concurrent, validation navigateur
  réelle et revue agronomique des extraits. Aucun déploiement effectué.

## Lot photo, concurrence audio et navigateur — 12 septembre 2026

- Une copie cohérente du journal et de deux JPEG synthétiques a été restaurée au
  même chemin isolé. Les références sont lisibles ; un second client ne peut ni
  voir ni supprimer les cas. Suppression par le propriétaire et expiration
  retirent les photos restaurées sans modifier l'original ni la sauvegarde.
- Quatre écritures audio simultanées du même conseil ne publient qu'un MP3 complet.
  Douze conseils concurrents convergent vers le budget souple après la fin des
  écritures et une passe de nettoyage. Aucun fragment temporaire ne subsiste.
- Chromium réel en mode sans interface : 320 px et 1280 px, message d'échec audio
  visible, texte conservé, aucun débordement horizontal ni erreur de page. Rapport
  et captures : `reports/browser_replay_check/`. Il s'agit d'un navigateur local,
  pas d'un téléphone physique ni d'une session avec participant.
- La suite complète a révélé une frontière de date : Casablanca était au lendemain
  tandis que le Burkina et le relevé météo étaient encore à la veille. Les fenêtres
  météo utilisent désormais la date portée par la réponse fournisseur, avec heure
  Burkina en repli. Une régression dédiée couvre ce passage de minuit.
- Restent ouverts : volume durable du fournisseur, cycle navigateur sur téléphone,
  validation terrain et approbation agronomique.
- Vérification finale de ce lot : 640 tests Python hors RAG réel et 27 tests
  JavaScript réussis ; un avertissement PyPDF2. Compilation des fichiers modifiés,
  export engrais inchangé et contrôle des différences réussis.

## Lot suivant — vérification des originaux du ticket 05 (12 septembre 2026)

- Les originaux IITA (67 pages) et ProSol (77 pages) ont été récupérés depuis la
  notice CGIAR et Inter-réseaux, contrôlés par empreinte, extraction page par page
  et rendu visuel des huit pages utiles.
- La matrice indique maintenant les pages PDF et imprimées. I1, I2 et I4 sont des
  paraphrases fidèles ; P1 est une synthèse interprétative ; I3 est une règle de
  prudence produit qui n'a pas été trouvée dans le texte IITA.
- L'URL IITA obsolète a été remplacée dans les métadonnées par la notice CGIAR et
  son flux PDF. Les empreintes des deux originaux ont été ajoutées aux synthèses.
- Les deux synthèses restent `reviewed_by_codex_pending_human_review`, donc hors
  RAG. Aucune dose, source ou cellule n'a été approuvée, et l'index n'a pas été
  reconstruit.

## Lot suivant — préparation accessibilité du ticket 08 (12 septembre 2026)

- Ajout d'un lien d'évitement et d'un repère principal, de noms distincts pour
  les sélecteurs sol/culture, et d'une indication explicite de l'état du journal.
- Les fenêtres Sources et Mes conseils contiennent désormais le focus clavier ;
  Échap les ferme et rend le focus au contrôle d'ouverture.
- Le parcours a été vérifié dans l'arbre d'accessibilité de Chromium. À 320 × 900
  pixels, aucun débordement horizontal n'est présent.
- Ce contrôle local ne constitue pas une réception du ticket 08 : lecteur d'écran
  système, vieux téléphone Android, permissions refusées et participants restent
  à tester.
- Vérification complète : 641 tests Python hors RAG réel et 27 tests JavaScript
  réussis ; un avertissement PyPDF2. Compilation des scripts navigateur et contrôle
  des différences réussis.
- Complément microphone : un refus navigateur conserve la question saisie,
  réactive le clavier et propose explicitement de taper la question. Les chemins
  MediaRecorder et reconnaissance vocale partagent ce message de reprise.

## Lot suivant — portes d'évaluation du ticket 09 (12 septembre 2026)

- Les feuilles de développement (40 cas) et réservées (20 cas) peuvent être
  générées séparément. La feuille réservée reste destinée à l'évaluation après gel
  des réglages.
- Un registre d'affirmations exige source, page, extrait court, décision et code de
  relecteur pour chaque affirmation. Le seuil de 90 % utilise les affirmations
  comme dénominateur.
- Un registre participant × tâche exige les cinq parcours pour au moins huit codes
  anonymes. Réussite autonome et compréhension utilisent ces observations comme
  dénominateur et doivent chacune atteindre 80 %.
- Un modèle de décision reste sur REPORTÉ tant que les preuves humaines,
  agronomiques et opérationnelles ne sont pas remplies.
- Vérification complète : 647 tests Python hors RAG réel et 29 tests JavaScript
  réussis ; un avertissement PyPDF2. Compilation du script et contrôle des
  différences réussis.
- Après le complément microphone : 647 tests Python hors RAG réel et 30 tests
  JavaScript réussis ; contrôle des différences réussi.
