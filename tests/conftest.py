"""Runtime budget isolation prevents tests from spending the developer's budget."""
import sys
import pytest

@pytest.fixture(autouse=True)
def isolate_request_budget(tmp_path, monkeypatch):
    module = sys.modules.get('app')
    if module:
        monkeypatch.setitem(module.app.config, 'BUDGET_DB_PATH', str(tmp_path / 'budget.sqlite3'))
