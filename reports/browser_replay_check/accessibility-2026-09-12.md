# Contrôle local d'accessibilité — 12 septembre 2026

Contrôle réalisé sur la fixture locale, sans fournisseur externe ni données
utilisateur. Il prépare le ticket 08 ; il ne remplace pas les essais avec de
vrais téléphones, VoiceOver/TalkBack ou des participants.

## Parcours vérifié dans Chromium

- La première tabulation atteint « Aller à la conversation » ; Entrée place le
  focus sur le contenu principal.
- « Sources et limites » reçoit le rôle et le nom accessibles attendus. Le focus
  reste dans la fenêtre, Échap la ferme et rend le focus au bouton d'ouverture.
- « Mes conseils » expose son état ouvert/fermé. Le focus parcourt ses trois
  boutons en boucle, Échap ferme la fenêtre et rend le focus au bouton d'ouverture.
- Les sélecteurs « Sol + engrais » annoncent séparément culture et lieu.
- À 320 × 900 pixels, la largeur du document ne dépasse pas celle de la fenêtre.

## Limites restantes

- Pas de lecteur d'écran système ni de téléphone physique dans ce contrôle.
- Pas de permission microphone ou caméra.
- Pas d'évaluation humaine de l'ordre de lecture, de la compréhension des noms
  ou de la facilité d'utilisation.
