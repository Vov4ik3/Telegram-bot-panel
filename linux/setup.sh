#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

echo "==================================="
echo " Bot Panel: first-time setup"
echo "==================================="

if [ ! -f venv/bin/python ]; then
    echo "[1/2] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[1/2] Virtual environment already exists."
fi

echo "[2/2] Installing dependencies..."
venv/bin/python -m pip install -r requirements.txt --quiet

echo
echo "Setup complete. Starting the panel now..."
exec "$SCRIPT_DIR/run.sh"
