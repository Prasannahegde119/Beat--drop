#!/data/data/com.termux/files/usr/bin/bash
# BeatDrop media engine — one-time Termux setup (run ONCE on the phone).
# Usage after copying the backend folder onto the phone:
#   bash ~/beatdrop-src/termux/setup_beatdrop.sh
set -e

SRC="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HOME/beatdrop-backend"

echo "==> [1/5] Updating Termux packages"
pkg update -y
pkg install -y python ffmpeg

echo "==> [2/5] Installing engine into $DEST"
mkdir -p "$DEST"
cp -f "$SRC/app.py" "$SRC/requirements.txt" "$DEST/"

echo "==> [3/5] Installing Python dependencies (flask + yt-dlp)"
cd "$DEST"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo "==> [4/5] Installing one-tap launcher, status/stop helpers and boot autostart"
mkdir -p "$HOME/.shortcuts" "$HOME/.termux/boot"
cp -f "$SRC/termux/start_beatdrop.sh" "$HOME/.shortcuts/start_beatdrop.sh"
cp -f "$SRC/termux/status_beatdrop.sh" "$HOME/.shortcuts/status_beatdrop.sh"
cp -f "$SRC/termux/stop_beatdrop.sh" "$HOME/.shortcuts/stop_beatdrop.sh"
cp -f "$SRC/termux/start_beatdrop.sh" "$HOME/.termux/boot/start_beatdrop.sh"
chmod +x "$HOME/.shortcuts/"*.sh "$HOME/.termux/boot/start_beatdrop.sh"

# Keep Termux awake so Android does not kill the engine when the screen sleeps.
termux-wake-lock

echo "==> [5/5] Starting the engine now"
echo "    In BeatDrop app → Settings → Media engine set: http://127.0.0.1:5001"
exec bash "$HOME/.shortcuts/start_beatdrop.sh"
