"""Tests for Firecrawl candidate source ingestion."""

import requests

from scripts.firecrawl_ingest import (
    FirecrawlClient,
    FirecrawlIngestError,
    ScrapedPage,
    promote_reviewed_markdown,
    write_pending_markdown,
)


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_firecrawl_client_posts_markdown_scrape_request():
    session = _FakeSession([
        _FakeResponse(
            payload={
                "success": True,
                "data": {
                    "markdown": "# Semis du mil\nContenu agricole.",
                    "metadata": {
                        "title": "Guide semis mil",
                        "sourceURL": "https://example.test/mil",
                        "statusCode": 200,
                    },
                },
            },
        )
    ])
    client = FirecrawlClient(
        api_key="test-key",
        api_url="https://api.firecrawl.test/v2/scrape",
        http_timeout_seconds=5,
        scrape_timeout_ms=12345,
        max_retries=0,
        session=session,
    )

    page = client.scrape("https://example.test/mil")

    assert page.title == "Guide semis mil"
    assert page.url == "https://example.test/mil"
    assert "Semis du mil" in page.markdown
    args, kwargs = session.calls[0]
    assert args[0] == "https://api.firecrawl.test/v2/scrape"
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert kwargs["timeout"] == 5
    assert kwargs["json"]["formats"] == ["markdown"]
    assert kwargs["json"]["onlyMainContent"] is True
    assert kwargs["json"]["removeBase64Images"] is True
    assert kwargs["json"]["timeout"] == 12345


def test_firecrawl_client_retries_retryable_status():
    sleeps = []
    session = _FakeSession([
        _FakeResponse(status_code=429, text="rate limited"),
        _FakeResponse(
            payload={
                "success": True,
                "data": {
                    "markdown": "Contenu final.",
                    "metadata": {"title": "Source finale"},
                },
            },
        ),
    ])
    client = FirecrawlClient(
        api_key="test-key",
        max_retries=1,
        session=session,
        sleep=lambda seconds: sleeps.append(seconds),
    )

    page = client.scrape("https://example.test/source")

    assert page.title == "Source finale"
    assert len(session.calls) == 2
    assert sleeps == [1]


def test_firecrawl_client_wraps_network_error():
    session = _FakeSession([requests.RequestException("offline")])
    client = FirecrawlClient(api_key="test-key", max_retries=0, session=session)

    try:
        client.scrape("https://example.test")
    except FirecrawlIngestError as exc:
        assert "offline" in str(exc)
    else:
        raise AssertionError("network failures should be wrapped")


def test_write_pending_markdown_adds_review_gate(tmp_path):
    page = ScrapedPage(
        url="https://example.test/guide",
        title="Guide agricole",
        markdown="## Contenu\nConseil source.",
        metadata={"statusCode": 200},
        scraped_at="2026-07-02T10:00:00+00:00",
    )

    path = write_pending_markdown(
        page,
        output_dir=tmp_path,
        topics="semis, pluie",
        crops="mil, sorgho",
    )

    text = path.read_text(encoding="utf-8")
    assert 'review_status: "pending_human_review"' in text
    assert "## Review checklist" in text
    assert "<!-- DAKIKOBO_SCRAPED_CONTENT_START -->" in text
    assert "Conseil source." in text
    assert 'topics: "semis, pluie"' in text
    assert 'crops: "mil, sorgho"' in text


def test_promote_reviewed_markdown_removes_pending_checklist(tmp_path):
    page = ScrapedPage(
        url="https://example.test/guide",
        title="Guide agricole",
        markdown="## Contenu\nConseil source.",
        metadata={"statusCode": 200},
        scraped_at="2026-07-02T10:00:00+00:00",
    )
    pending = write_pending_markdown(page, output_dir=tmp_path / "pending")

    reviewed = promote_reviewed_markdown(
        pending,
        reviewer="codex",
        reviewed_dir=tmp_path / "reviewed",
        reviewed_at="2026-07-02T11:00:00+00:00",
    )

    text = reviewed.read_text(encoding="utf-8")
    assert reviewed.parent == tmp_path / "reviewed"
    assert 'review_status: "reviewed_by_codex"' in text
    assert 'reviewed_at: "2026-07-02T11:00:00+00:00"' in text
    assert 'data_format: "markdown"' in text
    assert "## Review checklist" not in text
    assert "<!-- DAKIKOBO_SCRAPED_CONTENT_START -->" not in text
    assert "Conseil source." in text
