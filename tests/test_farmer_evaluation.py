import csv
import json
from scripts.farmer_evaluation import BENCHMARK, prepare, assess


def test_blank_or_missing_scorecards_cannot_pass(tmp_path):
    data=json.loads(BENCHMARK.read_text())
    assert len(data['cases']) == 60
    assert sum(c['split']=='held_out' for c in data['cases']) == 20
    path=tmp_path/'scores.csv'
    prepare(path)
    assert not assess(path)[0]


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
