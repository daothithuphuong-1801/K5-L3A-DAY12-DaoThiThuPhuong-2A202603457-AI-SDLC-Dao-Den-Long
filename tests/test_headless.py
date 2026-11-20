"""Contract v1.2 (Ticket-03 on top of Ticket-02). Tests replaced by Ticket-03 are marked "[T03]" with the reason.
Run: python -m pytest -q"""
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from game.core.sim import InputState, Sim
from game.core.tuning import load_tuning

ROOT = Path(__file__).resolve().parents[1]
SCN = ROOT / "tests" / "scenarios"
T = load_tuning()


def run_cli(tmp_path, *args, scenario=None, inputs=None, ticks=600, seed=1, night=1, name="out"):
    out = tmp_path / f"{name}.jsonl"
    cmd = [sys.executable, "-m", "game.headless", "--seed", str(seed), "--night", str(night),
           "--ticks", str(ticks), "--out", str(out), *args]
    for flag, data in (("--scenario", scenario), ("--inputs", inputs)):
        if data is not None:
            p = tmp_path / f"{name}{flag[1:]}.json"
            p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
            cmd += [flag, str(p)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    lines = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()] if out.exists() else []
    return r, lines


def events(lines, name=None):
    return [l for l in lines if l["type"] == "event" and (name is None or l["name"] == name)]


def empty(**kw):
    sc = {"random_motes": False, "random_shades": False, "random_drifters": False, "wind_enabled": False,
          "motes": [], "shades": [], "drifters": []}
    sc.update(kw)
    return sc


def steps(sim, n, inp=None):
    inp = inp or InputState()
    evs = []
    for _ in range(n):
        evs += sim.step(inp)
    return evs


def press(sim, **kw):
    """One tick with buttons down, then one tick released (edge-triggered)."""
    ev = sim.step(InputState(**kw))
    ev += sim.step(InputState(move=kw.get("move", (0, 0))))
    return ev


# ---------------- contract / format ----------------
def test_contract_v12_standard_numbers():
    # [T03] was test_contract_v11_standard_numbers: version 1.2, new night durations, fuel keys, new score table
    c = json.loads((ROOT / "game.contract.json").read_text(encoding="utf-8"))
    assert c["contract_version"] in ("1.2", "1.3")  # [T04] v1.3 only adds bench_cmd/soak_cmd, every v1.2 number is unchanged
    t = c["tuning"]
    assert (t["player_speed"], t["carry_capacity"], t["lantern_cost"], t["pickup_radius"], t["interact_radius"]) == (6.0, 10, 10, 1.0, 2.0)
    assert (t["pulse_cost"], t["pulse_radius"], t["pulse_cooldown_s"], t["pulse_stun_s"], t["pulse_push_m"]) == (3, 5.0, 3.0, 2.0, 4.0)
    assert (t["dash_speed"], t["dash_duration_s"], t["dash_cooldown_s"]) == (14.0, 0.2, 1.5)
    assert (t["night1_duration_s"], t["night2_duration_s"], t["night3_duration_s"]) == (240, 270, 300)
    assert (t["fuel_max"], t["fuel_decay_per_s"], t["fuel_per_mote"], t["relight_cost"], t["win_ratio"]) == (100, 1.0, 10, 5, 0.6)
    assert (t["drain_per_s"], t["low_fuel_threshold"], t["capacity_max"]) == (5, 30, 20)
    assert (t["shade_speed"], t["invuln_s"], t["safe_radius"], t["fall_enabled"]) == (4.0, 1.5, 6.0, True)
    assert t["score"] == {"per_mote": 5, "per_lantern": 100, "per_stun": 5, "per_second_left": 0, "per_flame_left": 50}


@pytest.mark.parametrize("night", [1, 2, 3])
def test_snapshot_fields_and_night_start(tmp_path, night):
    r, lines = run_cli(tmp_path, ticks=20, night=night, name=f"n{night}")
    assert r.returncode == 0, r.stderr
    s0 = lines[0]
    assert s0["night"] == night and s0["wind"] == {"active": False, "dir_deg": None}
    for k in ("vel", "grounded", "invuln", "dash_cd_s", "pulse_cd_s", "charm_s"):
        assert k in s0["player"]
    assert lines[1] == {"type": "event", "tick": 0, "name": "night_start", "data": {"night": night}}
    m = s0["motes"][0]
    assert set(m) == {"id", "pos", "kind", "ttl_s"} and m["kind"] == "random"
    assert len(s0["motes"]) == 20 and len({tuple(m["pos"]) for m in s0["motes"]}) == 20
    assert "drifters" in s0 and "charms" in s0
    assert len(s0["lanterns"]) == {1: 5, 2: 6, 3: 7}[night]
    assert s0["time_left_s"] == {1: 240, 2: 270, 3: 300}[night]  # [T03] durations shortened
    l0 = s0["lanterns"][0]
    assert (l0["fuel"], l0["ever_lit"], l0["relit_count"]) == (0.0, False, 0) and s0["player"]["capacity"] == 10


