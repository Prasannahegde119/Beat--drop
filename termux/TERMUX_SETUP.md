# BeatDrop + Termux — phone-only setup (tap-by-tap)

Goal: run the BeatDrop media engine on the same phone as the app. The app
talks to `http://127.0.0.1:5001` (device loopback), so nothing is exposed
outside the phone. Needs roughly 300–400 MB free space and ~10 minutes once.

## Part 0 — Install the correct Termux (important)

The Google Play Termux is abandoned and broken. Install from ONE of:

- **F-Droid:** install the F-Droid app (f-droid.org), search "Termux", install
  **Termux**, plus **Termux:Widget** and **Termux:Boot** (used in Part 5).
- **Or GitHub:** github.com/termux/termux-app/releases → download the
  `termux-app_..._github.apk` for your architecture (usually `arm64-v8a`),
  and the matching Termux:Widget / Termux:Boot APKs from their own repos.

## Part 1 — Put the backend files on the phone

1. Download `BeatDrop-backend.zip` on the phone and extract it with the
   Files app (tap the zip → Extract). You end up with a `backend` folder in
   Downloads.
2. Open Termux and run:
   ```bash
   termux-setup-storage
   ```
   A permission popup appears → **Allow**. This maps Downloads to
   `~/storage/downloads`.
3. Copy the folder into Termux home:
   ```bash
   cp -r ~/storage/downloads/backend ~/beatdrop-src
   ls ~/beatdrop-src
   ```
   You should see `app.py`, `requirements.txt`, and a `termux` folder.
   (If your extractor nested the folder, find it with
   `ls ~/storage/downloads` and adjust the source path.)

## Part 2 — One-time installer

```bash
bash ~/beatdrop-src/termux/setup_beatdrop.sh
```

It installs Python, FFmpeg, Flask and yt-dlp, then starts the engine. First
run takes several minutes and downloads packages — keep the screen on.
Success looks like:

```
 * Running on http://127.0.0.1:5001
```

Leave this Termux session running. Pressing **CTRL+C** stops the engine.

## Part 3 — Point the BeatDrop app at it

1. BeatDrop app → **Settings → Media engine (backend)**
2. Enter exactly: `http://127.0.0.1:5001`
3. Tap **Save & test** → status changes to **"Engine reachable"**
4. Go to Search and type a normal text query — platform results now work.
   Direct media links continue to work even if the engine is ever stopped.

## Part 4 — Verify from Termux (if the app says unreachable)

```bash
bash ~/.shortcuts/status_beatdrop.sh
```

Healthy output includes the running `python app.py` process and
`{"status":"ok"}`. Stop the engine with:

```bash
bash ~/.shortcuts/stop_beatdrop.sh
```

## Part 5 — One-tap start and auto-start after reboot

The setup script already placed everything; you just add the UI:

- **Home-screen button:** long-press home screen → Widgets → **Termux Widget**
  → place it → choose `start_beatdrop.sh`. Tapping it starts the engine in
  one tap (same list also contains status/stop helpers).
- **Auto-start on boot:** with **Termux:Boot** installed, start the engine
  once via the widget, then reboot the phone once to register it. From then
  on the engine comes up automatically after every restart.

Also: Android Settings → Apps → **Termux** → Battery → set to
**Unrestricted** (or "Don't optimize"), so the system won't kill it overnight.

## Maintenance

| Task | Command (in Termux) |
|---|---|
| Update platform support | `cd ~/beatdrop-backend && pip install -U yt-dlp` |
| Check engine status | `bash ~/.shortcuts/status_beatdrop.sh` |
| Restart after stopping | `bash ~/.shortcuts/start_beatdrop.sh` |
| View live request logs | They print in the Termux session running the engine |

## Troubleshooting

| Symptom | Fix |
|---|---|
| App: "Unreachable" | Run the status script; if not running, use the widget/start script. Confirm URL is exactly `http://127.0.0.1:5001` |
| `pkg` fails / repository errors | You have the Play Store Termux — replace it with the F-Droid/GitHub build |
| Permission denied reading Downloads | Re-run `termux-setup-storage` and allow the popup |
| Engine dies with screen off or after hours | Re-run `termux-wake-lock` (the start script does this) and set Termux battery to Unrestricted |
| "Address already in use" on start | Another session is running: `bash ~/.shortcuts/stop_beatdrop.sh`, then start again |
| A specific site fails in search | `pip install -U yt-dlp`; or use a direct media link, which never depends on yt-dlp |
| FFmpeg/merge format errors | Confirm `pkg install ffmpeg` succeeded; progressive formats still work without it |
