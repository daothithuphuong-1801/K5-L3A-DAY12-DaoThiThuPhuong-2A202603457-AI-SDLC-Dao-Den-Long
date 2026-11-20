"""Benchmark (Ticket-04 §1): python3 -m game.bench --seed 42 --duration 30 --out bench.json

1280x720 window, vsync off, Night 1 with full lighting/effects, 200 wander shades + 100 motes (seed),
L1-L3 lit with fuel 100; no spawns/damage/pickup/fuel use/end of night; Mây idle at (0,0,0);
camera orbits (0,0,0) at r = 30 m, y = 15 m, starting at (30,15,0), counter-clockwise, 15 s per lap.
3 s warm-up, then --duration seconds are measured; writes bench.json and exits 0.
"""
import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.core import sysinfo  # noqa: F401  (records the import time as a fallback process start)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="game.bench")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--out", default="bench.json")
    a = ap.parse_args(argv)
    from game import app
    return app.main(["--bench-scene", "--seed", str(a.seed), "--duration", str(a.duration), "--out", a.out,
                     "--size", "1280x720", "--night", "1"])


if __name__ == "__main__":
    sys.exit(main() or 0)
