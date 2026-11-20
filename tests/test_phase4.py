"""Ticket-04 (contract v1.3): leaderboard, soak, bench scene, settings/keys. No window needed."""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from game.core import leaderboard as lb
from game.core.sim import InputState, Sim

ROOT = Path(__file__).resolve().parents[1]


def test_contract_v13_commands():
    c = json.loads((ROOT / "game.contract.json").read_text(encoding="utf-8"))
    assert c["contract_version"] == "1.3"
    assert c["bench_cmd"] == "python3 -m game.bench" and c["soak_cmd"] == "python3 -m game.soak"
    assert c["tuning"]["night1_duration_s"] == 240  # v1.0-v1.2 keys still there


@pytest.mark.parametrize("name,ok", [("Mai", True), ("ab", False), ("a" * 13, False), ("Ma i", False), ("may_01", True),
                                     ("Mây", True), ("Đăng", True), ("x-y", False)])
def test_leaderboard_name_rule(name, ok):
    assert lb.valid_name(name) is ok


def test_leaderboard_top10_order_ties_persist(tmp_path):
    p = tmp_path / "lb.json"
    t0 = datetime(2026, 11, 20, 10, 0, tzinfo=timezone(timedelta(hours=7)))
    for i, sc in enumerate([300, 500, 500, 100, 900, 50, 700, 200, 400, 600, 800, 10]):
        lb.add(f"P{i:02d}", sc, i % 4, 7 + i, p, now=t0 + timedelta(minutes=i))
    entries = lb.load(p)  # reload from disk = survives restart
    assert len(entries) == 10
    assert [e["score"] for e in entries] == [900, 800, 700, 600, 500, 500, 400, 300, 200, 100]
    assert [e["name"] for e in entries[4:6]] == ["P01", "P02"]  # tie: who achieved it first stays above
    e = entries[0]
    assert set(e) == {"name", "score", "nights_won", "achieved_at", "seed"} and e["achieved_at"].endswith("+07:00")
    _, rank = lb.add("Late", 5, 0, 1, p)
    assert rank is None and len(lb.load(p)) == 10
    with pytest.raises(ValueError):
        lb.add("no", 999, 1, 1, p)


def test_export_leaderboard_cli(tmp_path):
    p, out = tmp_path / "lb.json", tmp_path / "out.json"
    lb.add("Alpha", 120, 1, 7, p)
    lb.add("Beta", 300, 2, 8, p)
    r = subprocess.run([sys.executable, "-m", "game.app", "--export-leaderboard", str(out), "--leaderboard-file", str(p)],
                       cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [e["name"] for e in data["entries"]] == ["Beta", "Alpha"]


def test_soak_short_run(tmp_path):
    out = tmp_path / "soak.json"
    r = subprocess.run([sys.executable, "-m", "game.soak", "--seed", "7", "--nights", "3", "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    s = json.loads(out.read_text(encoding="utf-8"))
    assert s["nights"] == 3 and s["crashes"] == 0 and len(s["results"]) == 3
    assert set(s["results"]) <= {"won", "lost"} and s["mem_end_mb"] <= 1.2 * s["mem_start_mb"]


def test_bench_scene_rules():
    sim = Sim.bench_scene(42)
    assert len(sim.shades) == 200 and len(sim.motes) == 100
    assert all(s.state == "wander" for s in sim.shades)
    assert [l.lit for l in sim.lanterns] == [True, True, True, False, False] and sim.lanterns[0].fuel_u == 6000
    for _ in range(600):
        sim.step(InputState())
    assert sim.state == "playing" and sim.player.flames == 3 and len(sim.motes) == 100 and len(sim.shades) == 200
    assert sim.lanterns[0].fuel_u == 6000 and (sim.player.x, sim.player.z) == (0, 0)
    assert Sim.bench_scene(42).snapshot() == Sim.bench_scene(42).snapshot()  # same seed -> same scene
    assert not Sim(1).bench  # normal sims unaffected (headless output unchanged)


def test_key_conflict_and_defaults(tmp_path):
    from game.view import audio
    keys = dict(audio.DEFAULT_KEYS)
    assert audio.key_conflict(keys, "jump", "e") == "interact" and audio.key_conflict(keys, "jump", "j") is None
    p = tmp_path / "s.json"
    s = audio.load_settings(p)
    assert s["keys"] == audio.DEFAULT_KEYS and s["reduce_motion"] == 0.0 and s["large_text"] == 0.0
    s["keys"]["jump"] = "j"
    s["large_text"] = 1.0
    audio.save_settings(s, p)
    s2 = audio.load_settings(p)
    assert s2["keys"]["jump"] == "j" and s2["large_text"] == 1.0
    bad = dict(s2, keys=dict(audio.DEFAULT_KEYS, jump="e"))
    audio.save_settings(bad, p)
    assert audio.load_settings(p)["keys"] == audio.DEFAULT_KEYS  # duplicate keys in file -> safe defaults