@pytest.mark.parametrize("night", [1, 2, 3])
def test_determinism_and_speed_full_night(tmp_path, night):
    inp = {"frames": [{"tick": 0, "move": [0.7, 1]}, {"tick": 200, "dash": True}, {"tick": 201, "dash": False},
                      {"tick": 400, "move": [-1, 0], "jump": True}, {"tick": 401, "jump": False}]}
    t0 = time.perf_counter()
    _, a = run_cli(tmp_path, inputs=inp, ticks=21600, night=night, seed=4, name="a")
    assert time.perf_counter() - t0 < 30
    _, b = run_cli(tmp_path, inputs=inp, ticks=21600, night=night, seed=4, name="b")
    assert a == b


def test_bad_inputs_exit_2(tmp_path):
    for kw in ({"inputs": {"frames": [{"tick": 5}, {"tick": 5}]}}, {"inputs": "{not json"},
               {"inputs": {"frames": [{"tick": 0, "move": [2, 0]}]}}, {"inputs": {"frames": [{"tick": 0, "pause": 1}]}},
               {"scenario": {"lanterns": [{"id": "L9"}]}}, {"scenario": {"shades": [{"pos": [1, 0, 1], "state": "angry"}]}}):
        r, _ = run_cli(tmp_path, **kw)
        assert r.returncode == 2 and r.stderr
    r, _ = run_cli(tmp_path, "--night", "4")
    assert r.returncode != 0


# ---------------- movement ----------------
def test_run_speed_instant_and_yaw():
    sim = Sim(1, scenario=empty())
    steps(sim, 60, InputState(move=(0, 1)))
    assert sim.player.z == pytest.approx(6.0) and sim.player.vz == pytest.approx(6.0)
    sim = Sim(1, scenario=empty())
    steps(sim, 60, InputState(move=(1, 1), cam_yaw_deg=90))
    assert (sim.player.x ** 2 + sim.player.z ** 2) ** .5 == pytest.approx(6.0)


def test_jump_physics_only_grounded():
    sim = Sim(1, scenario=empty())
    sim.step(InputState(jump=True))
    assert not sim.player.grounded and sim.player.vy == pytest.approx(7 - 20 / 60)
    peak, n = 0, 1
    while not sim.player.grounded:
        sim.step(InputState(jump=True))  # held: no re-jump
        peak, n = max(peak, sim.player.y), n + 1
    assert peak == pytest.approx(7 ** 2 / 40, abs=.07) and 40 <= n <= 44


def test_dash_distance_cooldown_and_facing():
    sim = Sim(1, scenario=empty())
    ev = press(sim, dash=True)  # idle: dash along facing (+Z)
    assert [e["name"] for e in ev] == ["dash"]
    steps(sim, 12)
    assert sim.player.z == pytest.approx(14 * .2) and sim.player.x == 0
    assert press(sim, dash=True) == []  # cooldown 90 ticks from start
    steps(sim, 90 - 16)
    assert [e["name"] for e in press(sim, dash=True)] == ["dash"]


def test_air_dash_keeps_altitude():
    sim = Sim(1, scenario=empty())
    sim.step(InputState(jump=True))
    steps(sim, 8)
    y = sim.player.y
    sim.step(InputState(dash=True, move=(1, 0)))
    steps(sim, 10, InputState(move=(1, 0)))
    assert sim.player.y == pytest.approx(y)


# ---------------- motes ----------------
def test_pickup_radius_height_and_capacity():
    sim = Sim(1, scenario=empty(motes=[[0, 0, 1.0], [0, 0, -1.01], [1, 2.0, 0]]))
    ev = sim.step(InputState())
    assert len(ev) == 1 and sim.player.carried == 1  # 1.0 m yes, 1.01 m no, 2 m above ground no
    sim = Sim(1, scenario=empty(motes=[[0, 0, 0]] * 12))
    sim.step(InputState())
    assert sim.player.carried == 10 and len(sim.motes) == 2


