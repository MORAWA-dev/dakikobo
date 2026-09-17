import csv
import json
from scripts.farmer_evaluation import (
    BENCHMARK,
    assess,
    assess_claims,
    assess_tasks,
    prepare,
    prepare_claims,
    prepare_tasks,
)


def test_blank_or_missing_scorecards_cannot_pass(tmp_path):
    data=json.loads(BENCHMARK.read_text())
    assert len(data['cases']) == 60
    assert sum(c['split']=='held_out' for c in data['cases']) == 20
    path=tmp_path/'scores.csv'
    prepare(path)
    assert not assess(path)[0]


def test_development_and_held_out_scorecards_stay_separate(tmp_path):
    development = tmp_path / 'development.csv'
    held_out = tmp_path / 'held-out.csv'
    prepare(development, split='development')
    prepare(held_out, split='held_out')
    with development.open() as handle:
        dev_rows = list(csv.DictReader(handle))
    with held_out.open() as handle:
        held_rows = list(csv.DictReader(handle))
    assert len(dev_rows) == 40
    assert {row['split'] for row in dev_rows} == {'development'}
    assert len(held_rows) == 20
    assert {row['split'] for row in held_rows} == {'held_out'}


def test_critical_failure_blocks_even_with_high_average(tmp_path):
    path=tmp_path/'scores.csv'; prepare(path)
    with path.open() as handle:
        reader=csv.DictReader(handle); fields=reader.fieldnames; rows=list(reader)
    for row in rows:
        for key in ('safety_pass','grounding_pass','task_success','understood_next_action'):
            row[key]='yes'
        row['reviewer']='test-fixture-only'
    next(row for row in rows if row['critical']=='yes')['safety_pass']='no'
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    assert not assess(path)[0]


def test_claim_ledger_uses_claims_as_grounding_denominator(tmp_path):
    path = tmp_path / 'claims.csv'
    prepare_claims(path)
    with path.open() as handle:
        fields = csv.DictReader(handle).fieldnames
    rows = []
    for index in range(10):
        rows.append({
            'case_id': 'agronomy_01',
            'split': 'development',
            'claim_id': f'claim-{index + 1}',
            'claim_text': f'Affirmation {index + 1}',
            'source': 'Guide contrôlé',
            'page': 'PDF 12 (p. 6)',
            'excerpt': 'Court extrait de preuve',
            'supported': 'no' if index == 0 else 'yes',
            'reviewer': 'expert-fixture',
            'notes': '',
        })
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    passed, summary = assess_claims(path)
    assert passed
    assert '9/10' in summary
    rows[1]['supported'] = 'no'
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    assert not assess_claims(path)[0]


def test_claim_ledger_rejects_unknown_or_incomplete_evidence(tmp_path):
    path = tmp_path / 'claims.csv'
    prepare_claims(path)
    with path.open() as handle:
        fields = csv.DictReader(handle).fieldnames
    row = {field: 'value' for field in fields}
    row.update(case_id='unknown_case', split='development', supported='yes')
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)
    assert not assess_claims(path)[0]


def test_participant_task_ledger_requires_five_tasks_for_eight_participants(tmp_path):
    path = tmp_path / 'tasks.csv'
    prepare_tasks(path)
    with path.open() as handle:
        fields = csv.DictReader(handle).fieldnames
    rows = []
    for participant in range(1, 9):
        for task_id in ('sowing', 'crop_problem', 'fertilizer', 'offline', 'saved_case'):
            rows.append({
                'participant_code': f'P{participant:02}',
                'task_id': task_id,
                'device': 'Android test',
                'network': 'faible',
                'completed_independently': 'yes',
                'understood_next_action': 'yes',
                'help_needed': 'no',
                'observer': 'observer-fixture',
                'notes': '',
            })
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    passed, summary = assess_tasks(path)
    assert passed
    assert '40/40' in summary
    rows.pop()
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    assert not assess_tasks(path)[0]


# ---------------------------------------------------------------------------
# Ticket 09 reproducibility coverage (K2): missing evidence, duplicate
# identifiers, denominators, exact threshold boundaries, fail-closed release.
# Each test exercises real screening logic and would fail if the corresponding
# guarantee in scripts/farmer_evaluation.py were reverted.
# ---------------------------------------------------------------------------


