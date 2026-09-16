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

Isolation and cleanup:
  * Container names are unique per run (a UUID token), so concurrent runs never
    collide and this rehearsal never force-removes a fixed name that could
    belong to another run. It only removes the containers it started.
  * Every container/HTTP operation has a timeout. Cleanup removes each owned
    container independently (a slow removal cannot skip the others), removes all
    containers before deleting mount data, and reports cleanup failures instead
    of hiding them, while preserving the original error.

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
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = os.environ.get("DAKIKOBO_IMAGE", "dakikobo:journal-rehearsal")
# A stable, throwaway secret used only inside this rehearsal. Not a real secret.
TEST_SECRET = "synthetic-docker-journal-rehearsal-secret-not-for-production"
CONTAINER_TIMEOUT = 90  # seconds to wait for /healthz
REMOVE_TIMEOUT = 30  # seconds to remove a single container


class RehearsalError(RuntimeError):
    """Raised when a rehearsal step fails; mapped to a non-zero exit."""


class CleanupError(RuntimeError):
    """Raised when one or more owned containers could not be removed."""


class RemovalFailed(RuntimeError):
    """Raised when `docker rm -f` returns a nonzero exit for one container."""


_STDERR_LIMIT = 300  # bounded stderr kept in internal failure messages
_CLEANUP_MESSAGE_LIMIT = 300  # bounded detail kept in filesystem cleanup errors


# ---------------------------------------------------------------------------
# Test-only cookie-aware HTTP harness
# ---------------------------------------------------------------------------

class SecureCookieClient:
    """Minimal HTTP client that carries the app's Secure session cookie.

    A production ``Secure`` cookie is not resent by a normal client over HTTP.
    This harness stores the cookie name/value from ``Set-Cookie`` and replays it
    on subsequent requests, emulating a browser over TLS without changing the
    server's production cookie settings. It is strictly for this rehearsal.

    ``base_url`` may change across container replacements (the port differs);
    the stored cookie is preserved so the same owner identity is reused.
    """

    def __init__(self, base_url: str, timeout: float = 15.0):
        self._timeout = timeout
        self._cookie: str | None = None
        self.retarget(base_url)

    def retarget(self, base_url: str) -> None:
        """Point the same owner (cookie kept) at a new container URL."""
        parts = urlsplit(base_url)
        self._host = parts.hostname
        self._port = parts.port

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