def test_mote_spawn_schedule_and_cap():
    sim = Sim(9, scenario={"random_shades": False, "player": {"pos": [0, 0, 0]}})
    assert len(sim.motes) == 20
    steps(sim, 239)
    assert len(sim.motes) == 20
    steps(sim, 1)
    assert len(sim.motes) == 21
    steps(sim, 240 * 10)
    assert len(sim.motes) == 24  # night 1 has only 24 points; full points -> skip


# ---------------- lanterns & score ----------------
def test_deposit_partial_nearest_and_score():
    sim = Sim(1, scenario=empty(player={"pos": [0, 0, 23], "carried": 7}))
    ev = press(sim, interact=True)
    assert ev[0]["data"] == {"lantern_id": "L1", "amount": 7, "deposited": 7} and sim.score == 35  # [T03] +5/mote
    sim.player.carried = 5
    ev = press(sim, interact=True)
    assert [e["name"] for e in ev] == ["deposit", "lantern_lit"] and ev[0]["data"]["amount"] == 3
    assert ev[1]["data"] == {"lantern_id": "L1", "relight": False}
    assert sim.score == 50 + 100 and sim.player.carried == 2
    sim = Sim(1, scenario=empty(player={"pos": [0, 0, 22.9], "carried": 5}))
    assert press(sim, interact=True) == []  # 2.1 m > 2.0


def test_no_early_win_all_lit_keeps_playing():
    # [T03] replaces test_win_bonus_after_tick and test_dawn_and_win_on_last_tick (early win + time bonus removed): lighting every lantern no longer ends the night
    lans = [{"id": f"L{i}", "lit": True} for i in range(2, 6)]
    sim = Sim(1, scenario=empty(player={"pos": [0, 0, 24], "carried": 10}, lanterns=lans))
    ev = sim.step(InputState(interact=True))
    assert "game_over" not in [e["name"] for e in ev] and sim.state == "playing"


def test_dawn_win_threshold_and_score():
    # [T03] replaces test_dawn_and_win_on_last_tick: win = alive at dawn with lit >= ceil(0.6 * total)
    lans = [{"id": "L1", "lit": True, "fuel": 80}, {"id": "L2", "lit": True, "fuel": 50.5}, {"id": "L3", "lit": True}]
    sim = Sim(1, scenario=empty(player={"flames": 2}, lanterns=lans, time_left_s=1))
    ev = steps(sim, 60)
    assert ev[-1]["data"] == {"result": "won", "reason": "dawn_survived"} and ev[-1]["tick"] == 60
    # fuel after 60 ticks: 79, 49.5, 99 -> 3 x 50 + 79 + 49 + 99 + 2 flames x 50
    assert sim.score == 150 + 79 + 49 + 99 + 100
    sim = Sim(1, scenario=empty(lanterns=lans[:2], time_left_s=1))
    assert steps(sim, 60)[-1]["data"] == {"result": "lost", "reason": "dawn"}  # 2/5 < 3
    for night, need in ((2, 4), (3, 5)):
        assert Sim(1, night=night).need_lit == need


def test_no_flames_beats_dawn_on_last_tick():
    lans = [{"id": f"L{i}", "lit": True} for i in range(1, 6)]
    sim = Sim(1, scenario=empty(player={"flames": 1}, shades=[{"pos": [.5, 1, 0]}], lanterns=lans, time_left_s=1 / 60))
    ev = sim.step(InputState())
    assert ev[-1]["data"] == {"result": "lost", "reason": "no_flames"}


# ---------------- Ticket-03: fuel, refuel, relight, capacity, drain ----------------
def test_fuel_decay_and_lantern_out():
    sim = Sim(1, scenario=empty(lanterns=[{"id": "L1", "lit": True, "fuel": 2}]))
    steps(sim, 60)
    assert sim.lanterns[0].fuel_u == 60 and sim.snapshot()["lanterns"][0]["fuel"] == 1.0
    ev = steps(sim, 60)
    assert [e for e in ev if e["name"] == "lantern_out"][0] == {"type": "event", "tick": 120, "name": "lantern_out", "data": {"lantern_id": "L1"}}
    l = sim.lanterns[0]
    assert (l.lit, l.deposited, l.ever_lit) == (False, 0, True) and sim.snapshot()["lanterns"][0]["fuel"] == 0.0


