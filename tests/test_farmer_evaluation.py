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
