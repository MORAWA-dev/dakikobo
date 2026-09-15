"""Failure-path unit tests for the Docker journal rehearsal.

These mock the Docker CLI so they run in the normal offline suite with no
Docker daemon. They cover the review findings: unique per-run container names,
cleanup that continues past a per-container removal timeout, cleanup-error
reporting, and preserving the original error while reporting cleanup problems.
The real container rehearsal is exercised separately (see SESSION.md / CI).
"""

import subprocess

import pytest

import tests.docker_journal_rehearsal as rehearsal_mod
from tests.docker_journal_rehearsal import (
    CleanupError,
    Rehearsal,
    RehearsalError,
    SecureCookieClient,
    rehearse,
)


def _fake_docker(record, *, timeout_names=None, fail_names=None):
    """Return a fake `_run` that records `docker rm` calls and can misbehave."""
    timeout_names = set(timeout_names or [])
    fail_names = set(fail_names or [])

    def run(cmd, timeout=120, check=True):
        if cmd[:3] == ["docker", "rm", "-f"]:
            name = cmd[3]
            record.append(name)
            if name in timeout_names:
                raise subprocess.TimeoutExpired(cmd, timeout)
            if name in fail_names:
                raise OSError(f"boom removing {name}")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    return run


def test_container_names_are_unique_per_run():
    a = Rehearsal("img", run_docker=lambda *a, **k: None)
    b = Rehearsal("img", run_docker=lambda *a, **k: None)
    assert a.token != b.token
    assert a.container_name("a") != b.container_name("a")
    assert a.container_name("a").startswith("dakikobo-journal-")
    # A run only ever names containers under its own token.
    assert a.token in a.container_name("control")


def test_cleanup_removes_only_started_containers():
    record: list[str] = []
    r = Rehearsal("img", run_docker=_fake_docker(record))
    r._started = [r.container_name("a"), r.container_name("b")]
    errors = r.cleanup()
    assert errors == []
    assert set(record) == {r.container_name("a"), r.container_name("b")}
    assert r._started == []


def test_cleanup_continues_after_a_removal_timeout():
    record: list[str] = []
    r = Rehearsal("img", run_docker=None)
    stuck = "dakikobo-journal-x-a"
    other = "dakikobo-journal-x-b"
    r._run = _fake_docker(record, timeout_names={stuck})
    r._started = [stuck, other]
    errors = r.cleanup()
    # The stuck container is reported, but the other is still removed.
    assert any("timed out" in e and stuck in e for e in errors)
    assert other in record
    assert other not in r._started  # the removable one was cleaned up


def test_cleanup_reports_removal_failures():
    record: list[str] = []
    r = Rehearsal("img", run_docker=None)
    bad = "dakikobo-journal-y-a"
    r._run = _fake_docker(record, fail_names={bad})
    r._started = [bad]
    errors = r.cleanup()
    assert len(errors) == 1 and bad in errors[0] and "failed to remove" in errors[0]


def test_rehearse_preserves_original_error_and_reports_cleanup(monkeypatch):
    """A body failure is preserved; a concurrent cleanup timeout is appended."""
    record: list[str] = []

    class _StubRehearsal(Rehearsal):
        def __init__(self):
            super().__init__("img", run_docker=_fake_docker(record))
            # Pretend two containers were started and one is stuck on removal.
            self._started = [self.container_name("a"), self.container_name("b")]
            self._run = _fake_docker(record, timeout_names={self.container_name("b")})

    stub = _StubRehearsal()

    def boom(*_args, **_kwargs):
        raise RehearsalError("assertion body failed")

    monkeypatch.setattr(rehearsal_mod, "_run_checks", boom)

    with pytest.raises(RehearsalError) as excinfo:
        rehearse("img", rehearsal=stub)
    message = str(excinfo.value)
    # Original error preserved AND cleanup problem reported alongside it.
    assert "assertion body failed" in message
    assert "cleanup errors" in message
    assert isinstance(excinfo.value.__cause__, RehearsalError)


def test_rehearse_raises_cleanup_error_when_body_passes_but_cleanup_fails(monkeypatch):
    record: list[str] = []

    class _StubRehearsal(Rehearsal):
        def __init__(self):
            super().__init__("img", run_docker=_fake_docker(record))
            self._started = [self.container_name("a")]
            self._run = _fake_docker(record, fail_names={self.container_name("a")})

    stub = _StubRehearsal()
    monkeypatch.setattr(rehearsal_mod, "_run_checks", lambda *a, **k: {"ok": True})

    with pytest.raises(CleanupError):
        rehearse("img", rehearsal=stub)


def test_secure_cookie_client_retarget_keeps_cookie():
    client = SecureCookieClient("http://127.0.0.1:5001")
    client._cookie = "session=abc"
    client.retarget("http://127.0.0.1:5002")
    assert client._port == 5002
    assert client.has_cookie and client._cookie == "session=abc"