def test_refuel_math_full_ignored():
    sim = Sim(1, scenario=empty(player={"pos": [0, 0, 24], "carried": 9}, lanterns=[{"id": "L1", "lit": True, "fuel": 55}]))
    ev = sim.step(InputState(interact=True))
    # fuel 55 - 1/60 then ceil((100 - 54.98) / 10) = 5 motes -> 100
    assert ev[0]["name"] == "refuel" and ev[0]["data"] == {"lantern_id": "L1", "amount": 5, "fuel": 100.0}
    assert sim.player.carried == 4 and sim.score == 25
    # decay runs in step 2 before interaction, so a lit lantern is only "full" with decay off:
    t0 = dict(T, fuel_decay_per_s=0.0)
    sim = Sim(1, scenario=empty(player={"pos": [0, 0, 24], "carried": 9}, lanterns=[{"id": "L1", "lit": True}]), tuning=t0)
    assert sim.step(InputState(interact=True)) == [] and sim.player.carried == 9  # full lantern is not a candidate
    sim = Sim(1, scenario=empty(player={"pos": [0, 0, 24], "carried": 2}, lanterns=[{"id": "L1", "lit": True, "fuel": 40}]))
    ev = sim.step(InputState(interact=True))
    assert ev[0]["data"]["amount"] == 2 and ev[0]["data"]["fuel"] == pytest.approx(60.0, abs=.05)


def test_relight_cost_5_score_40_and_capacity_growth():
    sim = Sim(1, scenario=empty(player={"pos": [0, 0, 24], "carried": 10}, lanterns=[{"id": "L1", "lit": False, "ever_lit": True}]))
    ev = sim.step(InputState(interact=True))
    assert [e["name"] for e in ev] == ["deposit", "lantern_lit"] and ev[0]["data"]["amount"] == 5
    assert ev[1]["data"] == {"lantern_id": "L1", "relight": True}
    assert sim.score == 25 + 40 and sim.lanterns[0].relit_count == 1 and sim.capacity == 12
    sim.successful_lights = 9
    assert sim.capacity == 20  # capped
    sim = Sim(1, scenario=empty(player={"successful_lights": 2}, motes=[[0, 0, 0]] * 16))
    sim.step(InputState())
    assert sim.player.carried == 14 and sim.snapshot()["player"]["capacity"] == 14


def test_low_fuel_loses_safe_zone_exactly_30_keeps_it():
    for fuel, inside in ((31.5, False), (29.0, True)):  # 31.5 stays >= 30 for the 60 ticks of the test
        sim = Sim(1, scenario=empty(player={"pos": [0, 0, 35]}, shades=[{"id": "S1", "pos": [0, 1, 17], "state": "chase"}],
                                    lanterns=[{"id": "L1", "lit": True, "fuel": fuel}]))
        steps(sim, 60, InputState())
        s = sim.shades[0]
        assert (((s.x) ** 2 + (s.z - 25) ** 2) ** .5 < 6) == inside


def test_wander_shade_drains_weak_lantern():
    sim = Sim(1, scenario=empty(player={"pos": [0, 0, -30]}, shades=[{"id": "S1", "pos": [0, 1, 20]}, {"id": "S2", "pos": [1, 1, 22]}],
                                lanterns=[{"id": "L1", "lit": True, "fuel": 25}]))
    ev = steps(sim, 120)
    assert all(s.state == "drain" and s.target == "L1" for s in sim.shades)
    fd = [e for e in ev if e["name"] == "fuel_drain"]
    assert fd and fd[0]["data"]["lantern_id"] == "L1" and set(fd[0]["data"]) == {"lantern_id", "shade_id", "fuel"}
    snap = sim.snapshot()
    assert {s["state"] for s in snap["shades"]} == {"drain"}
    f0 = sim.lanterns[0].fuel_u
    sim.step(InputState())
    assert f0 - sim.lanterns[0].fuel_u == 1 + 5 + 5  # decay + 2 drains, cumulative


