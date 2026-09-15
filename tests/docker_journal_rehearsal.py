"""Bounded, synthetic Docker rehearsal for journal continuity across a
container replacement.

WHAT THIS PROVES (and what it does NOT):
  * It shows that a private journal saved into a local bind-mounted directory
    survives stopping and removing the container and starting a fresh
    replacement container from the same image, secret, and mount. This is
    *local bind-mount persistence* evidence only.
  * It is NOT evidence of hosting-provider disk durability, host rebuilds,
    volume migration, or real-browser/physical-phone behaviour. Those remain
    separate, explicitly pending acceptance work.

The rehearsal runs the production image with ``APP_ENV=production`` so the
server keeps its production ``Secure`` session cookie. It never weakens that
setting. Because the container is reached over plain HTTP, a standard client
would refuse to resend a ``Secure`` cookie, so a small TEST-ONLY cookie-aware
harness (``SecureCookieClient``) captures the owner cookie from the response and
re-sends it on later requests — exactly what a browser over TLS would do. No
model, no external provider, and no real user data are involved: one explicitly
consented synthetic case is saved.

Every container/HTTP operation has a timeout, and every container and temporary
directory is cleaned up on success and on failure. Public logs and artifacts
never contain the cookie, the secret, or database contents.

Usage:
    python tests/docker_journal_rehearsal.py            # builds image if needed
    DAKIKOBO_IMAGE=dakikobo:ci python tests/docker_journal_rehearsal.py
"""

import argparse
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import closing, contextmanager
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = os.environ.get("DAKIKOBO_IMAGE", "dakikobo:journal-rehearsal")
# A stable, throwaway secret used only inside this rehearsal. Not a real secret.
TEST_SECRET = "synthetic-docker-journal-rehearsal-secret-not-for-production"
CONTAINER_TIMEOUT = 90  # seconds to wait for /healthz


class RehearsalError(RuntimeError):
    """Raised when a rehearsal step fails; mapped to a non-zero exit."""


# ---------------------------------------------------------------------------
# Test-only cookie-aware HTTP harness
# ---------------------------------------------------------------------------

class SecureCookieClient:
    """Minimal HTTP client that carries the app's Secure session cookie.

    A production ``Secure`` cookie is not resent by a normal client over HTTP.
    This harness stores the cookie name/value from ``Set-Cookie`` and replays it
    on subsequent requests, emulating a browser over TLS without changing the
    server's production cookie settings. It is strictly for this rehearsal.
    """

    def __init__(self, base_url: str, timeout: float = 15.0):
        parts = urlsplit(base_url)
        self._host = parts.hostname
        self._port = parts.port
        self._timeout = timeout
        self._cookie: str | None = None

    @property
    def has_cookie(self) -> bool:
        return self._cookie is not None

    def clone_without_cookie(self) -> "SecureCookieClient":
        """A second, independent client (a different visitor) with no cookie."""
        return SecureCookieClient(
            f"http://{self._host}:{self._port}", timeout=self._timeout
        )

    def _request(self, method: str, path: str, form: dict | None = None) -> dict:
        conn = http.client.HTTPConnection(self._host, self._port, timeout=self._timeout)
        try:
            headers = {"Accept": "application/json"}
            body = None
            if self._cookie:
                headers["Cookie"] = self._cookie
            if form is not None:
                from urllib.parse import urlencode

                body = urlencode(form)
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()
            raw = response.read()
            set_cookie = response.getheader("Set-Cookie")
            if set_cookie:
                # Keep only the "name=value" pair; drop attributes like Secure.
                self._cookie = set_cookie.split(";", 1)[0]
            payload = json.loads(raw.decode("utf-8")) if raw else {}
            return {"status": response.status, "json": payload}
        finally:
            conn.close()

    def get(self, path: str) -> dict:
        return self._request("GET", path)

    def post(self, path: str, form: dict) -> dict:
        return self._request("POST", path, form=form)

    def delete(self, path: str) -> dict:
        return self._request("DELETE", path)


# ---------------------------------------------------------------------------
# Docker helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], timeout: float = 120, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode != 0:
        raise RehearsalError(
            f"Command failed ({' '.join(cmd[:3])}...): {result.stderr.strip()[:500]}"
        )
    return result


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        return _run(["docker", "info"], timeout=30, check=False).returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def ensure_image(image: str) -> None:
    exists = _run(["docker", "image", "inspect", image], timeout=30, check=False)
    if exists.returncode == 0:
        return
    print(f"Building image {image} (one-time)...")
    _run(["docker", "build", "--pull", "-t", image, str(ROOT)], timeout=1500)


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _force_remove(name: str) -> None:
    _run(["docker", "rm", "-f", name], timeout=30, check=False)


