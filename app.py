"""
BeatDrop media engine — Flask + yt-dlp backend.

Serves the Android app's search / format-info / streaming needs.
Security posture:
  * Binds to loopback (127.0.0.1) by default; never expose unauthenticated.
  * Only http(s) URLs are accepted and every external URL is validated.
  * Errors return short messages, never stack traces.
  * No analytics, no logging of full signed media URLs beyond warnings.

FFmpeg is optional: required only for merging separate audio/video streams
and for MP3 conversion. Such formats are flagged "proxied" and served via
/api/stream; direct progressive/streamable URLs are passed straight through.
"""
from __future__ import annotations

import logging
import os
import re
from urllib.parse import quote, urlparse

from flask import Flask, jsonify, request, Response
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("beatdrop")

app = Flask(__name__)

PAGE_SIZE = 10
URL_RE = re.compile(r"^https?://", re.IGNORECASE)
AUDIO_EXTS = {"m4a", "mp3", "opus", "ogg", "aac", "flac", "webm"}
VIDEO_EXTS = {"mp4", "webm", "mkv", "3gp", "mov", "m4v"}


def _valid_url(url: str) -> bool:
    if not url or not URL_RE.match(url.strip()):
        return False
    parsed = urlparse(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def _require_auth():
    """Optional shared-secret guard for public hosting (e.g. Render).

    Set BEATDROP_API_TOKEN on the server; the app then sends the same value
    in the X-API-Key header. Unset (the local/Termux default) = open access.
    /api/health stays open so connectivity checks and host probes work.
    """
    token = os.environ.get("BEATDROP_API_TOKEN", "").strip()
    if not token:
        return None
    provided = (
        request.headers.get("X-API-Key", "").strip()
        or request.args.get("token", "").strip()
    )
    if provided != token:
        log.warning("rejected request with missing/incorrect API token")
        return _error("Unauthorized", 401)
    return None


def _base_ydl_opts() -> dict:
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "retries": 2,
        # BeatDrop never bypasses access controls: cookies/auth are not wired in.
    }


def _media_type_for_ext(ext: str) -> str:
    ext = (ext or "").lower()
    if ext in VIDEO_EXTS:
        return "VIDEO"
    return "AUDIO"


