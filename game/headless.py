"""Headless runner — Test Contract v1.1.

python3 -m game.headless --seed 1 --night 1|2|3 [--scenario s.json] [--inputs i.json]
                         --ticks N --out out.jsonl [--snapshot-every 10]
Exit 0 ok, 2 bad scenario/inputs, 1 other errors (message on stderr).
"""
import argparse
import json
import sys

from game.core.sim import InputState, ScenarioError, Sim

BUTTONS = ("jump", "interact", "pulse", "dash", "pause")


def load_json(path, what):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ScenarioError(f"cannot read {what} file {path}: {e}")


def parse_inputs(data) -> dict[int, dict]:
    """Return {tick: changes}. Validates the contract format."""
    if not isinstance(data, dict) or not isinstance(data.get("frames"), list):
        raise ScenarioError("inputs must be an object with a 'frames' list")
    out, last = {}, -1
    for fr in data["frames"]:
        if not isinstance(fr, dict):
            raise ScenarioError("each frame must be an object")
        tk = fr.get("tick")
        if isinstance(tk, bool) or not isinstance(tk, int) or tk < 0:
            raise ScenarioError(f"frame tick must be a non-negative integer: {fr!r}")
        if tk <= last:
            raise ScenarioError(f"frame ticks must strictly increase (got {tk} after {last})")
        last = tk
        ch = {}
        if "move" in fr:
            mv = fr["move"]
            if (not isinstance(mv, list) or len(mv) != 2
                    or any(isinstance(c, bool) or not isinstance(c, (int, float)) or not -1 <= c <= 1 for c in mv)):
                raise ScenarioError(f"move must be [x, z] with components in [-1, 1]: {fr!r}")
            ch["move"] = (float(mv[0]), float(mv[1]))
        if "cam_yaw_deg" in fr:
            y = fr["cam_yaw_deg"]
            if isinstance(y, bool) or not isinstance(y, (int, float)):
                raise ScenarioError(f"cam_yaw_deg must be a number: {fr!r}")
            ch["cam_yaw_deg"] = float(y)
        for b in BUTTONS:
            if b in fr:
                if not isinstance(fr[b], bool):
                    raise ScenarioError(f"{b} must be boolean: {fr!r}")
                ch[b] = fr[b]
        out[tk] = ch
    return out


def run(seed, night, ticks, out_path, scenario=None, inputs=None, snapshot_every=10):
    sim = Sim(seed=seed, night=night, scenario=scenario)
    frames = parse_inputs(inputs) if inputs is not None else {}
    cur = InputState()
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        def emit(obj):
            f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")

        emit(sim.snapshot())
        emit({"type": "event", "tick": 0, "name": "night_start", "data": {"night": night}})
        for k in range(ticks):
            if k in frames:
                for key, val in frames[k].items():
                    setattr(cur, key, val)
            for ev in sim.step(cur):
                emit(ev)
            if sim.tick % snapshot_every == 0:
                emit(sim.snapshot())
            if sim.state not in ("playing",):
                break
        end_state = "paused" if sim.paused and sim.state == "playing" else sim.state
        emit({"type": "end", "ticks": sim.tick, "state": end_state, "score": sim.score})
    return sim


def main(argv=None):
    ap = argparse.ArgumentParser(prog="game.headless")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--night", type=int, default=1)
    ap.add_argument("--scenario")
    ap.add_argument("--inputs")
    ap.add_argument("--ticks", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--snapshot-every", type=int, default=10)
    a = ap.parse_args(argv)
    try:
        if a.ticks < 0 or a.snapshot_every <= 0:
            raise ScenarioError("--ticks must be >= 0 and --snapshot-every > 0")
        scenario = load_json(a.scenario, "scenario") if a.scenario else None
        inputs = load_json(a.inputs, "inputs") if a.inputs else None
        if inputs is not None:
            parse_inputs(inputs)  # validate before writing anything
        run(a.seed, a.night, a.ticks, a.out, scenario, inputs, a.snapshot_every)
    except ScenarioError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
