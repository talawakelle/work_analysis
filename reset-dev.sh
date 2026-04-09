#!/usr/bin/env bash
set -euo pipefail

echo "Resetting frontend dependencies..."
cd frontend
rm -rf node_modules package-lock.json
npm install

echo "Resetting backend virtual environment..."
cd ../backend
rm -rf .venv
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "Done."