def _write_rows(path, rows):
    """Write rows to a CSV, deriving the header from the blank ledger already at path."""
    with path.open(encoding='utf-8', newline='') as handle:
        fields = csv.DictReader(handle).fieldnames
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _claim_row(claim_id, supported='yes', **overrides):
    row = {
        'case_id': 'agronomy_01',
        'split': 'development',
        'claim_id': claim_id,
        'claim_text': f'Affirmation {claim_id}',
        'source': 'Guide contrôlé',
        'page': 'PDF 12 (p. 6)',
        'excerpt': 'Court extrait de preuve',
        'supported': supported,
        'reviewer': 'expert-fixture',
        'notes': '',
    }
    row.update(overrides)
    return row


def _claim_rows(supported_count, total):
    """Return ``total`` claim rows of which ``supported_count`` are marked supported=yes."""
    rows = []
    for index in range(total):
        supported = 'yes' if index < supported_count else 'no'
        rows.append(_claim_row(f'claim-{index + 1}', supported=supported))
    return rows


# Real case ids per split from evaluation/farmer_benchmark.json.
_DEV_CASE_ID = 'agronomy_01'
_HELD_OUT_CASE_ID = 'agronomy_03'


def _split_claim_rows(case_id, split, supported_count, total):
    """Return claim rows tied to a real ``case_id`` in ``split``.

    ``supported_count`` of ``total`` rows are marked supported=yes.
    """
    rows = []
    for index in range(total):
        supported = 'yes' if index < supported_count else 'no'
        rows.append(_claim_row(
            f'{case_id}-claim-{index + 1}',
            supported=supported,
            case_id=case_id,
            split=split,
        ))
    return rows


def _task_row(participant, task_id, completed='yes', understood='yes', **overrides):
    row = {
        'participant_code': participant,
        'task_id': task_id,
        'device': 'Android test',
        'network': 'faible',
        'completed_independently': completed,
        'understood_next_action': understood,
        'help_needed': 'no',
        'observer': 'observer-fixture',
        'notes': '',
    }
    row.update(overrides)
    return row


def _task_rows(completed_count, understood_count, participants=8):
    """Return participant x task rows (participants x 5 tasks).

    Exactly ``completed_count`` rows are marked completed_independently=yes and
    exactly ``understood_count`` rows are marked understood_next_action=yes.
    """
    rows = []
    for p in range(1, participants + 1):
        for task_id in ('sowing', 'crop_problem', 'fertilizer', 'offline', 'saved_case'):
            rows.append(_task_row(f'P{p:02}', task_id, completed='no', understood='no'))
    for index in range(completed_count):
        rows[index]['completed_independently'] = 'yes'
    for index in range(understood_count):
        rows[index]['understood_next_action'] = 'yes'
    return rows


# --- Category 1: missing evidence -----------------------------------------


def test_empty_ledgers_and_scorecard_fail_closed(tmp_path):
    scores = tmp_path / 'scores.csv'
    claims = tmp_path / 'claims.csv'
    tasks = tmp_path / 'tasks.csv'
    prepare(scores)
    prepare_claims(claims)
    prepare_tasks(tasks)
    # Blank scorecard has full case list but no scores; empty ledgers have only a header.
    assert assess(scores)[0] is False
    assert assess_claims(claims)[0] is False
    assert assess_tasks(tasks)[0] is False


def test_claim_row_missing_evidence_fields_fails(tmp_path):
    path = tmp_path / 'claims.csv'
    prepare_claims(path)
    for missing in ('source', 'page', 'excerpt', 'reviewer'):
        rows = _claim_rows(9, 10)
        rows[0][missing] = ''
        _write_rows(path, rows)
        passed, summary = assess_claims(path)
        assert passed is False, f'blank {missing} must fail closed'
        assert 'Incomplete claim evidence' in summary


def test_task_row_missing_evidence_fields_fails(tmp_path):
    path = tmp_path / 'tasks.csv'
    prepare_tasks(path)
    rows = _task_rows(40, 40)
    rows[0]['observer'] = ''
    _write_rows(path, rows)
    passed, summary = assess_tasks(path)
    assert passed is False
    assert 'Incomplete participant task evidence' in summary


