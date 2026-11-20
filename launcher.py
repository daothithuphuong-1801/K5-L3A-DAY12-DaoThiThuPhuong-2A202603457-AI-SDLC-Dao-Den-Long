"""Entry point for packaged builds (PyInstaller). Same CLI as `python -m game.app`."""
import sys

from game import app

if __name__ == "__main__":
    sys.exit(app.main() or 0)
