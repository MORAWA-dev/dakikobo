from concurrent.futures import ThreadPoolExecutor
from core.rate_budget import consume


def test_budget_is_atomic_and_expires(tmp_path):
    path = str(tmp_path/'budget.sqlite3')
    def send(_):
        return consume(path, 'shared-client', minute_limit=5, global_minute_limit=20, now=120)
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(send, range(12)))
    assert results.count(0) == 5
    assert consume(path, 'shared-client', minute_limit=5, now=181) == 0


def test_global_budget_cannot_be_reset_by_new_client(tmp_path):
    path = str(tmp_path/'budget.sqlite3')
    assert consume(path,'one',global_minute_limit=1,now=120) == 0
    assert consume(path,'two',global_minute_limit=1,now=120) == 60
