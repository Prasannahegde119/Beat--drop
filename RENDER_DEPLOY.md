# BeatDrop engine on Render — complete deployment guide

Result: a permanent https URL that the BeatDrop 1.0.2 app talks to. The
server is protected by a shared API token; nothing else on the internet can
use your engine.

## What you need

- A GitHub account (free) and git on your laptop, OR just the GitHub website
- The contents of `BeatDrop-backend.zip` (this folder)
- The BeatDrop **1.0.2** APK (the token field only exists from 1.0.2 onward)

## Step 1 — Put the backend on GitHub

### Easy route (website, no git commands)
1. github.com → New repository → name it `beatdrop-engine` → Private → Create.
2. On the empty repo page choose **uploading an existing file**.
3. Drag in everything from the `backend` folder: `app.py`, `requirements.txt`,
   `Procfile`, `render.yaml`, `.gitignore`, plus the `termux/` and `tests/`
   folders (the extras do no harm; Render only uses the first four).
4. Commit changes.

### Laptop route (git CLI)
```bash
unzip BeatDrop-backend.zip && cd backend
git init && git add . && git commit -m "BeatDrop media engine"
gh repo create beatdrop-engine --private --source=. --push
# or create an empty repo on github.com first, then:
# git remote add origin git@github.com:<you>/beatdrop-engine.git
# git push -u origin main
```

## Step 2 — Create the Render service

1. render.com → sign up free (use "Sign in with GitHub" and authorize Render).
2. Dashboard → **New + → Blueprint**.
3. Pick the `beatdrop-engine` repo. Render reads `render.yaml` and proposes a
   free web service named `beatdrop-engine`.
4. When prompted for the missing environment variable, add:
   - Key: `BEATDROP_API_TOKEN`
   - Value: a long random string you choose (e.g. 32+ letters/numbers —
     generate one with `openssl rand -hex 24` on the laptop). This is the
     same value the app will send. Treat it like a password.
5. Apply/Deploy. First build takes 3–6 minutes (installs Flask, gunicorn,
   yt-dlp). You end up with:
   `https://beatdrop-engine-xxxx.onrender.com`

Alternative if Blueprint doesn't appear: New + → **Web Service** → connect
the repo → Runtime Python → Build command `pip install -r requirements.txt`
→ Start command `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
→ Free plan → add the same env var → Deploy.

## Step 3 — Verify the server from a browser

- Open `https://<your-service>.onrender.com/api/health` → `{"status":"ok"}`
  (first hit after idle may take up to a minute while it wakes).
- Open `https://<your-service>.onrender.com/api/search?q=test` →
  `{"error":"Unauthorized"}` — that 401 proves the token guard works.

## Step 4 — Connect the BeatDrop app (1.0.2)

1. Install/open BeatDrop 1.0.2 → **Settings → Media engine (backend)**.
2. Backend URL: `https://beatdrop-engine-xxxx.onrender.com` (no trailing
   slash, use https).
3. API token: the exact `BEATDROP_API_TOKEN` value from Step 2.
4. **Save & test** → "Engine reachable". If the service was asleep, the
   first tap can time out — wait a minute and tap again; the health call
   itself wakes the service.
5. Search works from anywhere — the phone no longer needs to be near a PC.

## Step 5 — Keeping it working

- **Free-tier sleep:** the service idles after ~15 min without traffic and
  cold-starts in 30–60 seconds on the next request. The app's API timeout is
  set to 70 s to absorb this. Optional: add the `/api/health` URL to a free
  uptime monitor (UptimeRobot, 10-minute interval) to keep it warm.
- **yt-dlp freshness:** platforms change often. `requirements.txt` allows
  newer yt-dlp on each deploy; to force an update, bump it in the repo and
  push, or click Manual Deploy → Clear build cache.
- **Datacenter blocking:** some platforms (notably YouTube) occasionally
  challenge Render's server IPs. If a specific source fails with a bot/403
  message, that's the platform blocking cloud IPs — direct media links and
  other sources keep working, and the Termux/PC run modes remain fallbacks.
- **Token safety:** never commit the token itself; it lives only in Render's
  environment variables and the app's local DataStore.
- **Logs and cost:** Render's Logs tab shows every request (errors are short
  messages, never stack traces). The free plan costs nothing; usage limits
  are generous for personal use.

## Security recap

Only http(s) URLs are accepted; login/private/DRM content is refused, never
bypassed; the token gates every data endpoint while the health check stays
open for monitors; no analytics and no stored media — the engine only
resolves and redirects, the phone does the actual downloading.
