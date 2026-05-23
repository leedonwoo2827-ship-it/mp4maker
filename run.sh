#!/usr/bin/env bash
set -e

if [ ! -d .venv ]; then
    echo "[ERROR] .venv/ not found. Run ./setup.sh first."
    exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "[WARN] ffmpeg not on PATH. Rendering will fail until installed."
    echo
fi

echo "Launching mp4maker web UI..."
echo "A browser tab should open at http://localhost:8501"
python -m streamlit run app.py