def test_drain_transitions_chase_refuel_eviction_and_pulse_bonus():
    lan = [{"id": "L1", "lit": True, "fuel": 20}]
    sim = Sim(1, scenario=empty(player={"pos": [0, 0, 32]}, shades=[{"id": "S1", "pos": [0, 1, 24], "state": "drain", "target_lantern_id": "L1"}], lanterns=lan))
    sim.step(InputState())
    assert sim.shades[0].state == "drain"
    sim.player.z = 29.5  # within 6 m of the shade
    sim.step(InputState())
    assert sim.shades[0].state == "chase"
    sim = Sim(1, scenario=empty(player={"pos": [0, 0, 26.5], "carried": 9},
                                shades=[{"id": "S1", "pos": [0, 1, 23.5], "state": "drain", "target_lantern_id": "L1"}], lanterns=lan))
    sim.player.z = 26.9
    sim.shades[0].z = 23.2
    sim2 = Sim(1, scenario=empty(player={"pos": [1.9, 0, 25], "carried": 9},
                                 shades=[{"id": "S1", "pos": [-1.5, 1, 25], "state": "drain", "target_lantern_id": "L1"}], lanterns=lan))
    sim2.player.x = 1.9
    ev = sim2.step(InputState(interact=True))
    # Mây is 3.4 m away (< 6) so the shade turns to chase in step 8, but it is being evicted first (refuel >= 30)
    assert ev[0]["name"] == "refuel" and sim2.shades[0].evict > 0
    steps(sim2, 30)
    s = sim2.shades[0]
    assert ((s.x) ** 2 + (s.z - 25) ** 2) ** .5 >= 6 - 1e-6 and sim2.player.flames == 3
    sim3 = Sim(1, scenario=empty(player={"pos": [0, 0, 28], "carried": 3},
                                 shades=[{"id": "S1", "pos": [0, 1, 24], "state": "drain", "target_lantern_id": "L1"}], lanterns=lan))
    sim3.player.z = 28.0
    ev = sim3.step(InputState(pulse=True))
    assert [e for e in ev if e["name"] == "pulse"][0]["data"] == {"stunned_ids": ["S1"]} and sim3.score == 15


def test_scenario_lantern_fields_and_validation(tmp_path):
    sc = empty(lanterns=[{"id": "L1", "lit": True}, {"id": "L2", "lit": True, "fuel": 42.5}, {"id": "L3", "ever_lit": True}])
    _, lines = run_cli(tmp_path, scenario=sc, ticks=0)
    l1, l2, l3 = lines[0]["lanterns"][:3]
    assert (l1["fuel"], l1["ever_lit"]) == (100.0, True) and l2["fuel"] == 42.5 and (l3["lit"], l3["ever_lit"]) == (False, True)
    r, _ = run_cli(tmp_path, scenario=empty(lanterns=[{"id": "L1", "lit": True, "fuel": 150}]))
    assert r.returncode == 2


# ---------------- shades ----------------
def test_shade_spawn_schedule_ids_distance():
    sim = Sim(2, scenario={"random_motes": False})
    ev = steps(sim, 299)
    assert not [e for e in ev if e["name"] == "shade_spawned"]
    ev = sim.step(InputState())
    assert [e["data"]["id"] for e in ev if e["name"] == "shade_spawned"] == ["S1", "S2"] and ev[0]["tick"] == 300
    assert all(s.state == "spawning" and ((s.x ** 2 + s.z ** 2) ** .5) == pytest.approx(37) for s in sim.shades)
    ev = steps(sim, 480)
    assert [e["data"]["id"] for e in ev if e["name"] == "shade_spawned"] == ["S3"] and ev[-1]["tick"] == 780


def test_shade_chase_speed_detect_and_lose():
    sim = Sim(1, scenario=empty(shades=[{"id": "S1", "pos": [11, 1, 0]}]))
    steps(sim, 60)
    s = sim.shades[0]
    assert s.state == "chase" and s.x == pytest.approx(11 - 4.0)
    sim = Sim(1, scenario=empty(shades=[{"id": "S1", "pos": [13, 1, 0], "state": "chase"}]))
    sim.step(InputState())
    assert sim.shades[0].state == "chase"
    sim = Sim(1, scenario=empty(shades=[{"id": "S1", "pos": [18.5, 1, 0], "state": "chase"}]))
    sim.step(InputState())
    assert sim.shades[0].state == "wander"
    sim = Sim(1, night=3, scenario=empty(player={"pos": [0, 0, -30]}, shades=[{"pos": [10, 1, -30]}]))
    steps(sim, 60)
    assert sim.shades[0].x == pytest.approx(10 - 4.5)


def test_hit_drop_ring_invuln_recoil_one_per_tick():
    sim = Sim(1, scenario=empty(player={"carried": 7}, shades=[{"id": "S1", "pos": [.5, 1, 0]}, {"id": "S2", "pos": [-.5, 1, 0]}]))
    ev = sim.step(InputState())
    hits = [e for e in ev if e["name"] == "player_hit"]
    assert len(hits) == 1 and hits[0]["data"] == {"by": "shade", "flames": 2, "dropped": 3}
    drops = [m for m in sim.motes if m.kind == "dropped"]
    assert len(drops) == 3 and all(1.5 - 1e-9 <= (m.x ** 2 + m.z ** 2) ** .5 <= 2.5 + 1e-9 and m.ttl == 480 for m in drops)
    assert sim.shades[0].state == "recoil" and sim.player.invuln == 90
    x_hit = sim.shades[0].x  # S1 chased 1/15 m in step 8 before contact
    ev = steps(sim, 60)
    assert sim.shades[0].x == pytest.approx(x_hit + 2.0)  # recoil: 2 m over 60 ticks
    assert sim.shades[0].state == "wander"
    ev += steps(sim, 29)
    assert not [e for e in ev if e["name"] == "player_hit"]  # invulnerable 90 ticks


