# Audit statique des textes visibles — 20 septembre 2026

Révision examinée : `666a726c` (application issue de la fusion de PR #16).
Périmètre : templates HTML, `static/js/index.js`, `api.js`, `render.js`,
service worker et erreurs HTTP associées. Recherche des libellés visibles,
placeholders, titres, attributs ARIA, appels text/html et branches d’erreur.
Commentaires, identifiants, journaux développeur et fixtures exclus.

## Résultats

| Catégorie | Résultat de la lecture statique |
|---|---|
| Fuite anglaise dans les libellés de l’interface | Aucun problème observé |
| Exception interne exposée par les parcours examinés | Aucun problème observé |
| Libellé d’accessibilité non traduit | Aucun problème observé |

Constats : `static/js/index.js:641` traduit les codes d’échec de dictée ;
`app.py:1536` renvoie une erreur vocale française stable ; `app.py:1792`
masque les erreurs de validation des sources. Les erreurs ValueError du journal
exposées aux routes sont précédées de validations HTTP et les erreurs attendues
restantes du module journal sont en français. Les chaînes anglaises console
restent des journaux développeur et ne sont pas des messages affichés.

Aucun constat de sévérité bloquante, majeure ou mineure dans ce périmètre.
Ce résultat ne certifie pas la langue des futures réponses du modèle, des titres
bibliographiques externes, des contenus saisis par les utilisateurs ou des
interfaces natives du navigateur. Le test humain de compréhension du vocabulaire
agronomique reste nécessaire. Aucun changement applicatif issu de cet audit.
