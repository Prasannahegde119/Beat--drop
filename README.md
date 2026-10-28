# BeatDrop media engine

Flask + yt-dlp backend that powers platform search and format resolution for
the BeatDrop Android app. The app also works fully offline for direct media
links; this service only adds text/platform search.

## Endpoints

- `GET /api/health` — open reachability check → `{"status":"ok"}`
- `GET /api/search?q=...&page=0` — text search or direct-link short circuit
- `GET /api/info?u=<url>` — verified downloadable formats (no fabricated data)
- `GET /api/stream?u=<url>&format_id=...` — resolves and 302-redirects to a stream

## Deploy to Render

1. Render dashboard → **New + → Blueprint** → select this repository.
2. Add environment variable `BEATDROP_API_TOKEN` (long random string).
3. Deploy; copy the resulting `https://<service>.onrender.com` URL and the
   token into BeatDrop app → Settings → Media engine.

Full walkthrough: see [`RENDER_DEPLOY.md`](RENDER_DEPLOY.md).
Local PC and Termux run modes: [`README_PC.md`](README_PC.md).

## Security

- Only `http(s)` URLs accepted; DRM, paywall and login-gated media are
  refused, never bypassed.
- When `BEATDROP_API_TOKEN` is set, every data endpoint requires the same
  secret via `X-API-Key` header (or `?token=`); `/api/health` stays open.
- No media is stored, no analytics, errors return short messages only.

## Local development

```bash
pip install -r requirements.txt
python -m pytest tests/        # 12 offline tests, mocked yt-dlp
python app.py                  # http://127.0.0.1:5001
```