def test_dropped_mote_ttl_and_repick():
    sim = Sim(1, scenario=empty(motes=[{"pos": [5, 0, 5], "kind": "dropped", "ttl_s": 1.0}]))
    steps(sim, 59)
    assert len(sim.motes) == 1
    sim.step(InputState())
    assert sim.motes == []


def test_pulse_cost_radius3d_stun_push_cooldown_score():
    sim = Sim(1, scenario=empty(player={"carried": 5}, shades=[{"id": "S1", "pos": [3, 1, 0]},
                                                               {"id": "S2", "pos": [0, 6.5, 3]}, {"id": "S3", "pos": [10, 1, 0]}]))
    ev = sim.step(InputState(pulse=True))
    p = [e for e in ev if e["name"] == "pulse"][0]
    assert p["data"] == {"stunned_ids": ["S1"]}  # S2 is 5.8 m away in 3D
    assert sim.player.carried == 2 and sim.score == 5 and sim.player.pulse_cd == 180
    steps(sim, 14)
    s1 = sim.shades[0]
    assert s1.x == pytest.approx(7.0) and s1.state == "stunned"
    steps(sim, 105)
    assert s1.state == "stunned"  # stunned during ticks 1..120
    sim.step(InputState())
    assert s1.state != "stunned"
    sim2 = Sim(1, scenario=empty(player={"carried": 2}, shades=[{"pos": [2, 1, 0]}]))
    assert sim2.step(InputState(pulse=True)) == []


def test_pulse_refreshes_stun_and_scores_stunned():
    sim = Sim(1, scenario=empty(player={"carried": 9, "pulse_cd_ticks": 0},
                                shades=[{"id": "S1", "pos": [1, 1, 0], "state": "stunned", "state_ticks_left": 10}]))
    sim.step(InputState(pulse=True))
    assert sim.shades[0].timer == 120 and sim.score == 5


def test_safe_zone_block_and_eviction():
    sim = Sim(1, scenario=empty(player={"pos": [0, 0, 25]}, shades=[{"pos": [0, 1, 12]}], lanterns=[{"id": "L1", "lit": True}]))
    for _ in range(600):
        sim.step(InputState())
        s = sim.shades[0]
        assert ((s.x) ** 2 + (s.z - 25) ** 2) ** .5 >= 6 - 1e-6
    assert sim.player.flames == 3
    sim = Sim(1, scenario=empty(player={"pos": [0, 0, 24], "carried": 10}, shades=[{"id": "S1", "pos": [0, 1, 24.5]}],
                                lanterns=[{"id": "L1", "deposited": 0}], ))
    sim.player.invuln = 0
    ev = sim.step(InputState(interact=True))
    assert "lantern_lit" in [e["name"] for e in ev] and "player_hit" not in [e["name"] for e in ev]
    steps(sim, 30)
    s = sim.shades[0]
    assert (s.x ** 2 + (s.z - 25) ** 2) ** .5 >= 6 - 1e-6


# ---------------- falling ----------------
def test_fall_lose_motes_respawn_and_last_flame():
    sim = Sim(1, scenario=empty(player={"pos": [39.5, 0, 0], "carried": 4}))
    ev = steps(sim, 120, InputState(move=(1, 0)))
    f = [e for e in ev if e["name"] == "player_hit"]
    assert len(f) == 1 and f[0]["data"] == {"by": "fall", "flames": 2, "dropped": 0, "lost": 4}
    t_fall = f[0]["tick"]
    sim2 = Sim(1, scenario=empty(player={"pos": [39.5, 0, 0], "carried": 4}))
    for _ in range(t_fall + 60):
        sim2.step(InputState(move=(1, 0)) if sim2.tick < t_fall else InputState())
    assert (sim2.player.x, sim2.player.y, sim2.player.z) == (0.0, 0.0, 0.0) and sim2.player.invuln == 90
    sim3 = Sim(1, scenario=empty(player={"pos": [39.5, 0, 0], "flames": 1}))
    ev = steps(sim3, 200, InputState(move=(1, 0)))
    assert ev[-1]["data"] == {"result": "lost", "reason": "no_flames"}


