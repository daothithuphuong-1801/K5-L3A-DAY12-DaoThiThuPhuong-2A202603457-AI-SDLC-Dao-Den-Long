"""Soak test (Ticket-04 §2): python3 -m game.soak --seed 7 --nights 10 --out soak.json

Runs N nights headless in one process (night 1 -> 2 -> 3 rotating); night i (i = 0..N-1) uses seed + i.
Random input from seed + i: new move direction every 30 ticks; per tick 5 % jump, 3 % dash, 2 % pulse,
10 % interact. Each night runs until it ends or for its standard duration.
mem_start_mb = RSS after the first night is loaded; mem_end_mb = RSS after the last night is reset.
"""
import argparse
import gc
import json
import math
import random
import sys
import time
import traceback

if __package__ in (None, ""):
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.core.sim import InputState, Sim
from game.core.sysinfo import rss_mb


def random_input(rng, tick, state):
    if tick % 30 == 0:
        a = rng.uniform(0, 2 * math.pi)
        state["move"] = (math.cos(a), math.sin(a))
    return InputState(move=state["move"], jump=rng.random() < .05, dash=rng.random() < .03,
                      pulse=rng.random() < .02, interact=rng.random() < .10)


def run_night(night, seed):
    sim = Sim(seed, night=night)
    return sim


def play(sim, seed):
    rng = random.Random(seed * 7919 + 1)
    st = {"move": (0.0, 0.0)}
    k = 0
    while sim.state == "playing" and sim.sim_tick < sim.total_ticks:
        sim.step(random_input(rng, k, st))
        k += 1
    return sim.state


def soak(seed, nights):
    t0 = time.perf_counter()
    results, crashes, errors = [], 0, []
    mem_start = None
    for i in range(nights):
        night, s = i % 3 + 1, seed + i
        try:
            sim = run_night(night, s)
            if i == 0:
                gc.collect()
                mem_start = rss_mb()
            results.append(play(sim, s))
        except Exception as e:  # noqa: BLE001 - a crash is counted, the soak continues
            crashes += 1
            results.append("crash")
            errors.append(f"night {i} ({night}, seed {s}): {type(e).__name__}: {e}")
            traceback.print_exc()
        sim = None
        gc.collect()
    mem_end = rss_mb()
    return {"nights": nights, "crashes": crashes, "results": results,
            "mem_start_mb": round(mem_start, 1) if mem_start is not None else None,
            "mem_end_mb": round(mem_end, 1) if mem_end is not None else None,
            "duration_s": round(time.perf_counter() - t0, 2), **({"errors": errors} if errors else {})}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="game.soak")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--nights", type=int, default=10)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    res = soak(a.seed, a.nights)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
