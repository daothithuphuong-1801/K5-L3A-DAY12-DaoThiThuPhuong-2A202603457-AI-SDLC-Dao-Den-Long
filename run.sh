#!/usr/bin/env sh
# One-command launcher (macOS / Linux): creates a local venv on first run, then starts the game.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/python -m pip install -q -r requirements.txt
fi
exec ./.venv/bin/python -m game.app "$@"