# --- Category 2: duplicate identifiers ------------------------------------


def test_scorecard_rejects_duplicate_case_ids(tmp_path):
    path = tmp_path / 'scores.csv'
    prepare(path, split='development')
    with path.open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key in ('safety_pass', 'grounding_pass', 'task_success', 'understood_next_action'):
            row[key] = 'yes'
        row['reviewer'] = 'test-fixture-only'
    # Duplicate the first case id over the second row: count stays 40 but ids collide.
    rows[1]['id'] = rows[0]['id']
    _write_rows(path, rows)
    passed, summary = assess(path)
    assert passed is False
    assert 'Incomplete or duplicate case identifiers.' == summary


def test_claim_ledger_rejects_duplicate_case_claim_pairs(tmp_path):
    path = tmp_path / 'claims.csv'
    prepare_claims(path)
    rows = _claim_rows(10, 10)
    rows[1]['claim_id'] = rows[0]['claim_id']  # duplicate (case_id, claim_id)
    _write_rows(path, rows)
    passed, summary = assess_claims(path)
    assert passed is False
    assert 'Duplicate claim identifiers.' == summary


def test_task_ledger_rejects_duplicate_participant_task_pairs(tmp_path):
    path = tmp_path / 'tasks.csv'
    prepare_tasks(path)
    rows = _task_rows(40, 40)
    # Force a duplicate (participant_code, task_id): copy row 0 identity onto row 1.
    rows[1]['participant_code'] = rows[0]['participant_code']
    rows[1]['task_id'] = rows[0]['task_id']
    _write_rows(path, rows)
    passed, summary = assess_tasks(path)
    assert passed is False
    assert 'Duplicate participant/task identifiers.' == summary


# --- Category 3: denominator calculations ---------------------------------


def test_claim_grounding_denominator_is_claim_row_count(tmp_path):
    path = tmp_path / 'claims.csv'
    prepare_claims(path)
    _write_rows(path, _claim_rows(9, 10))
    passed, summary = assess_claims(path)
    assert passed is True
    assert '9/10' in summary
    assert '(90%)' in summary
    assert 'substantive claims reviewed' in summary


def test_pilot_denominator_is_participant_times_task_observations(tmp_path):
    path = tmp_path / 'tasks.csv'
    prepare_tasks(path)
    _write_rows(path, _task_rows(40, 40))
    passed, summary = assess_tasks(path)
    assert passed is True
    # 8 participants x 5 tasks = 40 observations, not 8 participants.
    assert '40/40' in summary
    assert 'participant/task observations across 8 participants' in summary


# --- Category 4: exact threshold boundaries -------------------------------


def test_claim_grounding_exact_ninety_percent_passes(tmp_path):
    path = tmp_path / 'claims.csv'
    prepare_claims(path)
    _write_rows(path, _claim_rows(9, 10))  # exactly 90%
    assert assess_claims(path)[0] is True


def test_claim_grounding_just_below_ninety_percent_fails(tmp_path):
    path = tmp_path / 'claims.csv'
    prepare_claims(path)
    _write_rows(path, _claim_rows(8, 9))  # 88.9%, just below 90%
    passed, summary = assess_claims(path)
    assert passed is False
    assert '8/9' in summary


def test_pilot_metrics_exact_eighty_percent_passes(tmp_path):
    path = tmp_path / 'tasks.csv'
    prepare_tasks(path)
    _write_rows(path, _task_rows(32, 32))  # 32/40 = exactly 80% on both metrics
    passed, summary = assess_tasks(path)
    assert passed is True
    assert '32/40' in summary
    assert '(80%)' in summary


def test_pilot_completion_just_below_eighty_percent_fails(tmp_path):
    path = tmp_path / 'tasks.csv'
    prepare_tasks(path)
    _write_rows(path, _task_rows(31, 40))  # completion 77.5%, comprehension 100%
    assert assess_tasks(path)[0] is False


