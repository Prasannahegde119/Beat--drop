#!/usr/bin/env bash
# Start the BeatDrop media engine on loopback:5001
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

# FFmpeg is optional but enables merging/conversion.
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "WARNING: ffmpeg not found — merged/MP3 formats will be unavailable."
fi

# Default: loopback only (emulator via adb forward, or local testing).
# To reach the engine from a physical phone on the SAME Wi-Fi, run instead:
#   BEATDROP_HOST=0.0.0.0 ./run_backend.sh
# then set the app's backend URL to http://<this-computer-LAN-IP>:5001
exec python app.py