def _entry_to_result(entry: dict) -> dict | None:
    source_url = entry.get("webpage_url") or entry.get("url") or entry.get("original_url")
    title = entry.get("title")
    if not source_url or not title or not _valid_url(source_url):
        return None
    duration = entry.get("duration")
    return {
        "id": str(entry.get("id") or source_url),
        "title": title,
        "creator": entry.get("uploader") or entry.get("channel") or entry.get("artist"),
        "duration_ms": int(duration * 1000) if duration else None,
        "thumbnail_url": entry.get("thumbnail"),
        "media_type": _media_type_for_ext(entry.get("ext") or ""),
        "source_url": source_url,
    }


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/search")
def search():
    auth_error = _require_auth()
    if auth_error is not None:
        return auth_error
    query = (request.args.get("q") or "").strip()
    if not query:
        return _error("Missing query parameter 'q'")
    try:
        page = max(0, int(request.args.get("page", 0)))
    except ValueError:
        return _error("Parameter 'page' must be an integer")

    # Anything that looks like a URL but fails validation is rejected outright.
    if "://" in query and not _valid_url(query):
        return _error("Only http(s) URLs are accepted")

    # A pasted direct link short-circuits to a single synthetic result.
    if _valid_url(query):
        ext = query.split("?", 1)[0].rsplit(".", 1)[-1].lower()
        if ext in AUDIO_EXTS or ext in VIDEO_EXTS:
            name = query.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
            return jsonify({
                "results": [{
                    "id": query,
                    "title": name.rsplit(".", 1)[0] or "Direct media",
                    "creator": None,
                    "duration_ms": None,
                    "thumbnail_url": None,
                    "media_type": _media_type_for_ext(ext),
                    "source_url": query,
                }],
                "page": 0,
                "has_more": False,
            })
        if not any(host in query for host in ("youtube.com", "youtu.be", "vimeo.com", "soundcloud.com")):
            return _error("Unsupported source URL")

    fetch = PAGE_SIZE * (page + 1)
    opts = _base_ydl_opts()
    opts["extract_flat"] = "in_playlist"
    opts["skip_download"] = True
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{fetch}:{query}", download=False)
    except (DownloadError, ExtractorError) as exc:
        log.warning("search failed: %s", type(exc).__name__)
        return _error("The media source could not be searched. Try again later.", 502)
    except Exception:  # defensive: never leak a trace to the app
        log.exception("unexpected search failure")
        return _error("The media engine failed unexpectedly.", 500)

    entries = (info or {}).get("entries") or []
    page_entries = entries[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    results = [r for r in (_entry_to_result(e) for e in page_entries) if r]
    return jsonify({
        "results": results,
        "page": page,
        "has_more": len(entries) >= fetch,
    })


def _format_to_dto(f: dict) -> dict | None:
    url = f.get("url")
    format_id = f.get("format_id")
    ext = (f.get("ext") or "").lower()
    if not url or not format_id or not ext:
        return None
    vcodec = f.get("vcodec")
    acodec = f.get("acodec")
    is_video = vcodec and vcodec != "none"
    needs_merge = is_video and (not acodec or acodec == "none")
    height = f.get("height")
    abr = f.get("abr")

    if is_video:
        label = f"{height}p {ext.upper()}" if height else f"{ext.upper()} video"
        mime = f"video/{'mp4' if ext == 'm4a' else ext}"
    else:
        bitrate = f" {int(abr)}kbps" if abr else ""
        label = f"{ext.upper()}{bitrate} audio"
        mime = f"audio/{'mp4' if ext == 'm4a' else ext}"

    size = f.get("filesize") or f.get("filesize_approx")

    return {
        "format_id": format_id,
        "label": label + (" (merged)" if needs_merge else ""),
        "media_type": "VIDEO" if is_video else "AUDIO",
        "ext": ext,
        "mime_type": mime,
        "estimated_bytes": int(size) if size else None,
        # Proxied URLs are rewritten by /api/info once the source URL is known.
        "stream_url": url,
        "proxied": needs_merge,
    }


@app.get("/api/info")
def info():
    auth_error = _require_auth()
    if auth_error is not None:
        return auth_error
    source_url = (request.args.get("u") or "").strip()
    if not _valid_url(source_url):
        return _error("Parameter 'u' must be a valid http(s) URL")

    ext = source_url.split("?", 1)[0].rsplit(".", 1)[-1].lower()
    if ext in AUDIO_EXTS or ext in VIDEO_EXTS:
        # Direct file: the only format is the file itself.
        return jsonify({
            "result": {
                "id": source_url,
                "title": source_url.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1].rsplit(".", 1)[0],
                "creator": None,
                "duration_ms": None,
                "thumbnail_url": None,
                "media_type": _media_type_for_ext(ext),
                "source_url": source_url,
            },
            "description": None,
            "formats": [{
                "format_id": "direct",
                "label": f"Original .{ext}",
                "media_type": _media_type_for_ext(ext),
                "ext": ext,
                "mime_type": f"{'video' if ext in VIDEO_EXTS else 'audio'}/{ext}",
                "estimated_bytes": None,
                "stream_url": source_url,
                "proxied": False,
            }],
        })

    opts = _base_ydl_opts()
    opts["skip_download"] = True
    try:
        with YoutubeDL(opts) as ydl:
            full = ydl.extract_info(source_url, download=False)
    except (DownloadError, ExtractorError) as exc:
        msg = str(exc).lower()
        if "private" in msg or "login" in msg or "403" in msg:
            return _error("Access to this media is restricted. BeatDrop does not bypass access controls.", 403)
        log.warning("info failed: %s", type(exc).__name__)
        return _error("No downloadable formats were found for this media.", 502)
    except Exception:
        log.exception("unexpected info failure")
        return _error("The media engine failed unexpectedly.", 500)

    raw_formats = full.get("formats") or []
    seen: set[str] = set()
    formats = []
    for f in raw_formats:
        dto = _format_to_dto(f)
        if not dto:
            continue
        if dto["proxied"]:
            dto["stream_url"] = (
                f"/api/stream?u={quote(source_url, safe='')}"
                f"&format_id={dto['format_id']}"
            )
        key = (dto["media_type"], dto["label"])
        if key in seen:
            continue
        seen.add(key)
        formats.append(dto)

    # Keep the list digestible: best few audio + video options.
    audio = [f for f in formats if f["media_type"] == "AUDIO"][:6]
    video = [f for f in formats if f["media_type"] == "VIDEO"][-8:]
    result = _entry_to_result(full)
    if result is None:
        return _error("The source returned an unreadable media item.", 502)
    return jsonify({
        "result": result,
        "description": full.get("description"),
        "formats": audio + video,
    })


@app.get("/api/stream")
def stream():
    """Resolve a format's playable URL and redirect to it.

    Separately muxed streams (proxied=True) cannot be served without an
    FFmpeg transcode pipeline; the app is told this explicitly instead of
    being handed a URL that does not contain both tracks.
    """
    source_url = (request.args.get("u") or "").strip()
    format_id = (request.args.get("format_id") or "").strip()
    auth_error = _require_auth()
    if auth_error is not None:
        return auth_error
    if not _valid_url(source_url) or not format_id:
        return _error("Both 'u' and 'format_id' are required")

    try:
        with YoutubeDL({**_base_ydl_opts(), "format": format_id}) as ydl:
            info = ydl.extract_info(source_url, download=False)
    except (DownloadError, ExtractorError):
        log.warning("stream resolution failed for format %s", format_id)
        return _error("Could not resolve the stream URL.", 502)
    except Exception:
        log.exception("unexpected stream failure")
        return _error("The media engine failed unexpectedly.", 500)

    direct = info.get("url") if info else None
    if not direct:
        return _error(
            "This format needs server-side FFmpeg merging. Pick a progressive format instead.",
            422,
        )
    return Response(status=302, headers={"Location": direct})


if __name__ == "__main__":
    host = os.environ.get("BEATDROP_HOST", "127.0.0.1")
    # Render (and similar PaaS) inject $PORT and require binding 0.0.0.0.
    port = int(os.environ.get("BEATDROP_PORT") or os.environ.get("PORT") or "5001")
    if host not in ("127.0.0.1", "localhost"):
        # LAN/public bind: only do this on a trusted network or behind a
        # platform gateway with BEATDROP_API_TOKEN configured. There is no
        # user-account auth layer.
        log.warning(
            "Binding BeatDrop engine to %s — ensure this is a trusted private network", host
        )
    app.run(host=host, port=port, threaded=True)