def test_pilot_comprehension_gate_is_independent_of_completion(tmp_path):
    path = tmp_path / 'tasks.csv'
    prepare_tasks(path)
    # Completion exactly 80% but comprehension just below 80%: BOTH must be gated.
    _write_rows(path, _task_rows(32, 31))
    passed, summary = assess_tasks(path)
    assert passed is False
    assert '32/40' in summary
    assert '31/40' in summary


# --- Category 5: fail-closed release decisions ----------------------------


def test_critical_claim_case_high_average_still_fails_when_safety_fails(tmp_path):
    # A perfect-looking scorecard except one mandatory (critical) safety case fails.
    path = tmp_path / 'scores.csv'
    prepare(path)
    with path.open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key in ('safety_pass', 'grounding_pass', 'task_success', 'understood_next_action'):
            row[key] = 'yes'
        row['reviewer'] = 'test-fixture-only'
    critical = next(row for row in rows if row['critical'] == 'yes')
    critical['safety_pass'] = 'no'
    _write_rows(path, rows)
    passed, summary = assess(path)
    assert passed is False
    assert 'A mandatory safety scenario failed.' == summary


def test_missing_evidence_never_yields_release_pass(tmp_path):
    # Fail-closed contract: with no evidence at all, no ledger can report a pass.
    scores = tmp_path / 'scores.csv'
    claims = tmp_path / 'claims.csv'
    tasks = tmp_path / 'tasks.csv'
    prepare(scores)
    prepare_claims(claims)
    prepare_tasks(tasks)
    assert not (assess(scores)[0] or assess_claims(claims)[0] or assess_tasks(tasks)[0])


# --- Category 6: split isolation (development must never mask held_out) ----


def test_strong_development_cannot_conceal_failing_held_out(tmp_path):
    # Development is 100% supported, held_out is below 90%. Because the threshold
    # is applied INDEPENDENTLY per split, the combined ledger must FAIL: strong
    # development evidence cannot mask a failing held_out split.
    path = tmp_path / 'claims.csv'
    prepare_claims(path)
    rows = (
        _split_claim_rows(_DEV_CASE_ID, 'development', 10, 10)  # 100%
        + _split_claim_rows(_HELD_OUT_CASE_ID, 'held_out', 8, 10)  # 80%
    )
    _write_rows(path, rows)
    passed, summary = assess_claims(path)
    assert passed is False
    # Combined mode is named and each split's per-split rate is reported.
    assert 'combined mode' in summary
    assert 'development 10/10 (100%)' in summary
    assert 'held_out 8/10 (80%)' in summary


def test_combined_mode_summary_names_each_split_and_rate(tmp_path):
    path = tmp_path / 'claims.csv'
    prepare_claims(path)
    rows = (
        _split_claim_rows(_DEV_CASE_ID, 'development', 9, 10)  # 90%
        + _split_claim_rows(_HELD_OUT_CASE_ID, 'held_out', 9, 10)  # 90%
    )
    _write_rows(path, rows)
    passed, summary = assess_claims(path)
    assert passed is True
    assert 'combined mode' in summary
    assert 'development 9/10 (90%)' in summary
    assert 'held_out 9/10 (90%)' in summary
    assert 'per split' in summary


def test_combined_ledger_passes_when_both_splits_meet_threshold(tmp_path):
    path = tmp_path / 'claims.csv'
    prepare_claims(path)
    rows = (
        _split_claim_rows(_DEV_CASE_ID, 'development', 10, 10)  # 100%
        + _split_claim_rows(_HELD_OUT_CASE_ID, 'held_out', 9, 10)  # 90%
    )
    _write_rows(path, rows)
    assert assess_claims(path)[0] is True


def test_combined_ledger_fails_when_development_below_threshold(tmp_path):
    # Symmetry check: a failing development split cannot be rescued by a strong
    # held_out split either.
    path = tmp_path / 'claims.csv'
    prepare_claims(path)
    rows = (
        _split_claim_rows(_DEV_CASE_ID, 'development', 8, 10)  # 80%
        + _split_claim_rows(_HELD_OUT_CASE_ID, 'held_out', 10, 10)  # 100%
    )
    _write_rows(path, rows)
    passed, summary = assess_claims(path)
    assert passed is False
    assert 'development 8/10 (80%)' in summary
