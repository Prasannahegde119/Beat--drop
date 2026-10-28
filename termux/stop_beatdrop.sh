#!/data/data/com.termux/files/usr/bin/bash
# Stop the BeatDrop media engine.
pkill -f "python app.py" && echo "BeatDrop engine stopped." || echo "No running engine found."
