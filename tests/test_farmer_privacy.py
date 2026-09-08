"""Cross-client journal regressions; never use the developer's journal."""
import io
import sqlite3
import pytest
import app as application

@pytest.fixture
def clients(tmp_path, monkeypatch):
    monkeypatch.setattr(application, 'CASE_LOG_DB', str(tmp_path / 'journal.sqlite3'))
    monkeypatch.setattr(application, 'FEEDBACK_IMAGES', str(tmp_path / 'photos'))
    application.app.config.update(TESTING=True)
    return application.app.test_client(), application.app.test_client()

def save(client):
    response = client.post('/feedback', data={'rating':'up', 'question':'Mon mil', 'answer':'Conseil', 'consent':'1'})
    assert response.status_code == 200
    return response.json['feedback_id']

def test_other_client_cannot_change_outcome_or_upload(clients, tmp_path):
    owner, other = clients
    case_id = save(owner)
    response = other.post('/feedback/outcome', data={'feedback_id':case_id, 'outcome':'applied_worse', 'after_image':(io.BytesIO(b'private'), 'leaf.jpg')})
    assert response.status_code == 404
    assert not (tmp_path / 'photos').exists()
    assert owner.post('/feedback/outcome', data={'feedback_id':case_id, 'outcome':'not_applied'}).status_code == 200

def test_due_digest_is_owned(clients):
    owner, other = clients
    save(owner)
    with sqlite3.connect(application.CASE_LOG_DB) as conn:
        conn.execute('UPDATE feedback_events SET follow_up_due_at=1')
    assert owner.get('/journal/due').json['count'] == 1
    assert other.get('/journal/due').json['count'] == 0


def test_consent_idempotence_deletion_and_legacy_isolation(clients):
    from core.case_log import record_feedback
    owner, other = clients
    rating_only = owner.post('/feedback', data={'rating':'up','question':'Q','answer':'A'})
    assert rating_only.status_code == 200
    assert rating_only.json == {'ok': True, 'saved_to_journal': False}
    assert owner.get('/journal').json['cases'] == []
    data = {'rating':'up','question':'Q','answer':'A','consent':'1','request_id':'retry-one'}
    first = owner.post('/feedback', data=data).json['feedback_id']
    assert owner.post('/feedback', data=data).json['feedback_id'] == first
    assert len(owner.get('/journal').json['cases']) == 1
    assert other.delete('/journal/'+str(first)).json['deleted'] == 0
    record_feedback(application.CASE_LOG_DB, rating='up', question='legacy', answer='private')
    assert len(owner.get('/journal').json['cases']) == 1
    assert other.get('/journal').json['cases'] == []
    assert owner.delete('/journal/'+str(first)).json['deleted'] == 1
    assert owner.get('/journal').json['cases'] == []


def test_expired_journal_is_not_returned(clients):
    owner, _ = clients
    save(owner)
    with sqlite3.connect(application.CASE_LOG_DB) as conn:
        conn.execute('UPDATE feedback_events SET expires_at=1')
    assert owner.get('/journal').json['cases'] == []
    with sqlite3.connect(application.CASE_LOG_DB) as conn:
        assert conn.execute('SELECT count(*) FROM feedback_events').fetchone()[0] == 0


def test_cross_origin_write_is_rejected(clients):
    owner, _ = clients
    assert owner.post('/feedback', data={'rating':'up'}, headers={'Origin':'https://attacker.invalid'}).status_code == 403
