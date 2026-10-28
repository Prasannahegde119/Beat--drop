# BeatDrop media engine — deployment guide

This Flask + yt-dlp server powers **text/platform search** in the BeatDrop
Android app. It is optional: pasting a direct media link (ending in
.mp3/.m4a/.mp4/.webm/…) into the app works with no server at all.

Three ways to run it — pick ONE:

| | A. PC + Wi-Fi | B. Termux on the phone | C. Render cloud |
|---|---|---|---|
| Extra hardware | Your computer | None (phone only) | None |
| Always available | While PC is on | While Termux runs | Yes (sleeps when idle) |
| Phone load | None | Medium (Python on phone) | None |
| Internet needed to search | Yes (platform fetch) | Yes | Yes |
| Setup difficulty | Easy | Medium | Medium |
| Cost | Free | Free | Free tier |

---

## Option B — Termux, fully on the phone (recommended for phone-only use)

Everything runs on the handset; the app talks to the engine over device
loopback, so no network exposure at all.

1. Install **Termux from F-Droid or GitHub** (the Google Play version is
   abandoned and broken on modern Android — do not use it).
2. Put the `backend` folder on the phone (e.g. unzip BeatDrop-backend.zip in
   Downloads). In Termux:
   ```bash
   cp -r /sdcard/Download/BeatDrop/backend ~/beatdrop-src
   bash ~/beatdrop-src/termux/setup_beatdrop.sh
   ```
   The one-time installer adds Python + FFmpeg, installs Flask and yt-dlp,
   acquires a wake-lock, and starts the engine.
3. In the BeatDrop app: **Settings → Media engine → `http://127.0.0.1:5001`**
   → Save & test → "Engine reachable".
4. After a reboot, start it again with one tap via the **Termux:Widget**
   home-screen shortcut (`start_beatdrop.sh`). Install Termux:Boot for fully
   automatic start on boot (both add-ons are on F-Droid).

Notes: keep Termux in the recent apps list; the wake-lock keeps the engine
alive with the screen off. Update the extractor periodically:
`pip install -U yt-dlp` inside `~/beatdrop-backend`. The engine listens only
on 127.0.0.1, so no token is needed and nothing is exposed off-device.

---

## Option C — Render free cloud hosting (always-on URL)

1. Push the `backend` folder to a GitHub repository (it includes
   `render.yaml` and is deploy-ready).
2. Render dashboard → **New + → Blueprint** → select the repo.
3. In the service's **Environment** tab add secret:
   `BEATDROP_API_TOKEN` = any long random string you choose.
4. Deploy. You get `https://<your-service>.onrender.com`.
5. App: **Settings → Media engine → that https URL** → Save & test.

Free-tier behavior you must know:
- The service **sleeps after ~15 minutes idle**; the first search after sleep
  takes 30–60 seconds to wake it (subsequent searches are fast).
- Searches run from Render datacenter IPs, which some platforms increasingly
  rate-limit or block ("confirm you're human"). Direct media links and many
  sources still work; if a platform blocks datacenter IPs, Termux/PC mode is
  the fallback.
- Because the URL is public, always set `BEATDROP_API_TOKEN`. The current
  BeatDrop APK does not yet send the token header — if you choose this
  option, ask for a small app rebuild that adds the token field in Settings.
- Merged/MP3 formats need FFmpeg; if those fail on Render, use progressive
  formats or switch the service to a Docker environment with ffmpeg installed.

---

## Option A — PC on the same Wi-Fi (original mode)

### Windows
1. Install Python 3.10+ from python.org — tick **"Add python.exe to PATH"**.
2. Unzip `BeatDrop-backend.zip`, open the `backend` folder.
3. Double-click **`run_backend.bat`** (allows Python through the firewall if
   prompted — private networks only).

### macOS / Linux
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
BEATDROP_HOST=0.0.0.0 ./run_backend.sh
```

Find the PC's LAN IP (`ipconfig` / `ipconfig getifaddr en0` / `ip addr`),
then in the app set `http://<PC-LAN-IP>:5001`. Verify from a browser:
`http://localhost:5001/api/health` → `{"status":"ok"}`.

---

## Files in this package

- `app.py` — the whole server: `/api/health`, `/api/search`, `/api/info`,
  `/api/stream`. Optional token auth via `BEATDROP_API_TOKEN`; reads
  `BEATDROP_HOST`, `BEATDROP_PORT`, and Render's `PORT`.
- `requirements.txt` — pinned `flask` + `yt-dlp`.
- `run_backend.bat` / `run_backend.sh` — PC launchers.
- `termux/setup_beatdrop.sh`, `termux/start_beatdrop.sh` — phone install/run.
- `render.yaml` — Render blueprint.
- `tests/test_app.py` — 12 offline tests (fake yt-dlp, no network).

## Security

Only http(s) URLs accepted; DRM/paywall/login content is refused, never
bypassed; errors are short messages, never stack traces; no analytics and no
logged signed URLs. On public hosting always set the API token; on
loopback/LAN keep the network trusted and stop the server when done.

## Troubleshooting

| Symptom | Fix |
|---|---|
| App says "Unreachable" | Wrong URL/IP, engine not started, or (PC mode) firewall — Termux mode must use exactly `http://127.0.0.1:5001` |
| Termux `pkg` fails | Reinstall Termux from F-Droid/GitHub; Play Store build is broken |
| Engine dies when screen off (Termux) | Run `termux-wake-lock` (the scripts already do) and disable battery optimization for Termux |
| Render first search very slow | Cold start after idle sleep — wait up to a minute |
| yt-dlp platform errors | `pip install -U yt-dlp`, or use a direct media link |
| Port already in use | Set `BEATDROP_PORT=5002` (Termux: edit `start_beatdrop.sh`) and use that port in the app |
| 401 Unauthorized | A token is configured on the server but not sent — unset it for loopback, or use an app build with the token field |
