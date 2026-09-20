"""Tests for the offline release-decision scaffold generator (K2, Ticket 09).

These prove the generator is deterministic, records the reproducible build
identity from repository state, lists every unresolved human/operational gate as
pending, and fails closed to REPORTÉE without inventing any human evidence.
"""
import re

import config
from core.answer_safety import safety_policy_revision
from scripts.farmer_evaluation import (
    EVALUATION_DIR,
    LIVE_EVALUATION_COMMAND,
    _corpus_identity,
    generate_release_decision,
    release_decision_scaffold,
)

FIXED_COMMIT = '0123456789abcdef0123456789abcdef01234567'
FIXED_DATE = '2026-09-18'

# Declared inputs of the committed scaffold artifact (see the module docstring
# of scripts.farmer_evaluation and SESSION.md for the exact regen command).
COMMITTED_SCAFFOLD = EVALUATION_DIR / 'RELEASE_DECISION_SCAFFOLD_2026-09-17.md'
COMMITTED_COMMIT = 'a41c842d6febbdf38d1cf771875ed59102094a2b'
COMMITTED_DATE = '2026-09-17'


def _fixed_body():
    return release_decision_scaffold(
        commit=FIXED_COMMIT,
        generated_on=FIXED_DATE,
        corpus=_corpus_identity(),
        models={
            'llm': config.LLM_MODEL,
            'vision': config.GEMINI_MODEL,
            'embedding': config.EMBEDDING_MODEL,
        },
        policy_revision=safety_policy_revision(),
    )


# --- (a) writes a dated file ----------------------------------------------


def test_generate_writes_dated_file(tmp_path):
    out = tmp_path / f'RELEASE_DECISION_SCAFFOLD_{FIXED_DATE}.md'
    path = generate_release_decision(str(out), commit=FIXED_COMMIT, generated_on=FIXED_DATE)
    assert path == out
    assert path.is_file()
    assert FIXED_DATE in path.name


def test_bare_date_target_uses_dated_convention(tmp_path):
    # A bare date routes to the injected output dir with the dated naming
    # convention. Writing under tmp_path keeps the real evaluation/ tree untouched.
    path = generate_release_decision(FIXED_DATE, commit=FIXED_COMMIT, output_dir=tmp_path)
    assert path.name == f'RELEASE_DECISION_SCAFFOLD_{FIXED_DATE}.md'
    assert path.parent == tmp_path
    assert path.is_file()


# --- (a') reproducible parity with the committed artifact ------------------


def test_regenerates_committed_scaffold_byte_for_byte(tmp_path):
    # Regenerate the checked-in artifact from its DECLARED inputs into tmp_path
    # and assert exact-byte equality against the committed file. This proves the
    # documented regen command reproduces the artifact byte-for-byte.
    committed_bytes = COMMITTED_SCAFFOLD.read_bytes()
    generated = generate_release_decision(
        COMMITTED_DATE,
        commit=COMMITTED_COMMIT,
        generated_on=COMMITTED_DATE,
        output_dir=tmp_path,
    )
    assert generated.parent == tmp_path
    assert generated.name == 'RELEASE_DECISION_SCAFFOLD_2026-09-17.md'
    assert generated.read_bytes() == committed_bytes


def test_generation_never_touches_committed_artifact(tmp_path):
    # Protection: a generation run directed at an injected output dir must not
    # overwrite or delete the committed scaffold on disk.
    before = COMMITTED_SCAFFOLD.read_bytes()
    generate_release_decision(
        COMMITTED_DATE,
        commit=FIXED_COMMIT,
        generated_on=COMMITTED_DATE,
        output_dir=tmp_path,
    )
    generate_release_decision(FIXED_DATE, commit=FIXED_COMMIT, output_dir=tmp_path)
    assert COMMITTED_SCAFFOLD.is_file()
    assert COMMITTED_SCAFFOLD.read_bytes() == before


# --- (b) reproducible identity fields -------------------------------------


def test_body_records_commit_corpus_models_and_policy():
    body = _fixed_body()
    corpus = _corpus_identity()
    assert FIXED_COMMIT in body
    assert corpus['manifest_hash'] in body
    assert str(corpus['file_count']) in body
    assert config.LLM_MODEL in body
    assert config.GEMINI_MODEL in body
    assert config.EMBEDDING_MODEL in body
    assert safety_policy_revision() in body


# --- (c) fail-closed REPORTÉE decision ------------------------------------


def test_decision_defaults_to_reportee():
    body = _fixed_body()
    assert 'REPORTÉE' in body
    # The REPORTER box is checked; LIVRER and RÉDUIRE stay unchecked.
    assert '[x] REPORTER' in body
    assert '[ ] LIVRER' in body
    assert '[ ] RÉDUIRE LE PÉRIMÈTRE' in body
    # Every gate result column stays "À mesurer".
    assert body.count('À mesurer') == 4


# --- (d) no fabricated human data; every gate pending ----------------------


def test_every_human_and_operational_gate_is_pending():
    body = _fixed_body()
    for heading in (
        'Revue agronomique',
        'Répétition sur téléphone physique',
        'Observations des participants',
        'Évaluation du modèle en direct',
        "Vérification de l'hébergement",
    ):
        assert heading in body, heading
    # Five "en attente" states (one per gate) confirm nothing was resolved.
    assert body.count('en attente') >= 5


def test_human_fields_stay_blank_with_no_invented_data():
    body = _fixed_body()
    # Reviewer/participant/date/result fields are rendered as blank underscores.
    assert 'Relecteur : ＿' in body
    assert 'Codes anonymes des participants : ＿' in body
    assert 'Responsable de la décision : ＿' in body
    # No fabricated calendar dates outside the injected generation date, the
    # policy-revision date (repository state), and the legitimate references to
    # dated checklist artifacts.
    policy_date = safety_policy_revision().split('.')[0].removeprefix('safety-')
    dates = set(re.findall(r'\d{4}-\d{2}-\d{2}', body))
    assert dates <= {FIXED_DATE, '2026-09-12', policy_date}


# --- (e) live command documented, not executed, no credentials -------------


def test_live_command_documented_without_credentials_and_not_run():
    body = _fixed_body()
    assert LIVE_EVALUATION_COMMAND in body
    assert 'scripts/evaluate_rag.py' in LIVE_EVALUATION_COMMAND
    assert '--strict' in LIVE_EVALUATION_COMMAND
    # No secrets embedded in the command or body.
    assert 'GROQ' not in body
    assert 'API_KEY' not in body
    # Explicitly states it was not executed and that secrets come from the env.
    assert "n'a PAS été exécutée" in body
    assert 'environnement du processus' in body


# --- (f) determinism -------------------------------------------------------


def test_body_is_deterministic_for_fixed_inputs():
    assert _fixed_body() == _fixed_body()


def test_generate_is_deterministic_across_two_writes(tmp_path):
    first = generate_release_decision(
        str(tmp_path / 'first.md'), commit=FIXED_COMMIT, generated_on=FIXED_DATE
    )
    second = generate_release_decision(
        str(tmp_path / 'second.md'), commit=FIXED_COMMIT, generated_on=FIXED_DATE
    )
    assert first.read_text(encoding='utf-8') == second.read_text(encoding='utf-8')
