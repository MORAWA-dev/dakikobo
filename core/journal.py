"""Owned journal boundary. Legacy rows remain available only to local operators.

All public reads and mutations pass through this module. A process lock covers
SQLite changes and attachment cleanup together; no client-supplied file paths.
"""
from contextlib import contextmanager
from pathlib import Path
import time
import uuid
import io

from PIL import Image, ImageOps, UnidentifiedImageError
from core.cache import interprocess_file_lock, sqlite_connection
from config import JOURNAL_MAX_CASES, JOURNAL_RETENTION_DAYS
from core.case_log import init_case_log, record_feedback, VALID_OUTCOMES


def _remove_photo(ref, directory):
    if not ref:
        return
    path = Path(ref)
    if path.parent.resolve() == Path(directory).resolve():
        path.unlink(missing_ok=True)


@contextmanager
def journal_connection(db_path, image_dir):
    with interprocess_file_lock(str(db_path) + '.mutations.lock'):
        init_case_log(db_path)
        with sqlite_connection(db_path) as conn:
            expired = conn.execute('SELECT id, before_image_ref, after_image_ref FROM feedback_events WHERE expires_at <= ?', (time.time(),)).fetchall()
            for row in expired:
                _remove_photo(row['before_image_ref'], image_dir)
                _remove_photo(row['after_image_ref'], image_dir)
                conn.execute('DELETE FROM evidence_ledger WHERE feedback_id=?', (row['id'],))
                conn.execute('DELETE FROM feedback_events WHERE id=?', (row['id'],))
            # Unlinked evidence contains no text but also has a bounded lifetime.
            conn.execute('DELETE FROM evidence_ledger WHERE feedback_id IS NULL AND created_at < ?', (time.time()-JOURNAL_RETENTION_DAYS*86400,))
            yield conn


def list_owned(db_path, owner, image_dir, *, due=False):
    with journal_connection(db_path, image_dir) as conn:
        rows = conn.execute('''SELECT id AS feedback_id, created_at, question, answer,
            crop_id, place_id, answer_path, follow_up_due_at, outcome, expires_at
            FROM feedback_events WHERE owner_hash=? AND expires_at>?
            ORDER BY id DESC LIMIT ?''', (owner, time.time(), JOURNAL_MAX_CASES)).fetchall()
        result = [dict(row) for row in rows]
    if due:
        result = [{k: v for k, v in row.items() if k not in ('question', 'answer')}
                  for row in result if row['outcome'] is None and row['follow_up_due_at'] <= time.time()]
    return result


def save_owned(db_path, owner, image_dir, *, request_id, **values):
    # The lock makes idempotent retries and per-owner capacity atomic across workers.
    with journal_connection(db_path, image_dir) as conn:
        previous = conn.execute('SELECT id FROM feedback_events WHERE owner_hash=? AND request_id=?', (owner, request_id)).fetchone()
        if previous:
            return previous['id']
        count = conn.execute('SELECT count(*) FROM feedback_events WHERE owner_hash=?', (owner,)).fetchone()[0]
        if count >= JOURNAL_MAX_CASES:
            raise ValueError('Votre journal est plein. Supprimez un ancien conseil avant de continuer.')
        # Commit retention cleanup before the existing ledger-aware insert opens its connection.
        conn.commit()
        return record_feedback(db_path, owner_hash=owner, expires_at=time.time()+JOURNAL_RETENTION_DAYS*86400,
                               request_id=request_id, **values)


def _photo_bytes(upload):
    raw = upload.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError('La photo dépasse 5 Mo.')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.width * image.height > 20_000_000:
                raise ValueError('La photo est trop grande. Réduisez sa taille.')
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((1600, 1600))
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Photo illisible. Envoyez une image JPEG, PNG ou WebP.') from exc


def update_owned(db_path, owner, image_dir, case_id, outcome, upload=None):
    with journal_connection(db_path, image_dir) as conn:
        row = conn.execute('SELECT after_image_ref FROM feedback_events WHERE id=? AND owner_hash=? AND expires_at>?', (case_id, owner, time.time())).fetchone()
        if row is None:
            return False
        if outcome not in VALID_OUTCOMES:
            raise ValueError('Le résultat de suivi est invalide.')
        ref = ''
        if upload and upload.filename:
            content = _photo_bytes(upload)  # validate only after ownership, before disk writes
            Path(image_dir).mkdir(parents=True, exist_ok=True)
            ref = str(Path(image_dir) / (uuid.uuid4().hex + '.jpg'))
            Path(ref).write_bytes(content)
        try:
            conn.execute('''UPDATE feedback_events SET outcome=?, outcome_at=datetime('now'),
                after_image_ref=COALESCE(NULLIF(?, ''), after_image_ref) WHERE id=? AND owner_hash=?''',
                (outcome, ref, case_id, owner))
            conn.commit()
        except Exception:
            _remove_photo(ref, image_dir)
            raise
        if ref:
            _remove_photo(row['after_image_ref'], image_dir)
        return True


def delete_owned(db_path, owner, image_dir, case_id=None):
    with journal_connection(db_path, image_dir) as conn:
        rows = conn.execute('SELECT id, before_image_ref, after_image_ref FROM feedback_events WHERE owner_hash=? AND (? IS NULL OR id=?)', (owner, case_id, case_id)).fetchall()
        for row in rows:
            conn.execute('DELETE FROM evidence_ledger WHERE feedback_id=?', (row['id'],))
            conn.execute('DELETE FROM feedback_events WHERE id=? AND owner_hash=?', (row['id'], owner))
            _remove_photo(row['before_image_ref'], image_dir)
            _remove_photo(row['after_image_ref'], image_dir)
        return len(rows)
