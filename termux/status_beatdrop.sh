#!/data/data/com.termux/files/usr/bin/bash
# BeatDrop engine health check — run anytime in Termux.
echo "== Process =="
if pgrep -af "python app.py" >/dev/null; then
    pgrep -af "python app.py"
else
    echo "Not running. Start it with: bash ~/.shortcuts/start_beatdrop.sh"
    exit 1
fi
echo "== Health endpoint =="
curl -s --max-time 5 http://127.0.0.1:5001/api/health && echo
