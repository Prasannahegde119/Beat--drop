#!/data/data/com.termux/files/usr/bin/bash
# BeatDrop engine launcher — used by Termux:Widget, Termux:Boot and setup.
# Binds to device loopback: only apps on THIS phone can reach it.
cd "$HOME/beatdrop-backend" || {
    echo "Engine not installed. Run termux/setup_beatdrop.sh first."
    exit 1
}

export BEATDROP_HOST=127.0.0.1
export BEATDROP_PORT=5001
unset BEATDROP_API_TOKEN   # loopback-only: no shared secret needed

termux-wake-lock
echo "============================================================"
echo " BeatDrop media engine running at http://127.0.0.1:5001"
echo " App: Settings -> Media engine -> http://127.0.0.1:5001"
echo " Stop with CTRL+C. Update yt-dlp anytime: pip install -U yt-dlp"
echo "============================================================"
exec python app.py
