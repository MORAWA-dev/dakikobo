# Vérification live et reconstruction du corpus — 12 septembre 2026

Evidence record for K1. Every command below was executed from the repository
root on this machine; outputs are reproduced verbatim where quoted.

## Cible et environnement

- Cible live : `https://kimcomehome-dakikobo.hf.space` (Hugging Face Space, Docker).
- Machine : macOS, Python du virtualenv `.venv` (3.11), embeddings CPU
  `paraphrase-multilingual-MiniLM-L12-v2`.
- Aucun appel Groq/Gemini facturé n'a été déclenché localement ; les appels LLM
  ont lieu côté serveur pendant l'évaluateur live.

## Reconstruction du magasin vectoriel (corpus éligible)

Commande :

```bash
REBUILD_VECTORSTORE=true .venv/bin/python -c "import app; app._load_or_build_vector_store()"
```

Résultat (première reconstruction, avant l'ajout des métadonnées `scope`) :

```
1. Clearing existing vector store for a clean rebuild...
2. Loading reviewed Markdown from Data/markdown...
Found 2 Markdown file(s) in and under Data/markdown
  - scraped_reviewed/cilss_orientation_sahel_2026.md (ok)
  - scraped_reviewed/maerah_oaph_orientation_burkina_2026.md (ok)
3. Building & persisting vector store (2 Markdown docs + 0 web sources)...
DB: ok
ACTIVE_MANIFEST_HASH: 828d5d06eeb22bba
```

Seules les deux sources éligibles (`reviewed_by_owner`) sont indexées ; les
synthèses IITA/ProSol/FAO en attente de revue humaine sont exclues, comme prévu
par `core/source_policy.py`.

Identité du corpus reconstruit (manifeste) :

| Fichier | Taille | SHA-256 |
|---|---:|---|
| `Data/markdown/scraped_reviewed/cilss_orientation_sahel_2026.md` | 4220 | `6ef7c807a4afd08f038515fdfec1ed63e372c6c5c5ba5b2833ec46ecf94c9733` |
| `Data/markdown/scraped_reviewed/maerah_oaph_orientation_burkina_2026.md` | 9423 | `8355b0f6d6fb350d5976f6bd43f004233a3043911bc3f0d1b36509a96e14d7f6` |

Après l'ajout des métadonnées `scope` (K2), une seconde reconstruction a été
réalisée ; le hachage manifeste local final est consigné en bas de ce rapport
(les corps de texte indexés sont inchangés ; seules les métadonnées de
front-matter diffèrent).

## Garde du manifeste

Second chargement sans `REBUILD_VECTORSTORE` :

```
1. Loading existing vector store (set REBUILD_VECTORSTORE=true to rebuild)...
1. Loaded existing vector store with 36 chunks.
DB: ok
ACTIVE_MANIFEST_HASH: 828d5d06eeb22bba
```

Le magasin persisté est accepté quand le manifeste correspond ; le rejet d'un
manifeste périmé est couvert par
`tests/test_ingestion.py::test_stale_vector_store_manifest_is_rejected`.

## Identité du corpus réellement servi

En-têtes d'une réponse live `POST /ask` (question engrais sorgho, 12 septembre) :

```
HTTP/2 200
x-dakikobo-cacheable: 0
x-dakikobo-corpus: 828d5d06eeb22bba
```

Le corpus servi par le Space correspond donc déjà au corpus à deux sources
éligibles — le hachage live est identique à la reconstruction locale.
`/healthz` : `ok=true`, `rag_status=ready` (warm-up terminé 2026-09-08).
`/version` : commit déployé `bc0670e35d85d199d13f33dcd7b1a27ad9a5ddce`,
`answer_cache_enabled=true`, modèle `openai/gpt-oss-120b`.

## Vérification TTS complète

La même réponse `/ask` a retourné `audio_url: /static/audio/m9k4ctqisv9y8dl.mp3`.
Téléchargement live de l'audio :

```
http=200 bytes=174336 type=audio/mpeg
file: MPEG ADTS, layer III, v2, 64 kbps, 24 kHz, Monaural
```

Un fichier MP3 valide et non vide a bien été servi.

## Évaluateur RAG live

Commande :

```bash
.venv/bin/python scripts/evaluate_rag.py \
  --base-url https://kimcomehome-dakikobo.hf.space \
  --output reports/rag_eval_results.md
```

Résultat : **14/14 cas hard-pass (100 %, seuil 75 %)**, 3 avertissements
consultatifs (`source_terms`/`confidence`). Détail : `reports/rag_eval_results.md`
(régénéré à cette date). Les avertissements correspondent au comportement
attendu d'un corpus aminci : moins de citations IITA, confiance parfois « Faible »
ou « Moyen » — c'est la dégradation honnête voulue, pas une régression.

## Échecs et limitations

- Le test RAG crédentiel local (`tests/test_rag.py`) n'a pas été exécuté dans
  cette passe ; la vérification LLM repose sur l'évaluateur live ci-dessus.
- La reconstruction locale a été faite sur CPU ; elle n'est pas une mesure de
  performance du matériel hébergé.
- Les contrôles navigateur existants sont du Chromium sans interface local,
  pas un téléphone physique (voir `evaluation/PILOT_REHEARSAL_CHECKLIST_2026-09-12.md`).
- Après les changements de métadonnées K2, le hachage du corpus local final est
  `11391cefa86f9f32` (voir sortie de reconstruction ci-dessous) ; le
  Space servira l'ancien hachage jusqu'au prochain déploiement avec warm-up —
  différence attendue, limitée aux métadonnées (corps de texte identiques).

## Reconstruction finale après K2

```
2. Loading reviewed Markdown from Data/markdown...
  - scraped_reviewed/cilss_orientation_sahel_2026.md (ok)
  - scraped_reviewed/maerah_oaph_orientation_burkina_2026.md (ok)
3. Building & persisting vector store (2 Markdown docs + 0 web sources)...
DB: ok
ACTIVE_MANIFEST_HASH: 11391cefa86f9f32
cilss_orientation_sahel_2026.md sha256: 881bebe13573…
maerah_oaph_orientation_burkina_2026.md sha256: dcc8c6d377ea…
```

## Vérification sur la tête de branche déployée (seconde passe, 12 septembre)

Le Space a été redéployé sur la tête courante de la branche PR
(commit de déploiement `a2798eb39a24316a55448afc0f04951ac28e2885`).
Le delta entre l'arbre déployé et la tête de branche finale (`36cfb185`)
est limité à des fichiers de documentation/preuve (`reports/`, `plans/`,
`PROJECT_STATE.md`), au chemin de sortie par défaut de
`scripts/audit_source_eligibility.py` et à la correction du comptage dans
`Data/reviews/AGRONOMIST_REVIEW_PACKET_2026-09-12.md` — aucun changement de
comportement d'exécution de l'application.

Vérifications rejouées contre `https://kimcomehome-dakikobo.hf.space` :

- `GET /healthz` : `ok=true`, `rag_status=ready` (warm-up terminé
  2026-09-12T19:23:28+00:00).
- `GET /version` : commit `a2798eb39a24316a55448afc0f04951ac28e2885`,
  modèle `openai/gpt-oss-120b`, `answer_cache_enabled=true`.
- `POST /ask` (« Quel engrais pour le sorgho ? ») : `HTTP 200`, en-tête
  `x-dakikobo-corpus: 11391cefa86f9f32` — le corpus servi correspond au
  hachage local post-K2.
- TTS complet : `audio_url: /static/audio/tts_a7740bcefc6710903e37692458eca4e3.mp3`,
  téléchargé à 174336 octets, `file` : MPEG ADTS, layer III, 64 kbps.
- Évaluateur RAG live : **14/14 hard-pass (100 %, seuil 75 %)**, 3
  avertissements consultatifs. Rapport régénéré :
  `reports/rag_eval_results.md` (horodaté 2026-09-12T19:25:56+00:00).
