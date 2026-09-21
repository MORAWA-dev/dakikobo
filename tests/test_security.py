"""Deployment and HTTP security regression tests."""

import os
from pathlib import Path
import subprocess
import sys

import app as app_module


ROOT = Path(__file__).resolve().parents[1]


def test_all_responses_receive_browser_security_headers(monkeypatch):
    monkeypatch.setattr(app_module, "IS_PRODUCTION", True)
    response = app_module.app.test_client().get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" not in response.headers
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")
    assert "object-src 'none'" in response.headers["Content-Security-Policy"]
    assert (
        "frame-ancestors 'self' https://huggingface.co https://*.huggingface.co"
        in response.headers["Content-Security-Policy"]
    )


def test_space_embedding_stays_restricted_to_hugging_face(monkeypatch):
    """Catch headers that make the Hugging Face App tab refuse its iframe."""
    monkeypatch.setattr(app_module, "IS_PRODUCTION", True)
    response = app_module.app.test_client().get("/")
    policy = response.headers["Content-Security-Policy"]

    assert "frame-ancestors 'none'" not in policy
    assert "https://huggingface.co" in policy
    assert "https://*.huggingface.co" in policy
    assert "http:" not in policy


def test_private_demo_is_not_indexed_by_default():
    client = app_module.app.test_client()

    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "User-agent: *\nDisallow: /\n"
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow, noarchive"
    assert b'<meta name="robots" content="noindex, nofollow, noarchive"' in client.get("/").data


def test_sensitive_repository_paths_are_not_web_routes():
    client = app_module.app.test_client()

    for path in ("/.env", "/.git/config", "/config.py", "/data/case_log.sqlite3"):
        response = client.get(path)
        assert response.status_code == 404
        assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_web_process_does_not_load_dotenv(tmp_path):
    (tmp_path / ".env").write_text("GROQ_API_KEY=must-not-load\n", encoding="utf-8")
    environment = os.environ.copy()
    environment.pop("GROQ_API_KEY", None)
    environment["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, "-c", "import config; print(config.GROQ_API_KEY)"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == ""


def test_production_refuses_missing_server_secret(tmp_path):
    environment = os.environ.copy()
    environment.update({"APP_ENV": "production", "PYTHONPATH": str(ROOT)})
    environment.pop("FLASK_SECRET_KEY", None)
    result = subprocess.run(
        [sys.executable, "-c", "import config"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "FLASK_SECRET_KEY must be supplied" in result.stderr


def test_packaging_and_apache_rules_exclude_secrets():
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    apache = (ROOT / ".htaccess").read_text(encoding="utf-8")

    assert ".env" in dockerignore
    assert ".env.*" in dockerignore
    assert "Options -Indexes" in apache
    assert "Require all denied" in apache
    assert "\\.env" in apache
    assert 'RewriteRule "^' in apache
    assert "(?:^|/)" not in apache
