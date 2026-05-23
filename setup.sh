#!/usr/bin/env bash
set -e

echo "=== mp4maker setup (macOS/Linux) ==="
echo

# ---- 1. Python check --------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 not found."
    echo "  macOS:  brew install python@3.12"
    echo "  Ubuntu: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi
PYVER=$(python3 --version 2>&1 | awk '{print $2}')
echo "[ok] Python ${PYVER}"

# ---- 2. Virtual env ---------------------------------------------------
if [ ! -d .venv ]; then
    echo "[..] Creating virtual environment in .venv/"
    python3 -m venv .venv
else
    echo "[ok] .venv/ already exists"
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# ---- 3. Dependencies --------------------------------------------------
echo "[..] Upgrading pip"
python -m pip install --upgrade pip --quiet --disable-pip-version-check

echo "[..] Installing requirements"
pip install -r requirements.txt --quiet --disable-pip-version-check
echo "[ok] Python packages installed"

# ---- 4. ffmpeg check --------------------------------------------------
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo
    echo "[WARN] ffmpeg not found on PATH."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "       Install with:  brew install ffmpeg"
    else
        echo "       Install with:  sudo apt install ffmpeg   (Debian/Ubuntu)"
        echo "                  or: sudo dnf install ffmpeg   (Fedora)"
    fi
else
    FFVER=$(ffmpeg -version 2>&1 | head -n1 | awk '{print $3}')
    echo "[ok] ffmpeg ${FFVER}"
fi

# ---- 5. _assets check -------------------------------------------------
if [ ! -d _assets ]; then
    echo
    echo "[info] _assets/ not found. Creating empty folder."
    echo "       Put your chNN_bundle directories inside _assets/ before running."
    mkdir _assets
else
    echo "[ok] _assets/ exists"
fi

echo
echo "=== setup complete ==="
echo "Next:  ./run.sh         (launches the web UI in your browser)"
echo "or:    source .venv/bin/activate && python -m mp4maker --probe"