class Rehearsal:
    """Owns exactly the containers it starts; provides robust, isolated cleanup.

    Container names carry a unique per-run token so this run can only ever
    remove its own containers — it never force-removes a fixed name that another
    run might own.
    """

    def __init__(self, image: str, run_docker=_run):
        self.image = image
        self._run = run_docker
        self.token = uuid.uuid4().hex[:12]
        self._started: list[str] = []

    def container_name(self, role: str) -> str:
        return f"dakikobo-journal-{self.token}-{role}"

    def start(self, role: str, mount: Path, port: int) -> str:
        """Start one container on an isolated mount and wait until healthy."""
        name = self.container_name(role)
        mount.mkdir(parents=True, exist_ok=True)
        # World-writable so the unprivileged container user (uid 1000) can create
        # the SQLite journal in the bind mount; it is a throwaway temp dir.
        os.chmod(mount, 0o777)
        self._run(
            [
                # --rm is defensive: if this process is killed before cleanup
                # runs, the container is still auto-removed once it stops.
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
                self.image,
            ],
            timeout=60,
        )
        self._started.append(name)
        _wait_healthy(name, port)
        return f"http://127.0.0.1:{port}"

    def stop(self, role: str) -> None:
        """Remove one owned container now (used for the deliberate replacement).

        Only untracks the container after `docker rm -f` is confirmed
        successful; a nonzero exit or timeout raises so the caller does not
        proceed with a container that may still be running.
        """
        name = self.container_name(role)
        self._remove_one(name)
        self._started = [n for n in self._started if n != name]

    def _remove_one(self, name: str) -> None:
        # Each removal has its own timeout so a single stuck container cannot
        # prevent the others from being cleaned up. `docker rm -f` can return a
        # nonzero exit WITHOUT raising (check=False), so we must inspect the
        # return code: a nonzero result means the container was not confirmed
        # removed and may still be running.
        result = self._run(
            ["docker", "rm", "-f", name], timeout=REMOVE_TIMEOUT, check=False
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[:_STDERR_LIMIT]
            raise RemovalFailed(
                f"docker rm -f {name} exited {result.returncode}: {stderr}"
            )

    @property
    def has_pending_containers(self) -> bool:
        """True while any started container has not been confirmed removed."""
        return bool(self._started)

    def cleanup(self) -> list[str]:
        """Remove every container this run started, independently.

        Returns a list of human-readable cleanup errors (empty when clean). A
        timeout, nonzero exit, or exception removing one container never skips
        the others, and a container is untracked only after confirmed removal.
        """
        errors: list[str] = []
        for name in list(self._started):
            try:
                self._remove_one(name)
                self._started.remove(name)  # only after confirmed success
            except subprocess.TimeoutExpired:
                errors.append(f"timed out removing container {name}")
            except RemovalFailed as exc:
                errors.append(str(exc))
            except Exception as exc:  # keep cleaning the rest regardless
                errors.append(f"failed to remove container {name}: {exc}")
        return errors


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


def _run_checks(rehearsal: Rehearsal, mount: Path, empty_mount: Path) -> dict:
    """The rehearsal body; assumes containers are cleaned up by the caller."""
    summary: dict = {}

    # 1) First container: save one consented synthetic case, keep the cookie.
    base_url = rehearsal.start("a", mount, _free_port())
    owner = SecureCookieClient(base_url)
    case_id = _save_synthetic_case(owner)
    if len(_owner_cases(owner)) != 1:
        raise RehearsalError("Expected exactly one case before replacement")
    rehearsal.stop("a")  # deliberate stop + remove before the replacement

    # 2) Replacement container: same image, secret, and mount. The owner's case
    #    must still be there; a different visitor must not see it.
    owner.retarget(rehearsal.start("b", mount, _free_port()))
    after = _owner_cases(owner)
    summary["owner_case_survived_replacement"] = (
        len(after) == 1 and after[0]["feedback_id"] == case_id
    )
    other = owner.clone_without_cookie()
    summary["other_client_sees_no_case"] = _owner_cases(other) == []
    other_delete = other.delete(f"/journal/{case_id}")
    summary["non_owner_delete_is_noop"] = (
        other_delete["status"] == 200 and other_delete["json"].get("deleted") == 0
    )
    summary["case_intact_after_non_owner_delete"] = len(_owner_cases(owner)) == 1

    # 3) Negative control WITH the positive mount still holding the case: the
    #    SAME owner cookie must see the case on the populated replacement mount
    #    and NO case on a fresh empty mount served by a separate container.
    positive_base = _owner_base(owner)  # the "b" replacement, still populated
    empty_base = rehearsal.start("control", empty_mount, _free_port())
    # Owner still sees the case on the positive (populated) mount.
    summary["owner_sees_case_on_positive_mount"] = len(_owner_cases(owner)) == 1
    # Same owner cookie, fresh empty mount: no case leaks across mounts.
    owner.retarget(empty_base)
    summary["same_owner_sees_no_case_on_empty_mount"] = _owner_cases(owner) == []
    # Re-point at the positive mount and confirm the case is still intact.
    owner.retarget(positive_base)
    summary["positive_case_intact_after_control"] = len(_owner_cases(owner)) == 1

    # 4) Owner deletion happens AFTER the negative-control checks.
    owner_delete = owner.delete(f"/journal/{case_id}")
    summary["owner_delete_succeeds"] = (
        owner_delete["status"] == 200 and owner_delete["json"].get("deleted") == 1
    )
    summary["case_removed_after_owner_delete"] = _owner_cases(owner) == []
    return summary


def _owner_base(owner: SecureCookieClient) -> str:
    return f"http://{owner._host}:{owner._port}"


def rehearse(image: str, *, rehearsal: Rehearsal | None = None) -> dict:
    """Run the full continuity rehearsal and strengthened negative control.

    Containers are always cleaned up before mount data is removed; cleanup
    errors are reported while preserving any original failure.
    """
    rehearsal = rehearsal or Rehearsal(image)
    workspace = Path(tempfile.mkdtemp(prefix="dakikobo-docker-"))
    mount = workspace / "mount"
    empty_mount = workspace / "empty-mount"
    primary_error: BaseException | None = None
    summary: dict = {}
    try:
        summary = _run_checks(rehearsal, mount, empty_mount)
    except BaseException as error:
        primary_error = error
    finally:
        # Remove all owned containers FIRST (independently). Only delete the
        # bind-mount data once every owned container removal is confirmed: a
        # container still running could hold the mount in use, so withhold the
        # deletion and report it rather than deleting data under a live mount.
        cleanup_errors = rehearsal.cleanup()
        if rehearsal.has_pending_containers:
            cleanup_errors.append(
                "withheld mount cleanup: unconfirmed containers still owned "
                f"({', '.join(rehearsal._started)}); left {workspace}"
            )
        else:
            # Delete the temp workspace, but never silently: a filesystem
            # cleanup failure is reported (bounded) with the preserved path so
            # a leftover mount is visible, and any primary error still wins.
            try:
                shutil.rmtree(workspace)
            except OSError as exc:
                cleanup_errors.append(
                    f"failed to remove workspace {workspace}: "
                    f"{str(exc)[:_CLEANUP_MESSAGE_LIMIT]}"
                )

    if primary_error is not None:
        # Preserve the original error; attach cleanup problems as context.
        if cleanup_errors:
            raise RehearsalError(
                f"{primary_error} (additional cleanup errors: "
                f"{'; '.join(cleanup_errors)})"
            ) from primary_error
        if isinstance(primary_error, (RehearsalError, subprocess.TimeoutExpired)):
            raise primary_error
        raise RehearsalError(str(primary_error)) from primary_error

    if cleanup_errors:
        raise CleanupError("; ".join(cleanup_errors))

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
    except (RehearsalError, CleanupError, RemovalFailed, subprocess.TimeoutExpired) as error:
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
