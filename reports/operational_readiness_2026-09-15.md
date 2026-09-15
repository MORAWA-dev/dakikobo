# Réception opérationnelle — 15 septembre 2026

## Résultat

Le ticket 07 reste **PARTIEL**. La reprise applicative par HTTP est vérifiée
localement ; la durabilité du stockage de l'hébergeur reste non démontrée.
Aucune donnée utilisateur ni opération de redémarrage distant n'a été utilisée.

## Reprise locale avec données synthétiques

Commande : `.venv/bin/python -m pytest -q tests/test_recovery.py`.
Résultat : **3 réussis**, un avertissement PyPDF2, 25,88 secondes.

Le nouveau parcours utilise un vrai serveur Werkzeug sur une adresse loopback
et un client HTTP conservant son cookie : sauvegarde consentie, arrêt du serveur,
nouveau processus, accès propriétaire, exclusion d'un autre client, sauvegarde
SQLite après arrêt des écritures, restauration isolée et suppression propriétaire.
La tentative de suppression d'un autre client retourne `deleted: 0` et laisse le
cas intact. Le journal original reste inchangé après les essais sur la copie.
Les tests existants couvrent également expiration et restauration des photos.

Limites : serveur de test local, sans Gunicorn ni proxy, sans TLS ni navigateur
physique. Le cookie Secure est désactivé exclusivement dans ce serveur loopback
de test. Aucun secret, chemin ou journal actif du développeur n'est employé.

## Vérification distante en lecture seule

Cible : `https://kimcomehome-dakikobo.hf.space`.

- API runtime Hugging Face : RUNNING, cpu-basic, une réplique ; commit
  `a2798eb39a24316a55448afc0f04951ac28e2885`. La réponse publique ne fournit
  aucune preuve de volume durable.
- `HEAD /confidentialite` : HTTP 200 ; CSP limitée à l'origine locale,
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, politique
  `no-referrer`, restrictions caméra/microphone et HSTS présents.
- `GET /data/case_log.sqlite3` : HTTP 404 ; aucun contenu de base téléchargé.

Un refus sur ce chemin ne prouve pas l'absence universelle de chemins privés
exposés. Ces vérifications ne remplacent pas une inspection du montage réel.

## Preuves restantes pour réceptionner le ticket 07

1. Confirmer dans l'environnement d'exploitation que les deux bases SQLite et
   les photos pointent vers le volume durable privé décrit dans DEPLOYMENT.
2. Confirmer que FLASK_SECRET_KEY est fourni par le gestionnaire de secrets et
   reste stable, sans copier ni enregistrer sa valeur dans les preuves.
3. Sur une cible de test isolée, enregistrer un cas synthétique consenti et
   vérifier son accès avec le même navigateur après redémarrage, puis rebuild.
4. Vérifier qu'un second navigateur ne peut ni lire ni supprimer ce cas ;
   répéter restauration, suppression et expiration avec la sauvegarde privée.
5. Consigner le type de volume, les limites, les dates, le commit et le résultat
   dans un compte rendu expurgé. Ne pas joindre cookies, photos ou bases.

La revue agronomique (02/05), les parcours physiques (03/08) et la décision
humaine de livraison (09) restent requis. Le ticket 10 demeure conditionnel.