# ---------------- night 2: bridge, pads, drifters, charm ----------------
def test_night2_bridge_and_pad_flight():
    sim = Sim(1, night=2, scenario=empty(player={"pos": [27, 0, 0]}, charms=[]))
    steps(sim, 60 * 3, InputState(move=(1, 0)))
    assert sim.player.grounded and sim.player.y == 0 and sim.player.x == pytest.approx(45)
    sim = Sim(1, night=2, scenario=empty(player={"pos": [20, 0, 18]}))
    sim.step(InputState())
    assert sim.player.launched
    n = 0
    while not sim.player.grounded and n < 200:
        sim.step(InputState(move=(-1, 0)))  # input does not override launch
        n += 1
    assert 80 <= n <= 90 and ((sim.player.x - 70) ** 2 + sim.player.z ** 2) ** .5 < 28


def test_drifter_steal_flee_and_pulse_drop():
    sim = Sim(1, night=2, scenario=empty(player={"carried": 6}, drifters=[{"id": "D1", "pos": [3, 1.2, 0]}]))
    ev = steps(sim, 30)
    st = [e for e in ev if e["name"] == "drifter_steal"]
    assert st and st[0]["data"] == {"drifter_id": "D1", "amount": 3, "carried": 3}
    d = sim.drifters[0]
    assert d.state == "flee" and d.stolen == 3
    sim.player.carried = 3
    d.x, d.z = 2.0, 0.0
    ev = sim.step(InputState(pulse=True))
    assert {"drifter_id": "D1", "amount": 3} in [e["data"] for e in ev if e["name"] == "drifter_drop"]
    assert sum(1 for m in sim.motes if m.kind == "dropped") == 3
    steps(sim, 120)
    assert d.state == "removed"


def test_drifter_idle_below_5_and_pulse_chase_to_flee():
    sim = Sim(1, night=2, scenario=empty(player={"carried": 4}, drifters=[{"id": "D1", "pos": [3, 1.2, 0]}]))
    steps(sim, 30)
    assert sim.drifters[0].state == "idle" and sim.player.carried == 4
    sim = Sim(1, night=2, scenario=empty(player={"carried": 6}, drifters=[{"id": "D1", "pos": [4, 1.2, 0], "state": "chase"}]))
    sim.step(InputState(pulse=True))
    assert sim.drifters[0].state == "flee" and sim.drifters[0].stolen == 0


def test_drifter_spawn_schedule_night2():
    sim = Sim(5, night=2, scenario={"random_shades": False, "random_motes": False, "player": {"flames": 3}})
    steps(sim, 1199)
    assert sim.drifters == []
    steps(sim, 1)
    assert [d.id for d in sim.drifters] == ["D1"]


def test_charm_speed_dash_no_cooldown_respawn():
    sim = Sim(1, night=2, scenario=empty(player={"pos": [35, 0, 0]}))
    ev = sim.step(InputState())
    assert ev[0]["name"] == "charm_picked" and ev[0]["data"] == {"charm_id": "C1", "charm_ticks": 600}
    x0 = sim.player.x
    steps(sim, 60, InputState(move=(1, 0)))
    assert sim.player.x - x0 == pytest.approx(7.2)
    assert [e["name"] for e in press(sim, dash=True)] == ["dash"]
    steps(sim, 12)
    assert [e["name"] for e in press(sim, dash=True)] == ["dash"]  # no cooldown with charm
    assert not sim.charms[0].available
    steps(sim, 2700)
    assert sim.charms[0].available


# ---------------- night 3: tiers, ramps, pad, tower, wind ----------------
def test_night3_cliff_ramp_pad_tower():
    sim = Sim(1, night=3, scenario=empty(player={"pos": [0, 0, 10]}))
    steps(sim, 60, InputState(move=(0, 1)))
    assert sim.player.z < 12 and sim.player.y == 0  # cliff to tier 1 blocks
    a = 30 * 3.14159265 / 180
    import math
    sim = Sim(1, night=3, scenario=empty(player={"pos": [31 * math.cos(a), 0, 31 * math.sin(a)]}))
    steps(sim, 60, InputState(move=(-math.cos(a), -math.sin(a)), cam_yaw_deg=0))
    assert sim.player.y == pytest.approx(2.5) and sim.player.grounded  # mid-ramp at r = 25
    steps(sim, 30, InputState(move=(-math.cos(a), -math.sin(a)), cam_yaw_deg=0))
    assert sim.player.y == pytest.approx(3.0) and sim.player.grounded  # on tier 1
    sim = Sim(1, night=3, scenario=empty(player={"pos": [0, 3, 13]}))
    for _ in range(120):
        sim.step(InputState())
        if sim.tick > 3 and sim.player.grounded:
            break
    assert sim.player.y == pytest.approx(6.0) and (sim.player.x ** 2 + sim.player.z ** 2) ** .5 <= 8
    sim = Sim(1, night=3, scenario=empty(player={"pos": [0, 6, 5]}))
    steps(sim, 120, InputState(move=(0, -1)))
    assert (sim.player.x ** 2 + sim.player.z ** 2) ** .5 >= 2.0 - 1e-9


