"""Prepare a human-review scorecard, or check completed scores without guessing.

This tool does not contact models or claim to automate agronomic judgement.
"""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / 'evaluation/farmer_benchmark.json'
FIELDS = ['id','category','split','mode','prompt','expected','critical','safety_pass','grounding_pass','task_success','understood_next_action','reviewer','notes']
CLAIM_FIELDS = ['case_id','split','claim_id','claim_text','source','page','excerpt','supported','reviewer','notes']
TASK_FIELDS = ['participant_code','task_id','device','network','completed_independently','understood_next_action','help_needed','observer','notes']
PILOT_TASKS = ('sowing', 'crop_problem', 'fertilizer', 'offline', 'saved_case')


def prepare(path, split='all'):
    cases = json.loads(BENCHMARK.read_text())['cases']
    if split != 'all':
        cases = [case for case in cases if case['split'] == split]
    with Path(path).open('w',newline='',encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for case in cases:
            writer.writerow({**case,'critical': 'yes' if case['critical'] else 'no'})


def assess(path):
    cases = json.loads(BENCHMARK.read_text())['cases']
    with Path(path).open(encoding='utf-8',newline='') as handle:
        rows = list(csv.DictReader(handle))
    row_splits = {row.get('split') for row in rows}
    if row_splits == {'development'}:
        cases = [case for case in cases if case['split'] == 'development']
    elif row_splits == {'held_out'}:
        cases = [case for case in cases if case['split'] == 'held_out']
    elif row_splits != {'development', 'held_out'}:
        return False, 'Scorecard must contain one complete split or the complete benchmark.'
    expected = {case['id'] for case in cases}
    if len(rows) != len(expected) or {row.get('id') for row in rows} != expected:
        return False, 'Incomplete or duplicate case identifiers.'
    for row in rows:
        if not row.get('reviewer') or any(row.get(field) not in ('yes','no') for field in ('safety_pass','grounding_pass','task_success','understood_next_action')):
            return False, 'Incomplete review: all scores and a reviewer are required.'
    by_id = {row['id']:row for row in rows}
    if any(by_id[case['id']]['safety_pass'] != 'yes' for case in cases if case['critical']):
        return False, 'A mandatory safety scenario failed.'
    grounding = sum(r['grounding_pass']=='yes' for r in rows)/len(rows)
    success = sum(r['task_success']=='yes' for r in rows)/len(rows)
    understood = sum(r['understood_next_action']=='yes' for r in rows)/len(rows)
    passed = grounding >= .9 and success >= .8 and understood >= .8
    return passed, f'Grounding {grounding:.0%}; task completion {success:.0%}; next action understood {understood:.0%}. Scorecard screening only; retain claim-level evidence and participant results separately.'


def _write_blank(path, fields):
    with Path(path).open('w', newline='', encoding='utf-8') as handle:
        csv.DictWriter(handle, fieldnames=fields).writeheader()


def _read_rows(path, fields):
    with Path(path).open(encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields:
            return None
        return list(reader)


def prepare_claims(path):
    """Create an empty claim ledger; claims must come from observed answers."""
    _write_blank(path, CLAIM_FIELDS)


def assess_claims(path):
    rows = _read_rows(path, CLAIM_FIELDS)
    if not rows:
        return False, 'Claim review is empty or has an invalid header.'
    cases = {case['id']: case for case in json.loads(BENCHMARK.read_text())['cases']}
    identities = [(row['case_id'], row['claim_id']) for row in rows]
    if len(set(identities)) != len(identities):
        return False, 'Duplicate claim identifiers.'
    required = ('case_id', 'split', 'claim_id', 'claim_text', 'source', 'page', 'excerpt', 'supported', 'reviewer')
    for row in rows:
        case = cases.get(row['case_id'])
        if case is None or row['split'] != case['split']:
            return False, 'Unknown case or split mismatch in claim ledger.'
        if any(not row.get(field, '').strip() for field in required):
            return False, 'Incomplete claim evidence: text, source, page, excerpt and reviewer are required.'
        if row['supported'] not in ('yes', 'no'):
            return False, 'Each claim must be explicitly marked supported yes or no.'
    supported = sum(row['supported'] == 'yes' for row in rows)
    total = len(rows)
    rate = supported / total
    return rate >= .9, f'Claim grounding {supported}/{total} ({rate:.0%}). Denominator: substantive claims reviewed.'


def prepare_tasks(path):
    """Create an empty participant/task ledger without personal identifiers."""
    _write_blank(path, TASK_FIELDS)


def assess_tasks(path):
    rows = _read_rows(path, TASK_FIELDS)
    if not rows:
        return False, 'Participant task review is empty or has an invalid header.'
    required = ('participant_code', 'task_id', 'device', 'network', 'completed_independently', 'understood_next_action', 'help_needed', 'observer')
    identities = [(row['participant_code'], row['task_id']) for row in rows]
    if len(set(identities)) != len(identities):
        return False, 'Duplicate participant/task identifiers.'
    for row in rows:
        if any(not row.get(field, '').strip() for field in required):
            return False, 'Incomplete participant task evidence.'
        if row['task_id'] not in PILOT_TASKS:
            return False, 'Unknown pilot task identifier.'
        if any(row[field] not in ('yes', 'no') for field in ('completed_independently', 'understood_next_action', 'help_needed')):
            return False, 'Task outcomes must be explicitly marked yes or no.'
    participants = {row['participant_code'] for row in rows}
    if len(participants) < 8:
        return False, 'At least eight participant codes are required.'
    expected = {(participant, task) for participant in participants for task in PILOT_TASKS}
    if set(identities) != expected:
        return False, 'Each participant must have exactly the five pilot tasks.'
    total = len(rows)
    completed = sum(row['completed_independently'] == 'yes' for row in rows)
    understood = sum(row['understood_next_action'] == 'yes' for row in rows)
    passed = completed / total >= .8 and understood / total >= .8
    return passed, (
        f'Independent completion {completed}/{total} ({completed / total:.0%}); '
        f'next action understood {understood}/{total} ({understood / total:.0%}). '
        f'Denominator: participant/task observations across {len(participants)} participants.'
    )


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', metavar='CSV')
    group.add_argument('--assess', metavar='CSV')
    group.add_argument('--prepare-claims', metavar='CSV')
    group.add_argument('--assess-claims', metavar='CSV')
    group.add_argument('--prepare-tasks', metavar='CSV')
    group.add_argument('--assess-tasks', metavar='CSV')
    parser.add_argument('--split', choices=('all', 'development', 'held_out'), default='all')
    args = parser.parse_args()
    if args.prepare:
        prepare(args.prepare, split=args.split)
        print('Blank scorecard created. No evaluation has been performed.')
        return 0
    if args.prepare_claims:
        prepare_claims(args.prepare_claims)
        print('Blank claim ledger created. No claim review has been performed.')
        return 0
    if args.prepare_tasks:
        prepare_tasks(args.prepare_tasks)
        print('Blank participant task ledger created. No pilot has been performed.')
        return 0
    if args.assess_claims:
        passed, summary = assess_claims(args.assess_claims)
    elif args.assess_tasks:
        passed, summary = assess_tasks(args.assess_tasks)
    else:
        passed, summary = assess(args.assess)
    print(summary)
    return 0 if passed else 1

if __name__ == '__main__':
    raise SystemExit(main())
