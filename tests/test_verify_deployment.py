"""Deployment identity tests use real Git trees, including LFS pointer blobs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/verify_deployment.py"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args]).decode().strip()


@pytest.fixture
def snapshots(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "app.txt").write_bytes(b"bonjour\n")
    (tmp_path / "données.bin").write_bytes(b"binary\x00payload")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "GitHub")
    github = git(tmp_path, "rev-parse", "HEAD")
    data = b"binary\x00payload"
    (tmp_path / "données.bin").write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        f"oid sha256:{hashlib.sha256(data).hexdigest()}\nsize {len(data)}\n"
    )
    (tmp_path / ".gitattributes").write_text("# Space metadata\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", f"Deploy GitHub main {github} to Space")
    return tmp_path, github, git(tmp_path, "rev-parse", "HEAD")


def run_check(snapshots, *extra):
    repo, github, hf = snapshots
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--github-ref", github,
         "--hf-ref", hf, *extra], capture_output=True, text=True,
    )
    return result, json.loads(result.stdout)


def test_dry_run_normalizes_lfs_and_ignores_only_space_attributes(snapshots):
    result, report = run_check(snapshots, "--dry-run")
    assert result.returncode == 0
    assert report["manifest_match"] is True
    assert report["live_verified"] is False
    assert report["result"] == "PASS (dry run only)"
    assert report["github_sha"] == snapshots[1]
    assert report["hf_sha"] == snapshots[2]


@pytest.mark.parametrize("change,path", [("content", "app.txt"), ("delete", "app.txt"),
                                           ("extra", "extra.txt"), ("mode", "app.txt")])
def test_drift_fails_with_exact_path(snapshots, change, path):
    repo, github, _ = snapshots
    if change == "delete":
        (repo / path).unlink()
    elif change == "mode":
        (repo / path).chmod(0o755)
    else:
        (repo / path).write_text("changed")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", f"Deploy GitHub main {github} to Space")
    result, report = run_check((repo, github, git(repo, "rev-parse", "HEAD")), "--dry-run")
    assert result.returncode == 1
    assert report["differing_paths"] == [path]
    assert report["result"] == "FAIL"


def test_bad_ref_fails_closed(snapshots):
    repo, _, hf = snapshots
    result, report = run_check((repo, "missing-ref", hf), "--dry-run")
    assert result.returncode == 1
    assert report["result"] == "FAIL"
    assert report["error"]


def test_uncommitted_files_cannot_change_snapshot(snapshots):
    (snapshots[0] / "app.txt").write_text("local edit")
    (snapshots[0] / "private-untracked.txt").write_text("not a deployment file")
    result, report = run_check(snapshots, "--dry-run")
    assert result.returncode == 0
    assert report["differing_paths"] == []


def test_wrong_deployment_message_fails(snapshots):
    repo, github, _ = snapshots
    git(repo, "commit", "--allow-empty", "-qm", "Unmapped deployment")
    result, report = run_check((repo, github, git(repo, "rev-parse", "HEAD")), "--dry-run")
    assert result.returncode == 1
    assert report["manifest_match"] is True
    assert report["deployment_message_match"] is False


def test_malformed_lfs_pointer_fails_closed(snapshots):
    repo, github, _ = snapshots
    (repo / "données.bin").write_text("version https://git-lfs.github.com/spec/v1\noid invalid\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", f"Deploy GitHub main {github} to Space")
    result, report = run_check((repo, github, git(repo, "rev-parse", "HEAD")), "--dry-run")
    assert result.returncode == 1
    assert "LFS" in report["error"]


@pytest.mark.parametrize("live_sha,ready,ok,expected", [
    ("current", True, True, 0), ("stale", True, True, 1),
    ("current", False, True, 1), ("current", True, False, 1),
])
def test_live_identity_and_health(snapshots, live_sha, ready, ok, expected):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            payload = ({"commit": snapshots[2] if live_sha == "current" else "0" * 40,
                        "rag_status": "ready" if ready else "loading"}
                       if self.path == "/version" else
                       {"ok": ok, "rag_ready": ready, "rag_status": "ready" if ready else "loading"})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result, report = run_check(snapshots, "--base-url", f"http://127.0.0.1:{server.server_port}")
        assert result.returncode == expected
        assert report["live_verified"] is (expected == 0)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
