"""Stop hook: block the agent from finishing while tests are red (exit 2 = feedback to agent)."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x"], cwd=root, capture_output=True, text=True)
if r.returncode != 0:
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-25:])
    print(f"Tests are failing - fix them before finishing (do not weaken tests):\n{tail}", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
