"""Restart and SQLite backup rehearsal with synthetic data in fresh processes."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys


_HTTP_SERVER = r'''
from pathlib import Path
import sys
import app
from werkzeug.serving import make_server
# Synthetic loopback rehearsal only: HTTP cannot exercise a Secure cookie.
app.app.config['SESSION_COOKIE_SECURE'] = False
server = make_server('127.0.0.1', 0, app.app)
Path(sys.argv[1]).write_text(str(server.server_port))
server.serve_forever()
'''


def test_http_restart_and_restore_preserve_owner_cookie(tmp_path):
    """Exercise real requests and cookie continuity across isolated server restarts."""
    from contextlib import contextmanager
    import time
    import requests

    root = Path(__file__).resolve().parents[1]

    @contextmanager
    def server(directory, run_name):
        directory.mkdir(exist_ok=True)
        ready = tmp_path / (run_name + '.port')
        env = dict(os.environ, APP_ENV='production', FLASK_DEBUG='false',
                   FLASK_SECRET_KEY='synthetic-loopback-recovery-secret',
                   RAG_WARMUP_ON_START='false', GROQ_API_KEY='', GEMINI_API_KEY='',
                   FIRECRAWL_API_KEY='', STATE_DB_PATH=str(directory / 'state.sqlite3'),
                   CASE_LOG_DB_PATH=str(directory / 'journal.sqlite3'),
                   FEEDBACK_IMAGE_DIR=str(directory / 'photos'))
        with (tmp_path / (run_name + '.log')).open('w+') as log:
            process = subprocess.Popen([sys.executable, '-c', _HTTP_SERVER, str(ready)],
                                       cwd=root, env=env, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 35
                while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.05)
                if not ready.exists():
                    log.seek(0)
                    raise AssertionError('Loopback server did not start: ' + log.read())
                yield 'http://127.0.0.1:' + ready.read_text().strip()
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    owner = requests.Session()
    original = tmp_path / 'original-http'
    with server(original, 'initial') as url:
        saved = owner.post(url + '/feedback', data={
            'rating': 'up', 'question': 'Exercice HTTP synthétique',
            'answer': 'Sans valeur agronomique.', 'consent': '1'
        }, timeout=10)
        assert saved.status_code == 200
        case_id = saved.json()['feedback_id']
        expected = owner.get(url + '/journal', timeout=10).json()['cases']
        assert len(expected) == 1
        assert owner.cookies.get('session')

    with server(original, 'restarted') as url:
        response = owner.get(url + '/journal', timeout=10)
        assert response.status_code == 200
        assert response.headers['Cache-Control'] == 'no-store'
        assert response.json()['cases'] == expected
        assert requests.get(url + '/journal', timeout=10).json()['cases'] == []

    # Writers are stopped before the consistent snapshot is taken.
    restored = tmp_path / 'restored-http'
    restored.mkdir()
    with sqlite3.connect(original / 'journal.sqlite3') as source:
        with sqlite3.connect(restored / 'journal.sqlite3') as destination:
            source.backup(destination)
            assert destination.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    with server(restored, 'restored') as url:
        assert owner.get(url + '/journal', timeout=10).json()['cases'] == expected
        denied = requests.delete(url + '/journal/' + str(case_id), timeout=10)
        assert denied.status_code == 200
        assert denied.json()['deleted'] == 0
        assert owner.get(url + '/journal', timeout=10).json()['cases'] == expected
        deleted = owner.delete(url + '/journal/' + str(case_id), timeout=10)
        assert deleted.status_code == 200
        assert deleted.json()['deleted'] == 1
        assert owner.get(url + '/journal', timeout=10).json()['cases'] == []
    with sqlite3.connect(original / 'journal.sqlite3') as source:
        assert source.execute('SELECT count(*) FROM feedback_events').fetchone()[0] == 1
    owner.close()


# Each invocation imports Flask afresh; no developer journal or provider is used.
_PROCESS = r'''
import json, sys
import app
request = json.load(sys.stdin)
client = app.app.test_client()
if request.get('cookie'):
    client.set_cookie('session', request['cookie'], domain='localhost')
action = request['action']
if action == 'save':
    for index in range(2):
        result = client.post('/feedback', base_url='https://localhost', data={
            'rating': 'up', 'question': 'Question synthétique ' + str(index),
            'answer': 'Conseil synthétique sans valeur agronomique.', 'consent': '1'
        })
        assert result.status_code == 200
elif action == 'delete':
    result = client.delete('/journal/' + str(request['case_id']), base_url='https://localhost')
    assert result.status_code == 200
    assert result.json['deleted'] == 1
result = client.get('/journal', base_url='https://localhost')
assert result.status_code == 200
assert result.headers['Cache-Control'] == 'no-store'
print('RECOVERY_RESULT=' + json.dumps({'cases': result.json['cases'],
    'cookie': client.get_cookie('session').value}))
'''


def test_restart_backup_restore_ownership_deletion_and_expiration(tmp_path):
    root = Path(__file__).resolve().parents[1]
    secret = 'synthetic-recovery-secret-not-used-outside-this-test'

    def run(directory, action, **values):
        directory.mkdir(exist_ok=True)
        env = dict(os.environ, APP_ENV='production', FLASK_DEBUG='false',
                   FLASK_SECRET_KEY=secret, RAG_WARMUP_ON_START='false',
                   GROQ_API_KEY='', GEMINI_API_KEY='', FIRECRAWL_API_KEY='',
                   STATE_DB_PATH=str(directory / 'state.sqlite3'),
                   CASE_LOG_DB_PATH=str(directory / 'journal.sqlite3'),
                   FEEDBACK_IMAGE_DIR=str(directory / 'photos'))
        result = subprocess.run([sys.executable, '-c', _PROCESS], cwd=root, env=env,
                                input=json.dumps(dict(action=action, **values)),
                                text=True, capture_output=True, timeout=45)
        assert result.returncode == 0, result.stderr
        line = next(line for line in result.stdout.splitlines() if line.startswith('RECOVERY_RESULT='))
        return json.loads(line.split('=', 1)[1])

    original = tmp_path / 'original'
    saved = run(original, 'save')
    assert len(saved['cases']) == 2
    owner_cookie = saved['cookie']
    restarted = run(original, 'read', cookie=owner_cookie)
    assert restarted['cases'] == saved['cases']
    assert run(original, 'read')['cases'] == []

    # SQLite's backup API creates a consistent snapshot including committed WAL.
    backup = tmp_path / 'backup.sqlite3'
    with sqlite3.connect(original / 'journal.sqlite3') as source:
        with sqlite3.connect(backup) as destination:
            source.backup(destination)
            assert destination.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    restored = tmp_path / 'restored'
    restored.mkdir()
    with sqlite3.connect(backup) as source:
        with sqlite3.connect(restored / 'journal.sqlite3') as destination:
            source.backup(destination)
    assert run(restored, 'read', cookie=owner_cookie)['cases'] == saved['cases']
    assert run(restored, 'read')['cases'] == []
    remaining = run(restored, 'delete', cookie=owner_cookie, case_id=saved['cases'][0]['feedback_id'])
    assert len(remaining['cases']) == 1
    with sqlite3.connect(restored / 'journal.sqlite3') as conn:
        conn.execute('UPDATE feedback_events SET expires_at=1')
    assert run(restored, 'read', cookie=owner_cookie)['cases'] == []
    # Restoring/testing never mutates the original journal or snapshot.
    with sqlite3.connect(original / 'journal.sqlite3') as conn:
        assert conn.execute('SELECT count(*) FROM feedback_events').fetchone()[0] == 2
    with sqlite3.connect(backup) as conn:
        assert conn.execute('SELECT count(*) FROM feedback_events').fetchone()[0] == 2


def test_photo_snapshot_restored_at_same_path_cleans_up_owned_attachments(tmp_path, monkeypatch):
    """Recreate an isolated mount at the original path; do not rewrite photo refs."""
    import io
    import shutil
    from PIL import Image
    import app as application

    mount = tmp_path / 'mount'
    mount.mkdir()
    database = mount / 'journal.sqlite3'
    photos = mount / 'photos'
    monkeypatch.setattr(application, 'CASE_LOG_DB', str(database))
    monkeypatch.setattr(application, 'FEEDBACK_IMAGES', str(photos))
    owner = application.app.test_client()
    ids = []
    for color in ('green', 'yellow'):
        response = owner.post('/feedback', data={'rating': 'up', 'question': 'Photo synthétique',
            'answer': 'Exercice de restauration.', 'consent': '1'})
        case_id = response.json['feedback_id']
        ids.append(case_id)
        image = io.BytesIO()
        Image.new('RGB', (8, 8), color).save(image, format='PNG')
        image.seek(0)
        response = owner.post('/feedback/outcome', data={'feedback_id': case_id,
            'outcome': 'not_sure', 'after_image': (image, 'synthetic.png')})
        assert response.status_code == 200
    with sqlite3.connect(database) as connection:
        refs = [Path(row[0]) for row in connection.execute(
            'SELECT after_image_ref FROM feedback_events ORDER BY id')]
    expected = {path.name: path.read_bytes() for path in refs}
    backup = tmp_path / 'snapshot'
    backup.mkdir()
    with sqlite3.connect(database) as source, sqlite3.connect(backup / 'journal.sqlite3') as target:
        source.backup(target)
        assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    shutil.copytree(photos, backup / 'photos')
    # No open application connections: swap the isolated mount for its restored copy.
    original = tmp_path / 'original-mount'
    mount.rename(original)
    shutil.copytree(backup, mount)
    assert {p.name: p.read_bytes() for p in refs} == expected
    for path in refs:
        with Image.open(path) as image:
            assert image.size == (8, 8)
            assert image.format == 'JPEG'
    assert owner.get('/journal').json['count'] == 2
    other = application.app.test_client()
    assert other.get('/journal').json['count'] == 0
    assert other.delete('/journal/' + str(ids[0])).json['deleted'] == 0
    assert refs[0].exists()
    assert owner.delete('/journal/' + str(ids[0])).json['deleted'] == 1
    assert not refs[0].exists()
    assert refs[1].exists()
    with sqlite3.connect(database) as connection:
        connection.execute('UPDATE feedback_events SET expires_at=1')
    assert owner.get('/journal').json['count'] == 0
    assert not refs[1].exists()
    for preserved in (backup, original):
        assert {p.name: p.read_bytes() for p in (preserved / 'photos').iterdir()} == expected