@contextmanager
def running_container(image: str, name: str, mount: Path, port: int):
    """Start a container on the isolated mount and always remove it.

    The mount is made world-writable so the unprivileged container user (uid
    1000 in the image) can create the SQLite journal; it is a throwaway temp
    directory removed by the caller.
    """
    _force_remove(name)
    mount.mkdir(parents=True, exist_ok=True)
    os.chmod(mount, 0o777)
    _run(
        [
            # --rm is defensive: if this process is killed before its finally
            # block runs, the container is still auto-removed once it stops.
            "docker", "run", "-d", "--rm", "--name", name,
            "-p", f"127.0.0.1:{port}:7860",
            "-e", "APP_ENV=production",
            "-e", "FLASK_DEBUG=false",
            "-e", f"FLASK_SECRET_KEY={TEST_SECRET}",
            "-e", "RAG_WARMUP_ON_START=false",
            "-e", "GROQ_API_KEY=",
            "-e", "GEMINI_API_KEY=",
            "-e", "FIRECRAWL_API_KEY=",
            "-e", "STATE_DB_PATH=/data/dakikobo/state.sqlite3",
            "-e", "CASE_LOG_DB_PATH=/data/dakikobo/journal.sqlite3",
            "-e", "FEEDBACK_IMAGE_DIR=/data/dakikobo/photos",
            "-v", f"{mount}:/data/dakikobo",
            image,
        ],
        timeout=60,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_healthy(name, port)
        yield base_url
    finally:
        _force_remove(name)


def _wait_healthy(name: str, port: int) -> None:
    deadline = time.monotonic() + CONTAINER_TIMEOUT
    while time.monotonic() < deadline:
        # Bail out early if the container has already exited.
        state = _run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name],
            timeout=15, check=False,
        )
        if state.stdout.strip() == "false":
            raise RehearsalError(f"Container {name} exited before becoming healthy")
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            conn.request("GET", "/healthz")
            if conn.getresponse().status == 200:
                conn.close()
                return
            conn.close()
        except OSError:
            pass
        time.sleep(1)
    raise RehearsalError(f"Container {name} did not answer /healthz in {CONTAINER_TIMEOUT}s")


# ---------------------------------------------------------------------------
# Rehearsal steps
# ---------------------------------------------------------------------------

def _save_synthetic_case(owner: SecureCookieClient) -> int:
    """Save one explicitly consented, synthetic case and return its id."""
    saved = owner.post("/feedback", {
        "rating": "up",
        "question": "Exercice Docker synthétique",
        "answer": "Conseil synthétique sans valeur agronomique.",
        "consent": "1",
        "request_id": uuid.uuid4().hex,
    })
    if saved["status"] != 200 or "feedback_id" not in saved["json"]:
        raise RehearsalError(f"Case save failed: HTTP {saved['status']}")
    if not owner.has_cookie:
        raise RehearsalError("Owner cookie was not established")
    return int(saved["json"]["feedback_id"])


def _owner_cases(client: SecureCookieClient) -> list:
    response = client.get("/journal")
    if response["status"] != 200:
        raise RehearsalError(f"Journal read failed: HTTP {response['status']}")
    return response["json"].get("cases", [])


def rehearse(image: str) -> dict:
    """Run the full continuity rehearsal and negative control.

    Returns a redacted summary safe for public logs (no cookies, secrets, or
    database contents).
    """
    workspace = Path(tempfile.mkdtemp(prefix="dakikobo-docker-"))
    mount = workspace / "mount"
    empty_mount = workspace / "empty-mount"
    port = _free_port()
    summary: dict = {}
    try:
        # 1) First container: save one consented synthetic case, keep the cookie.
        with running_container(image, "dakikobo-journal-a", mount, port) as base_url:
            owner = SecureCookieClient(base_url)
            case_id = _save_synthetic_case(owner)
            before = _owner_cases(owner)
            if len(before) != 1:
                raise RehearsalError(f"Expected 1 case before replacement, got {len(before)}")

        # 2) Replacement container: same image, secret, and mount. The owner's
        #    case must still be there; a different visitor must not see it; a
        #    non-owner deletion must be a no-op; the owner can delete it.
        with running_container(image, "dakikobo-journal-b", mount, port) as base_url:
            # The owner keeps the cookie captured before the replacement.
            after = _owner_cases(owner)
            summary["owner_case_survived_replacement"] = (
                len(after) == 1 and after[0]["feedback_id"] == case_id
            )

            other = owner.clone_without_cookie()
            other_view = _owner_cases(other)
            summary["other_client_sees_no_case"] = other_view == []

            other_delete = other.delete(f"/journal/{case_id}")
            summary["non_owner_delete_is_noop"] = (
                other_delete["status"] == 200
                and other_delete["json"].get("deleted") == 0
            )
            summary["case_intact_after_non_owner_delete"] = (
                len(_owner_cases(owner)) == 1
            )

            owner_delete = owner.delete(f"/journal/{case_id}")
            summary["owner_delete_succeeds"] = (
                owner_delete["status"] == 200
                and owner_delete["json"].get("deleted") == 1
            )
            summary["case_removed_after_owner_delete"] = (
                _owner_cases(owner) == []
            )

        # 3) Negative control: a fresh empty mount must contain no saved case.
        control_port = _free_port()
        with running_container(
            image, "dakikobo-journal-control", empty_mount, control_port
        ) as base_url:
            control_owner = SecureCookieClient(base_url)
            summary["fresh_mount_has_no_case"] = _owner_cases(control_owner) == []
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
        for name in (
            "dakikobo-journal-a",
            "dakikobo-journal-b",
            "dakikobo-journal-control",
        ):
            _force_remove(name)

    failures = [key for key, ok in summary.items() if not ok]
    if failures:
        raise RehearsalError("Rehearsal assertions failed: " + ", ".join(failures))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument(
        "--skip-if-no-docker",
        action="store_true",
        help="Exit 0 with a notice if Docker is unavailable (for local runs).",
    )
    args = parser.parse_args()

    if not docker_available():
        message = "Docker is unavailable; the container rehearsal cannot run here."
        if args.skip_if_no_docker:
            print(message + " Skipping.")
            return 0
        print(message, file=sys.stderr)
        return 1

    try:
        ensure_image(args.image)
        summary = rehearse(args.image)
    except (RehearsalError, subprocess.TimeoutExpired) as error:
        print(f"Docker journal rehearsal FAILED: {error}", file=sys.stderr)
        return 1

    print("Docker journal rehearsal passed (local bind-mount persistence only):")
    for key, value in summary.items():
        print(f"  - {key}: {value}")
    print(
        "NOTE: This is local bind-mount persistence evidence only. It is NOT "
        "hosting-provider disk durability, host-rebuild, or physical-browser "
        "evidence."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
