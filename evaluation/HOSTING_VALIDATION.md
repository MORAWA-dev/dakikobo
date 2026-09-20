# Vérification de l’hébergement — procédure opérateur

État initial : **hosting pending**. Cette procédure prépare K3 ; elle ne
certifie aucun volume ni aucun redémarrage chez un hébergeur. La démo peut
être mise à jour sans que la décision de livraison terrain soit approuvée.

## Préparation sans modifier le service

Choisir la cible autorisée, son commit et un opérateur. Ne jamais enregistrer
question, réponse, photo, audio, cookie, jeton ou secret dans la preuve.
Consigner seulement les booléens, codes HTTP, références de version, date UTC
et identifiant non sensible du volume. Ne pas exporter les paramètres secrets.

1. Vérifier `/healthz` (`ok`, `rag_status=ready`) et `/version` ; comparer le
   commit à celui du déploiement HF, distinct du commit GitHub.
2. Vérifier sur HTTPS les en-têtes CSP, HSTS, X-Content-Type-Options et
   X-Frame-Options, puis les refus 403/404 pour `/.env`, `/.git/config`,
   `/config.py`, `/data/case_log.sqlite3` et `/data/feedback_images/`.
3. Dans le panneau de l’hébergeur, vérifier un vrai volume durable, sa politique
   de remplacement/reconstruction et son montage hors des fichiers publics.
   Vérifier `CASE_LOG_DB_PATH`, `STATE_DB_PATH`, `FEEDBACK_IMAGE_DIR` et la
   stabilité de `FLASK_SECRET_KEY` sans consigner sa valeur. Un disque de
   conteneur, un redémarrage réussi ou `/healthz` ne prouve pas la durabilité.
4. Préparer une instance isolée sur le même type de volume. Utiliser uniquement
   un conseil synthétique consenti et une photo synthétique, deux navigateurs
   distincts (propriétaire et autre utilisateur), et les limites de rétention
   de la configuration cible. Ne jamais réduire ces limites sur la cible réelle.

## Répétition locale automatisée (preuve distincte)

Depuis la racine du dépôt, avec les dépendances et Docker installés :

```sh
.venv/bin/python -m pytest -q tests/test_recovery.py tests/test_docker_journal_rehearsal.py
.venv/bin/python tests/docker_journal_rehearsal.py
```

La seconde commande crée et nettoie uniquement ses propres conteneurs et
fixtures. Ne pas utiliser `--skip-if-no-docker` comme preuve de réussite.
Le workflow [Docker journal](../.github/workflows/docker-journal-rehearsal.yml)
fournit également une preuve locale automatisée ; aucune ne remplace les
étapes hébergeur ci-dessous. Aucun changement de source n’est nécessaire.

## Exécution sur une instance de validation de l’hébergeur

Suivre [sauvegarde et restauration](../DEPLOYMENT.md#consistent-backup).
Suspendre les écritures pendant une sauvegarde cohérente SQLite et photos.
Conserver cette sauvegarde hors des chemins servis, avec rétention et accès
privés. Garder une sauvegarde de retour arrière distincte avant chaque opération.

| Étape | Vérification requise | UTC | Révision cible | Résultat pass/fail | Référence de preuve non sensible |
|---|---|---|---|---|---|
| Prévol | Volume, chemins privés, secret stable, santé, version, en-têtes | | | | |
| Création | Conseil et photo synthétiques visibles uniquement du propriétaire | | | | |
| Remplacement du conteneur | Même navigateur propriétaire retrouve conseil, sources et photo ; autre navigateur refusé | | | | |
| Reconstruction par l’hébergeur | Même contrôle après reconstruction effective de l’instance de validation | | | | |
| Sauvegarde | SQLite integrity_check et cohérence des références de photos | | | | |
| Restauration isolée | Même chemin absolu, même secret ; propriétaire accepté, autre navigateur refusé | | | | |
| Suppression et expiration | Conseil et photo supprimés ; rétention contrôlée dans la fixture isolée | | | | |
| Retour arrière | Révision et sauvegarde précédentes restaurées ; santé et propriété revérifiées | | | | |

Si une étape échoue, arrêter la validation, garder la cible de validation fermée
aux écritures et appliquer le retour arrière documenté. Ne pas recopier la
sauvegarde isolée sur le service réel. Une preuve manquante ou un échec de
persistance, propriété, en-têtes ou chemin privé maintient **REPORTÉE** dans la
[décision de livraison](RELEASE_DECISION_TEMPLATE.md). Les cases restent vides
jusqu’à l’exécution réelle. Responsable et date de décision : à renseigner.
