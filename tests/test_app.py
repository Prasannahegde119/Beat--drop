"""Offline pytest suite for the BeatDrop media engine.

yt_dlp.YoutubeDL is replaced by a deterministic fake, so no network and no
third-party platform is ever touched by these tests.
"""
import sys
from pathlib import Path
from unittest import mock

import pytest
from yt_dlp.utils import DownloadError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as backend  # noqa: E402


@pytest.fixture()
def client():
    backend.app.config["TESTING"] = True
    return backend.app.test_client()


class FakeYDL:
    """Deterministic stand-in for yt_dlp.YoutubeDL used across the suite."""

    search_payload = {
        "entries": [
            {
                "id": "vid-1",
                "title": "First Song",
                "uploader": "Alice",
                "duration": 210,
                "ext": "m4a",
                "thumbnail": "https://img.example/1.jpg",
                "webpage_url": "https://youtube.com/watch?v=vid-1",
            },
            {
                "id": "vid-2",
                "title": "Second Video",
                "channel": "Bob",
                "duration": None,
                "ext": "mp4",
                "url": "https://vimeo.com/12345",
            },
            # Entries lacking a usable URL/title must be filtered, not fabricated.
            {"id": "broken", "title": None, "url": "https://example.com/x"},
        ]
    }

    info_payload = {
        "id": "vid-1",
        "title": "First Song",
        "uploader": "Alice",
        "duration": 210,
        "webpage_url": "https://youtube.com/watch?v=vid-1",
        "formats": [
            {
                "format_id": "140",
                "ext": "m4a",
                "acodec": "mp4a",
                "vcodec": "none",
                "abr": 128,
                "url": "https://cdn.example/audio.m4a",
                "filesize": 2_500_000,
            },
            {
                "format_id": "136",
                "ext": "mp4",
                "acodec": "none",
                "vcodec": "avc1",
                "height": 720,
                "url": "https://cdn.example/video-only.mp4",
                "filesize_approx": 9_000_000,
            },
            {
                "format_id": "18",
                "ext": "mp4",
                "acodec": "mp4a",
                "vcodec": "avc1",
                "height": 360,
                "url": "https://cdn.example/progressive.mp4",
                "filesize": 12_000_000,
            },
        ],
    }

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=False):
        if url.startswith("ytsearch"):
            return self.search_payload
        if self.opts.get("format"):
            return {"url": "https://cdn.example/resolved-stream"}
        return self.info_payload


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_search_requires_query(client):
    resp = client.get("/api/search")
    assert resp.status_code == 400
    assert "q" in resp.get_json()["error"]


def test_search_rejects_non_http(client):
    resp = client.get("/api/search?q=ftp://example.com/file.mp3")
    assert resp.status_code == 400
    assert "http(s)" in resp.get_json()["error"]


def test_search_maps_entries_without_fabrication(client):
    with mock.patch.object(backend, "YoutubeDL", FakeYDL):
        resp = client.get("/api/search?q=jazz&page=0")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["page"] == 0
    # Two valid entries; the malformed one is dropped rather than invented.
    assert len(body["results"]) == 2
    first = body["results"][0]
    assert first["title"] == "First Song"
    assert first["creator"] == "Alice"
    assert first["duration_ms"] == 210_000
    assert first["media_type"] == "AUDIO"
    assert first["source_url"].startswith("https://")


def test_search_direct_link_short_circuit(client):
    url = "https://files.example.org/album/track.mp3"
    ydl_mock = mock.MagicMock(side_effect=FakeYDL)
    with mock.patch.object(backend, "YoutubeDL", ydl_mock):
        resp = client.get(f"/api/search?q={url}")
        ydl_mock.assert_not_called()
    assert resp.status_code == 200
    results = resp.get_json()["results"]
    assert len(results) == 1
    assert results[0]["source_url"] == url
    assert results[0]["media_type"] == "AUDIO"
    assert resp.get_json()["has_more"] is False


def test_info_validates_url(client):
    resp = client.get("/api/info?u=not-a-url")
    assert resp.status_code == 400
    resp2 = client.get("/api/info")
    assert resp2.status_code == 400


def test_info_reports_real_formats_and_flags_merge(client):
    with mock.patch.object(backend, "YoutubeDL", FakeYDL):
        resp = client.get("/api/info?u=https://youtube.com/watch?v=vid-1")
    assert resp.status_code == 200
    body = resp.get_json()
    labels = {f["label"] for f in body["formats"]}
    assert any("audio" in label for label in labels)
    video_only = next(f for f in body["formats"] if f["format_id"] == "136")
    # Honest merge flag + proxied stream URL rather than a fake direct link.
    assert video_only["proxied"] is True
    assert video_only["stream_url"].startswith("/api/stream?")
    progressive = next(f for f in body["formats"] if f["format_id"] == "18")
    assert progressive["proxied"] is False
    assert progressive["stream_url"].startswith("https://")


def test_info_direct_file_single_format(client):
    url = "https://files.example.org/clip.webm"
    resp = client.get(f"/api/info?u={url}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["formats"]) == 1
    assert body["formats"][0]["format_id"] == "direct"
    assert body["formats"][0]["stream_url"] == url
    assert body["formats"][0]["proxied"] is False


def test_stream_requires_both_params(client):
    resp = client.get("/api/stream?u=https://example.com/x")
    assert resp.status_code == 400
    resp2 = client.get("/api/stream?format_id=18")
    assert resp2.status_code == 400


def test_stream_redirects_to_resolved_url(client):
    with mock.patch.object(backend, "YoutubeDL", FakeYDL):
        resp = client.get(
            "/api/stream?u=https://youtube.com/watch?v=vid-1&format_id=18"
        )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "https://cdn.example/resolved-stream"


def test_token_auth_enforced_when_configured(client, monkeypatch):
    # Health stays open; every data endpoint requires the shared secret.
    monkeypatch.setenv("BEATDROP_API_TOKEN", "secret")
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/info?u=not-a-url").status_code == 401
    assert client.get(
        "/api/info?u=not-a-url", headers={"X-API-Key": "wrong"}
    ).status_code == 401
    # Correct key passes auth, then ordinary URL validation applies (400).
    ok = client.get("/api/info?u=not-a-url", headers={"X-API-Key": "secret"})
    assert ok.status_code == 400
    monkeypatch.delenv("BEATDROP_API_TOKEN")
    # Without a configured token the engine is open again (local/Termux mode).
    assert client.get("/api/info?u=not-a-url").status_code == 400


def test_search_surfaces_source_failure_as_clean_error(client):
    class FailingYDL(FakeYDL):
        def extract_info(self, url, download=False):
            raise DownloadError("simulated platform outage")

    with mock.patch.object(backend, "YoutubeDL", FailingYDL):
        resp = client.get("/api/search?q=jazz")
    assert resp.status_code == 502
    # User-facing message, never a stack trace.
    assert "Traceback" not in resp.get_data(as_text=True)
