@echo off
rem One-command launcher (Windows): creates a local venv on first run, then starts the game.
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
  .venv\Scripts\python -m pip install -q -r requirements.txt
)
.venv\Scripts\python -m game.app %*