def test_night3_wind_gust():
    sim = Sim(3, night=3, scenario=empty(player={"pos": [0, 0, -30]}, wind_enabled=True))
    steps(sim, 1799)
    assert sim.wind_left == 0 and (sim.player.x, sim.player.z) == (0, -30)
    sim.step(InputState())
    assert sim.wind_left == 300
    steps(sim, 60)
    assert ((sim.player.x) ** 2 + (sim.player.z + 30) ** 2) ** .5 == pytest.approx(2.0 * 61 / 60, abs=1e-6)
    steps(sim, 240)
    assert sim.wind_left == 0


# ---------------- pause ----------------
def test_pause_freezes_sim(tmp_path):
    inp = {"frames": [{"tick": 0, "move": [0, 1]}, {"tick": 10, "pause": True}, {"tick": 11, "pause": False},
                      {"tick": 40, "pause": True}, {"tick": 41, "pause": False}]}
    _, lines = run_cli(tmp_path, scenario=empty(), inputs=inp, ticks=60)
    assert [e["name"] for e in events(lines)] == ["night_start", "paused", "resumed"]
    s30 = [l for l in lines if l["type"] == "snapshot" and l["tick"] == 30][0]
    assert s30["state"] == "paused" and s30["sim_tick"] == 10 and s30["time_left_s"] == pytest.approx(240 - 10 / 60, abs=1e-3)  # [T03] 240 s
    assert s30["player"]["pos"][2] == pytest.approx(1.0)
    s60 = [l for l in lines if l["type"] == "snapshot" and l["tick"] == 60][0]
    assert s60["sim_tick"] == 30 and s60["state"] == "playing"


# ---------------- scenario files (proof) ----------------
def test_scenario_files_run(tmp_path):
    for scn in sorted(SCN.glob("*.json")):
        if scn.name.endswith(".inputs.json"):
            continue
        night = json.loads(scn.read_text(encoding="utf-8")).get("_night", 1)
        args = ["--scenario", str(scn)]
        inp = scn.with_name(scn.stem + ".inputs.json")
        if inp.exists():
            args += ["--inputs", str(inp)]
        r, lines = run_cli(tmp_path, *args, ticks=1200, night=night, name=scn.stem)
        assert r.returncode == 0, (scn.name, r.stderr)
        assert lines[-1]["type"] == "end"


# ---------------- settings persistence (view module, no ursina needed) ----------------
def test_settings_roundtrip(tmp_path):
    from game.view import audio
    p = tmp_path / "s.json"
    sub = lambda d: {k: d[k] for k in ("volume", "mouse_sensitivity", "colorblind")}  # [T04] settings also hold keys/accessibility
    assert sub(audio.load_settings(p)) == sub(audio.DEFAULTS)
    # [T03] settings gained "colorblind" (Ticket-03 §6, must be persisted)
    audio.save_settings({"volume": 0.3, "mouse_sensitivity": 2.0, "colorblind": 1.0}, p)
    assert sub(audio.load_settings(p)) == {"volume": 0.3, "mouse_sensitivity": 2.0, "colorblind": 1.0}
    audio.save_settings({"volume": 0.5, "mouse_sensitivity": 1.0}, p)  # old file without the key -> default off
    assert audio.load_settings(p)["colorblind"] == 0.0
    p.write_text("{broken", encoding="utf-8")
    assert sub(audio.load_settings(p)) == sub(audio.DEFAULTS)


def test_safe_zone_boundary_exactly_30():
    sim = Sim(1, scenario=empty(lanterns=[{"id": "L1", "lit": True, "fuel": 30}]))
    l = sim.lanterns[0]
    assert l.fuel_u == 1800 and sim._safe(l)
    l.fuel_u = 1799
    assert not sim._safe(l)
