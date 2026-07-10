# Data collection tasks (for you later)

Use this checklist when you have time to search online and ask people.  
You do **not** need to finish everything at once. Each track is independent.

When something is ready, drop files in the paths below (or paste links/lists in chat) and ask:

```text
@SESSION.md @Data/reviews/DATA_COLLECTION_TASKS.md ingest what I collected
```

---

## How to use this file

1. Pick **one track** (A, B, or C).
2. Collect items into the **inbox** folder or a short note.
3. Tick boxes as you go.
4. When a track is “good enough”, note the date and tell the agent to process it.

**Inbox (create as needed):** `Data/reviews/inbox/`  
Put downloads, PDFs, CSV exports, or a `NOTES.md` with URLs and who you asked.

Do **not** put API keys or private personal data (full names of farmers, phone numbers, faces if avoidable).

---

## Track A — Climate & research sources (WASCAL / INERA / AGRHYMET)

**Goal:** Official or trusted documents for Sahel climate / Burkinabè research so DakiKobo can cite them (after review).  
**Why blocked before:** Sites often unreachable from our network.

### A1. Online search (you)

- [ ] Try opening (bookmark if OK):
  - [ ] https://www.inera.bf/
  - [ ] https://www.wascal.org/ or https://wascal.org/
  - [ ] https://www.agrhymet.ne/
  - [ ] CILSS / AGRHYMET reports on Google / institutional pages
- [ ] Download **2–10** useful PDFs or save stable public URLs  
  Prefer: rainfall / agro-meteo bulletins, crop calendars, INERA factsheets for mil / sorgho / maïs / niébé / arachide
- [ ] For each file, write one line in `Data/reviews/inbox/SOURCE_NOTES.md`:

```text
- title: ...
  url: ...
  publisher: ...
  year: ...
  why useful: ...
  crops: ...
```

### A2. Ask people

- [ ] Extension agent / INERA contact / student: “Where do you get official climate or crop tech sheets for Burkina?”
- [ ] Ask for **public** PDFs or links only (not confidential project docs unless they confirm reuse is OK)

### A3. Done when

- [ ] At least **3** sources with title + URL/publisher + why useful  
- [ ] Files or links in inbox  
- [ ] Note: “Track A ready for agent review” in SESSION or a chat message  

**Agent will then:** review → curated Markdown (no auto-promote of raw dumps) → optional RAG.

---

## Track B — Leaf phone photos (vision lab)

**Goal:** Private evaluation set so we can compare Gemini vs experimental models.  
**Not** for public training without consent.

### B1. Photos (you or partners)

- [ ] Collect **20–50** photos (more is better, 10 is already useful)
- [ ] Mix of crops if possible: mil, sorgho, maïs, niébé, arachide
- [ ] Include hard cases:
  - [ ] a few **blurry** photos
  - [ ] a few **not a plant** (soil, sky, tool, random object)
  - [ ] healthy leaves if available
  - [ ] leaves with spots / damage if available
- [ ] Prefer daylight, leaf filling most of the frame
- [ ] Avoid faces and ID documents

**Where to put files:** `Data/vision_eval/samples/`  
(large/private samples stay local; do not commit private farmer photos without consent)

### B2. Labels (you or someone who saw the plant)

Copy template: `Data/vision_eval/manifest_template.csv`  
→ e.g. `Data/reviews/inbox/vision_manifest.csv` or `reports/vision_eval_manifest.csv`

For each photo, set `gold_label` to **one** of:

| Label | Meaning |
|--------|---------|
| `healthy` | Looks healthy |
| `disease_suspected` | Disease possible (not a diagnosis) |
| `pest_damage` | Insect / pest damage possible |
| `blurry` | Too blurry to judge |
| `not_a_plant` | Not a crop leaf |
| `unknown` | You really cannot say |

Example row:

```csv
phone_001,Data/vision_eval/samples/phone_001.jpg,mais,disease_suspected,taches jaunes,phone_photo,eval
```

### B3. Consent note

- [ ] Write 2–3 sentences in `Data/reviews/inbox/PHOTO_CONSENT.md`:
  - Who took/shared the photos
  - OK for **private DakiKobo evaluation** (yes/no)
  - OK for **public training / open dataset** (yes/no — default **no**)

### B4. Done when

- [ ] ≥10 labelled photos (or ≥20 for a real comparison)
- [ ] Manifest CSV complete
- [ ] Consent note present  

**Agent will then:** wire Colab notebooks 01/03/04, run metrics, keep Gemini in production until gates pass.

---

## Track C — Local crop names (labels only)

**Goal:** Mooré / Dioula / Fulfulde **names for crop selectors** — not full translation of answers.  
**Rule:** Do not invent spellings; only fill after someone who speaks the language confirms.

File to edit later: `Data/glossaries/crop_labels.json`

| Crop id | French | Mooré | Dioula | Fulfulde | Who confirmed |
|---------|--------|-------|--------|----------|---------------|
| mil | Mil | | | | |
| sorgho | Sorgho | | | | |
| mais | Maïs | | | | |
| niebe | Niébé | | | | |
| arachide | Arachide | | | | |

### C1. Ask people

- [ ] 1+ speaker or extension agent for **Mooré**
- [ ] 1+ for **Dioula** (if you need it)
- [ ] 1+ for **Fulfulde** (if you need it)
- [ ] Prefer names used with **farmers**, not only textbook

### C2. Write answers

- [ ] Fill the table above (or edit `crop_labels.json` fields `moore` / `dioula` / `fulfulde`)
- [ ] Note validator name/role + date in `Data/reviews/inbox/CROP_NAMES_NOTES.md`

### C3. Done when

- [ ] At least **one** language fully filled for the 5 crops  
- [ ] Validator noted  

**Agent will then:** update glossary JSON, optional UI labels only (still **no** answer generation in local languages until you ask for that separately).

---

## Quick “minimum viable” packs

If time is short, aim for **one** of these:

| Pack | Minimum |
|------|---------|
| **A quick** | 3 public PDFs/URLs with notes |
| **B quick** | 10 labelled photos + consent “private eval only” |
| **C quick** | 5 Mooré crop names + who confirmed |

---

## Status log (tick when you finish a track)

| Track | Started | Ready for agent | Notes |
|-------|---------|-----------------|-------|
| A Climate / research | | | |
| B Leaf photos | | | |
| C Crop names | | | |

---

## Related files

| Path | Role |
|------|------|
| `Data/reviews/OWNER_SIGNOFF.md` | MAERAH/CILSS already signed (morawa-dev) |
| `Data/reviews/SOURCE_VERIFICATION_AUDIT_2026-07-10.md` | Agent verification record |
| `Data/vision_eval/manifest_template.csv` | Photo label template |
| `Data/glossaries/crop_labels.json` | Crop names (local slots empty) |
| `SESSION.md` | Session continuity for the agent |
