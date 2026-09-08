"""Generate a private, persistent fallback secret shared by local workers."""
import os
import secrets
from pathlib import Path
import fcntl


def load_session_secret(configured, directory):
    if configured and configured != 'change-me-in-production':
        return configured
    path = Path(directory) / '.session_secret'
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(descriptor, 'r+') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        value = handle.read().strip()
        if not value:
            value = secrets.token_hex(32)
            handle.write(value)
            handle.flush()
        return value
