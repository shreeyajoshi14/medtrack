#!/usr/bin/env bash
# =========================================================
# MEDTRACK - AWS EC2 FOREGROUND LAUNCH SCRIPT
# Runs Gunicorn directly in terminal for easy debugging.
# =========================================================

if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Starting MedTrack on port 5000..."
gunicorn --workers 3 --bind 0.0.0.0:5000 app:app
