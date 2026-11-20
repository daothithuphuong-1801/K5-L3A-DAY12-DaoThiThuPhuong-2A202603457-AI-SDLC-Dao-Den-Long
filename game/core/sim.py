"""Deterministic simulation of Dao Den Long - Test Contract v1.2 (Ticket-03 on top of Ticket-02). Fixed 60 ticks/s.

Tick order (Ticket-02, mandatory):
  1 input (pause first)  2 counters (+ lantern fuel decay/drain, then lanterns at fuel <= 0 go out)  3 move Mây (+fall check)  4 pickup motes/charms
  5 lantern interact  6 safe-zone update  7 pulse  8 move shades + drifters
  9 contacts (drifters steal, then shades hit, by id)  10 spawns  11 win/lose
"""
import math
import random
from dataclasses import dataclass, field

from . import tuning as T
from .maps import make_map

EPS = 1e-9
SHADE_STATES = ("spawning", "wander", "chase", "recoil", "stunned", "drain")
DRIFTER_STATES = ("idle", "chase", "flee", "removed")


class ScenarioError(ValueError):
    """Bad scenario/inputs content -> headless exit code 2."""


@dataclass
class InputState:
    move: tuple = (0.0, 0.0)
    cam_yaw_deg: float = 0.0
    jump: bool = False
    interact: bool = False
    pulse: bool = False
    dash: bool = False
    pause: bool = False


@dataclass
class Player:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    fx: float = 0.0          # facing (unit, XZ); starts +Z
    fz: float = 1.0
    grounded: bool = True
    flames: int = 3
    carried: int = 0
    invuln: int = 0
    dash_cd: int = 0
    dash_ticks: int = 0
    dash_dx: float = 0.0
    dash_dz: float = 0.0
    pulse_cd: int = 0
    charm: int = 0
    launched: bool = False
    lvx: float = 0.0
    lvz: float = 0.0
    respawn_wait: int = 0


@dataclass
class Mote:
    id: str
    x: float
    y: float
    z: float
    kind: str = "random"
    ttl: int | None = None
    point: int | None = None
    pick_from: int = 0


@dataclass
class Shade:
    id: str
    x: float
    y: float
    z: float
    state: str = "wander"
    timer: int = 0            # ticks left in spawning/recoil/stunned
    hover: float = 1.0
    push_left: int = 0
    pdx: float = 1.0
    pdz: float = 0.0
    evict: int = 0
    tx: float | None = None
    tz: float | None = None
    target: str | None = None   # lantern id (wander-to-weak-lantern / drain)
    drain_ticks: int = 0

    @property
    def num(self):
        return int(self.id[1:]) if self.id[1:].isdigit() else 10 ** 9


@dataclass
class Drifter:
    id: str
    x: float
    y: float
    z: float
    state: str = "idle"
    stolen: int = 0
    timer: int = 0
    tx: float | None = None
    tz: float | None = None


@dataclass
class Charm:
    id: str
    x: float
    y: float
    z: float
    available: bool = True
    respawn: int = 0


@dataclass
class Lantern:
    id: str
    x: float
    y: float
    z: float
    deposited: int = 0
    lit: bool = False
    fuel_u: int = 0           # fuel in 1/60 units (100 fuel = 6000)
    ever_lit: bool = False
    relit_count: int = 0


def dxz(ax, az, bx, bz):
    return math.hypot(ax - bx, az - bz)


def _num(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ScenarioError(f"{what} must be a number")
    return float(v)


def _vec3(v, what):
    if not isinstance(v, list) or len(v) != 3:
        raise ScenarioError(f"{what} must be [x, y, z]")
    return [_num(c, what) for c in v]


def _int(v, what):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise ScenarioError(f"{what} must be a non-negative integer")
    return v


def _bool(v, what):
    if not isinstance(v, bool):
        raise ScenarioError(f"{what} must be boolean")
    return v


def _idnum(i):
    return int(i[1:]) if isinstance(i, str) and i[1:].isdigit() else 0


class Sim:
    def __init__(self, seed: int = 0, night: int = 1, scenario: dict | None = None, tuning: dict | None = None,
                 bench: bool = False):
        if night not in (1, 2, 3):
            raise ScenarioError("--night must be 1, 2 or 3")
        self.t = tuning or T.load_tuning()
        self.bench = bench  # Ticket-04 bench scene: no spawns, damage, pickup, fuel use or end of night
        self.map = make_map(night)
        self.night = night
        self.rng = random.Random(seed * 10 + night)
        self.tick = 0
        self.sim_tick = 0
        self.state = "playing"
        self.paused = False
        self.reason = None
        self.score = 0
        self.events: list[dict] = []
        self.prev = InputState()
        self.total_ticks = round(self.t[f"night{night}_duration_s"] * T.TICK_RATE)
        sx, sy, sz = self.map.start
        self.player = Player(x=sx, y=sy, z=sz, flames=int(self.t["flames"]))
        self.random_motes = True
        self.random_shades = True
        self.random_drifters = self.map.drifters
        self.wind_enabled = self.map.wind
        self.wind_left = 0
        self.wind_dir = None
        self.next_mote = self.next_shade = self.next_drifter = 1
        self.successful_lights = 0
        self.fuel_max_u = round(self.t["fuel_max"] * T.FUEL_UNIT)
        self.low_u = round(self.t["low_fuel_threshold"] * T.FUEL_UNIT)
        self.lanterns = [Lantern(i, *p) for i, p in self.map.lanterns]
        self.charms = [Charm(i, *p) for i, p in self.map.charms]
        self.motes: list[Mote] = []
        self.shades: list[Shade] = []
        self.drifters: list[Drifter] = []
        sc = scenario or {}
        if scenario is not None:
            self._apply_scenario(scenario)
        if self.random_motes and "motes" not in sc:
            for idx in self.rng.sample(range(len(self.map.mote_points)), min(T.MOTE_START, len(self.map.mote_points))):
                self._add_mote(idx)

    # ------------------------------------------------------------------ setup
    def _apply_scenario(self, sc):
        if not isinstance(sc, dict):
            raise ScenarioError("scenario must be an object")
        p = sc.get("player", {})
        if not isinstance(p, dict):
            raise ScenarioError("player must be an object")
        pl = self.player
        if "pos" in p:
            pl.x, pl.y, pl.z = _vec3(p["pos"], "player.pos")
            g = self.map.ground(pl.x, pl.z)
            pl.grounded = g is not None and abs(pl.y - g) < 1e-6
        for k, attr in (("carried", "carried"), ("flames", "flames"), ("invuln_ticks", "invuln"),
                        ("dash_cd_ticks", "dash_cd"), ("pulse_cd_ticks", "pulse_cd"), ("charm_ticks", "charm")):
            if k in p:
                setattr(pl, attr, _int(p[k], f"player.{k}"))
        if "successful_lights" in p:
            self.successful_lights = _int(p["successful_lights"], "player.successful_lights")
        for k in ("random_motes", "random_shades", "random_drifters", "wind_enabled"):
            if k in sc:
                setattr(self, k, _bool(sc[k], k))
        if "motes" in sc:
            if not isinstance(sc["motes"], list):
                raise ScenarioError("motes must be a list")
            for m in sc["motes"]:
                if isinstance(m, dict):
                    x, y, z = _vec3(m.get("pos"), "motes[].pos")
                    kind = m.get("kind", "random")
                    if kind not in ("random", "dropped"):
                        raise ScenarioError("motes[].kind must be random|dropped")
                    ttl = round(_num(m["ttl_s"], "ttl_s") * 60) if m.get("ttl_s") is not None else (T.DROP_TTL if kind == "dropped" else None)
                else:
                    x, y, z = _vec3(m, "motes[]")
                    kind, ttl = "random", None
                self.motes.append(Mote(f"M{self.next_mote}", x, y, z, kind, ttl))
                self.next_mote += 1
        if "shades" in sc:
            if not isinstance(sc["shades"], list):
                raise ScenarioError("shades must be a list")
            given = []
            for s in sc["shades"]:
                if not isinstance(s, dict) or "pos" not in s:
                    raise ScenarioError("shades[] must be objects with pos")
                x, y, z = _vec3(s["pos"], "shades[].pos")
                sid = s.get("id")
                if sid is not None and not isinstance(sid, str):
                    raise ScenarioError("shades[].id must be a string")
                st = s.get("state", "wander")
                if st not in SHADE_STATES:
                    raise ScenarioError(f"shades[].state must be one of {SHADE_STATES}")
                left = _int(s.get("state_ticks_left", 0), "state_ticks_left")
                tgt = s.get("target_lantern_id")
                if tgt is not None and tgt not in {i for i, _ in self.map.lanterns}:
                    raise ScenarioError(f"unknown target_lantern_id {tgt!r}")
                given.append((sid, x, y, z, st, left, tgt))
            used = {g[0] for g in given if g[0]}
            self.next_shade = max([self.next_shade] + [_idnum(u) + 1 for u in used])
            for sid, x, y, z, st, left, tgt in given:
                if sid is None:
                    while f"S{self.next_shade}" in used:
                        self.next_shade += 1
                    sid = f"S{self.next_shade}"
                    self.next_shade += 1
                g = self.map.ground(x, z)
                if st in ("spawning", "recoil", "stunned") and left == 0:
                    left = {"spawning": T.SHADE_SPAWNING_TICKS, "recoil": T.RECOIL_TICKS,
                            "stunned": round(self.t["pulse_stun_s"] * 60)}[st]
                self.shades.append(Shade(sid, x, y, z, st, left, hover=y - (g if g is not None else 0.0), target=tgt))
        if "drifters" in sc:
            if not isinstance(sc["drifters"], list):
                raise ScenarioError("drifters must be a list")
            for d in sc["drifters"]:
                if not isinstance(d, dict) or "pos" not in d:
                    raise ScenarioError("drifters[] must be objects with pos")
                x, y, z = _vec3(d["pos"], "drifters[].pos")
                st = d.get("state", "idle")
                if st not in DRIFTER_STATES:
                    raise ScenarioError(f"drifters[].state must be one of {DRIFTER_STATES}")
                did = d.get("id") or f"D{self.next_drifter}"
                self.next_drifter = max(self.next_drifter, _idnum(did) + 1)
                stolen = _int(d.get("stolen", 0), "drifters[].stolen")
                timer = T.DRIFTER_FLEE_TICKS if st == "flee" else 0
                self.drifters.append(Drifter(did, x, y, z, st, stolen, timer))
        if "charms" in sc:
            if not isinstance(sc["charms"], list):
                raise ScenarioError("charms must be a list")
            self.charms = []
            for c in sc["charms"]:
                if not isinstance(c, dict) or "id" not in c:
                    raise ScenarioError("charms[] must be objects with id")
                default = dict(self.map.charms).get(c["id"], (0.0, 0.0, 0.0))
                x, y, z = _vec3(c["pos"], "charms[].pos") if "pos" in c else default
                avail = _bool(c.get("available", True), "charms[].available")
                resp = c.get("respawn_ticks")
                if resp is None and c.get("respawn_s") is not None:
                    resp = round(_num(c["respawn_s"], "respawn_s") * 60)
                if resp is None:
                    resp = 0 if avail else T.CHARM_RESPAWN
                self.charms.append(Charm(c["id"], x, y, z, avail, _int(int(resp), "respawn")))
        if "lanterns" in sc:
            if not isinstance(sc["lanterns"], list):
                raise ScenarioError("lanterns must be a list")
            by_id = {l.id: l for l in self.lanterns}
            for l in sc["lanterns"]:
                if not isinstance(l, dict) or l.get("id") not in by_id:
                    raise ScenarioError(f"unknown lantern: {l!r}")
                lan = by_id[l["id"]]
                if "pos" in l:
                    lan.x, lan.y, lan.z = _vec3(l["pos"], "lanterns[].pos")
                if "deposited" in l:
                    lan.deposited = _int(l["deposited"], "lanterns[].deposited")
                if "lit" in l:
                    lan.lit = _bool(l["lit"], "lanterns[].lit")
                if "fuel" in l:
                    f = _num(l["fuel"], "lanterns[].fuel")
                    if not 0 <= f <= self.t["fuel_max"]:
                        raise ScenarioError("lanterns[].fuel must be in [0, fuel_max]")
                    lan.fuel_u = round(f * T.FUEL_UNIT)
                elif lan.lit:
                    lan.fuel_u = self.fuel_max_u
                if not lan.lit:
                    lan.fuel_u = 0
                lan.ever_lit = _bool(l["ever_lit"], "lanterns[].ever_lit") if "ever_lit" in l else (lan.ever_lit or lan.lit)
        if "time_left_s" in sc:
            self.total_ticks = round(_num(sc["time_left_s"], "time_left_s") * T.TICK_RATE)

    @classmethod
    def bench_scene(cls, seed=42, shades=200, motes=100):
        """Ticket-04 benchmark scene: Night 1, Mây idle at (0,0,0), `shades` wander shades and `motes` motes spread
        uniformly over the island (seeded), L1-L3 lit with fuel 100. Spawning, damage, pickup, fuel use and the end of
        the night are disabled; shades still follow the normal wander rules."""
        sim = cls(seed, night=1, scenario={"random_motes": False, "random_shades": False, "random_drifters": False,
                                           "wind_enabled": False, "motes": [], "shades": [], "drifters": [],
                                           "lanterns": [{"id": f"L{i}", "lit": True, "fuel": 100} for i in (1, 2, 3)]},
                  bench=True)
        rng = random.Random(seed)
        R = 39.0

        def point():
            r, a = R * math.sqrt(rng.random()), rng.uniform(0, 2 * math.pi)
            return r * math.cos(a), r * math.sin(a)

        for i in range(shades):
            x, z = point()
            sim.shades.append(Shade(f"S{i + 1}", x, 1.0, z, "wander", 0, hover=1.0))
        sim.next_shade = shades + 1
        for _ in range(motes):
            x, z = point()
            sim.motes.append(Mote(f"M{sim.next_mote}", x, 0.0, z))
            sim.next_mote += 1
        return sim

    def _add_mote(self, idx):
        x, y, z = self.map.mote_points[idx]
        self.motes.append(Mote(f"M{self.next_mote}", x, y, z, "random", None, idx))
        self.next_mote += 1

    # ------------------------------------------------------------------ helpers
    @property
    def time_left_s(self):
        return (self.total_ticks - self.sim_tick) / T.TICK_RATE

    @property
    def wind_warning(self):
        return self.wind_enabled and self.sim_tick > 0 and (T.WIND_EVERY - self.sim_tick % T.WIND_EVERY) <= T.WIND_WARN

    def _event(self, name, data):
        self.events.append({"type": "event", "tick": self.tick + 1, "name": name, "data": data})

    def _safe(self, l):
        """A lit lantern keeps its safe zone only while fuel >= low_fuel_threshold (exactly 30 still safe)."""
        return l.lit and l.fuel_u >= self.low_u

    def _in_safe(self, x, z):
        sr = self.t["safe_radius"]
        return [l for l in self.lanterns if self._safe(l) and dxz(x, z, l.x, l.z) < sr]

    @property
    def need_lit(self):
        return math.ceil(self.t["win_ratio"] * len(self.lanterns) - 1e-9)

    @property
    def capacity(self):
        return min(self.t["capacity_max"], self.t["carry_capacity"] + T.CAPACITY_PER_LIGHT * self.successful_lights)

    def _evict_from(self, lan):
        for s in self.shades:
            if dxz(s.x, s.z, lan.x, lan.z) < self.t["safe_radius"]:
                s.evict = T.EVICT_MAX_TICKS
                if s.state == "drain":
                    s.state, s.target, s.drain_ticks = "wander", None, 0

    def _ground(self, x, z):
        return self.map.ground(x, z)

    def _drop_motes(self, n, cx, cy, cz, nt):
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            r = self.rng.uniform(*T.DROP_R)
            x, z = cx + r * math.cos(a), cz + r * math.sin(a)
            g = self._ground(x, z)
            self.motes.append(Mote(f"M{self.next_mote}", x, g if g is not None else cy, z, "dropped", T.DROP_TTL,
                                   None, nt + 1))
            self.next_mote += 1

    # ------------------------------------------------------------------ step
    def step(self, inp: InputState) -> list[dict]:
        """Advance one tick. Returns events emitted in this tick."""
        if self.state != "playing":
            return []
        self.events = []
        pv = self.prev
        edge = {k: getattr(inp, k) and not getattr(pv, k) for k in ("jump", "interact", "pulse", "dash", "pause")}
        self.prev = InputState(tuple(inp.move), inp.cam_yaw_deg, inp.jump, inp.interact, inp.pulse, inp.dash, inp.pause)

        # 1 pause first
        if edge["pause"]:
            if self.paused:
                self.paused = False
                self._event("resumed", {})
            else:
                self.paused = True
                self._event("paused", {})
                self.tick += 1
                return self.events
        if self.paused:
            self.tick += 1
            return self.events

        nt = self.sim_tick + 1
        p, t = self.player, self.t

        # 2 counters
        for a in ("invuln", "dash_cd", "pulse_cd", "charm"):
            if getattr(p, a) > 0:
                setattr(p, a, getattr(p, a) - 1)
        for s in self.shades:
            if s.state in ("spawning", "stunned"):  # recoil counts down where it moves (60 moves = 2 m)
                s.timer -= 1
                if s.timer <= 0:
                    s.state, s.timer, s.push_left = "wander", 0, 0
        keep = []
        for m in self.motes:
            if m.ttl is not None:
                m.ttl -= 1
                if m.ttl <= 0:
                    continue
            keep.append(m)
        self.motes = keep
        for c in self.charms:
            if not c.available:
                c.respawn -= 1
                if c.respawn <= 0:
                    c.available, c.respawn = True, 0
        for d in self.drifters:
            if d.state == "flee":
                d.timer -= 1
                if d.timer <= 0:
                    d.state = "removed"
        if self.wind_left > 0:
            self.wind_left -= 1
            if self.wind_left == 0:
                self.wind_dir = None
        if self.wind_enabled and nt % T.WIND_EVERY == 0:
            self.wind_left = T.WIND_TICKS
            self.wind_dir = self.rng.uniform(0, 360)
        # 2b lantern fuel: decay 1/s + drain 5/s per draining shade (integer 1/60 units)
        by_id = {l.id: l for l in self.lanterns}
        decay_u = round(t["fuel_decay_per_s"] * T.FUEL_UNIT / T.TICK_RATE)
        drain_u = round(t["drain_per_s"] * T.FUEL_UNIT / T.TICK_RATE)
        if self.bench:
            decay_u = drain_u = 0
        for l in self.lanterns:
            if l.lit:
                l.fuel_u -= decay_u
        for s in sorted((s for s in self.shades if s.state == "drain"), key=lambda s: (s.num, s.id)):
            if s.target in by_id and by_id[s.target].lit:
                lan = by_id[s.target]
                lan.fuel_u -= drain_u
                s.drain_ticks += 1
                if s.drain_ticks % T.DRAIN_EVENT_EVERY == 0:
                    self._event("fuel_drain", {"lantern_id": lan.id, "shade_id": s.id, "fuel": r1(max(0, lan.fuel_u) / T.FUEL_UNIT)})
        # 2c lanterns at fuel <= 0 go out (remember ever_lit)
        for l in self.lanterns:
            if l.lit and l.fuel_u <= 0:
                l.lit, l.fuel_u, l.deposited = False, 0, 0
                self._event("lantern_out", {"lantern_id": l.id})
                for s in self.shades:
                    if s.state == "drain" and s.target == l.id:
                        s.state, s.target, s.drain_ticks = "wander", None, 0

        # 3 move Mây + fall check
        self._move_player(inp, edge)

        # 4 pickup motes and charms
        if p.respawn_wait == 0 and not self.bench:
            keep = []
            for m in self.motes:
                if (nt >= m.pick_from and p.carried < self.capacity
                        and dxz(p.x, p.z, m.x, m.z) <= t["pickup_radius"] + EPS and abs(p.y - m.y) <= T.PICKUP_DY + EPS):
                    p.carried += 1
                    self._event("mote_picked", {"carried": p.carried})
                else:
                    keep.append(m)
            self.motes = keep
            for c in self.charms:
                if c.available and dxz(p.x, p.z, c.x, c.z) <= t["pickup_radius"] + EPS and abs(p.y - c.y) <= T.PICKUP_DY + EPS:
                    c.available, c.respawn = False, T.CHARM_RESPAWN
                    p.charm = T.CHARM_TICKS
                    self._event("charm_picked", {"charm_id": c.id, "charm_ticks": p.charm})

        # 5 lantern interaction: light / relight unlit lanterns, refuel lit ones that are not full
        newly_safe = []
        if edge["interact"] and p.respawn_wait == 0 and p.carried > 0:
            cands = [l for l in self.lanterns if (not l.lit or l.fuel_u < self.fuel_max_u)
                     and dxz(p.x, p.z, l.x, l.z) <= t["interact_radius"] + EPS and abs(p.y - l.y) <= T.INTERACT_DY + EPS]
            if cands:
                lan = min(cands, key=lambda l: (dxz(p.x, p.z, l.x, l.z), _idnum(l.id), l.id))
                if lan.lit:
                    per = round(t["fuel_per_mote"] * T.FUEL_UNIT)
                    used = min(p.carried, -(-(self.fuel_max_u - lan.fuel_u) // per))
                    was_low = lan.fuel_u < self.low_u
                    lan.fuel_u = min(self.fuel_max_u, lan.fuel_u + per * used)
                    p.carried -= used
                    self.score += used * t["score"]["per_mote"]
                    self._event("refuel", {"lantern_id": lan.id, "amount": used, "fuel": r1(lan.fuel_u / T.FUEL_UNIT)})
                    if was_low and lan.fuel_u >= self.low_u:
                        newly_safe.append(lan)
                else:
                    relight = lan.ever_lit
                    cost = t["relight_cost"] if relight else t["lantern_cost"]
                    amount = min(p.carried, max(0, cost - lan.deposited))
                    if amount > 0:
                        p.carried -= amount
                        lan.deposited += amount
                        self.score += amount * t["score"]["per_mote"]
                        self._event("deposit", {"lantern_id": lan.id, "amount": amount, "deposited": lan.deposited})
                    if lan.deposited >= cost:
                        lan.lit, lan.ever_lit, lan.fuel_u = True, True, self.fuel_max_u
                        if relight:
                            lan.relit_count += 1
                        self.successful_lights += 1
                        self.score += T.SCORE_RELIGHT if relight else t["score"]["per_lantern"]
                        newly_safe.append(lan)
                        self._event("lantern_lit", {"lantern_id": lan.id, "relight": relight})

        # 6 safe zones: shades inside a lantern that just became safe are evicted (<=30 ticks, harmless)
        for lan in newly_safe:
            self._evict_from(lan)

        # 7 pulse
        if edge["pulse"] and p.pulse_cd == 0 and p.carried >= t["pulse_cost"] and p.respawn_wait == 0:
            p.carried -= t["pulse_cost"]
            p.pulse_cd = round(t["pulse_cooldown_s"] * 60)
            cx, cy, cz = p.x, p.y + T.PULSE_CENTER_DY, p.z
            hit = []
            for s in sorted(self.shades, key=lambda s: (s.num, s.id)):
                if math.dist((cx, cy, cz), (s.x, s.y, s.z)) <= t["pulse_radius"] + EPS:
                    was_drain = s.state == "drain"
                    s.target, s.drain_ticks = None, 0
                    s.state, s.timer = "stunned", round(t["pulse_stun_s"] * 60)
                    s.push_left = T.PUSH_TICKS
                    ddx, ddz = s.x - p.x, s.z - p.z
                    dl = math.hypot(ddx, ddz)
                    s.pdx, s.pdz = (ddx / dl, ddz / dl) if dl > EPS else (1.0, 0.0)
                    hit.append(s.id)
                    self.score += T.SCORE_DRAIN_STUN if was_drain else t["score"]["per_stun"]
            for d in self.drifters:
                if d.state in ("idle", "removed") or math.dist((cx, cy, cz), (d.x, d.y, d.z)) > t["pulse_radius"] + EPS:
                    continue
                if d.state == "chase":
                    d.state, d.timer = "flee", T.DRIFTER_FLEE_TICKS
                elif d.state == "flee" and d.stolen > 0:
                    amount, d.stolen = d.stolen, 0
                    self._drop_motes_at(amount, d.x, d.z, nt)
                    d.timer = T.DRIFTER_DROP_TICKS
                    self._event("drifter_drop", {"drifter_id": d.id, "amount": amount})
            self._event("pulse", {"stunned_ids": hit})

        # 8 move shades and drifters
        self._move_shades()
        self._move_drifters()

        # 9 contacts: drifters steal first, then shades hit (id order)
        if p.respawn_wait == 0 and not self.bench:
            for d in sorted(self.drifters, key=lambda d: (_idnum(d.id), d.id)):
                if d.state == "chase" and p.carried > 0 and dxz(d.x, d.z, p.x, p.z) <= T.DRIFTER_TOUCH + EPS:
                    amount = min(T.DRIFTER_STEAL, p.carried)
                    p.carried -= amount
                    d.stolen, d.state, d.timer = amount, "flee", T.DRIFTER_FLEE_TICKS
                    self._event("drifter_steal", {"drifter_id": d.id, "amount": amount, "carried": p.carried})
            if p.invuln == 0:
                for s in sorted(self.shades, key=lambda s: (s.num, s.id)):
                    if (s.state in ("wander", "chase") and s.evict == 0
                            and dxz(s.x, s.z, p.x, p.z) <= t["shade_hit_radius"] + EPS and abs(p.y - s.y) <= T.SHADE_HIT_DY + EPS):
                        p.flames = max(0, p.flames - 1)
                        dropped = p.carried // 2
                        p.carried -= dropped
                        self._drop_motes(dropped, p.x, p.y, p.z, nt)
                        p.invuln = round(t["invuln_s"] * 60)  # 90 ticks
                        s.state, s.timer = "recoil", T.RECOIL_TICKS
                        ddx, ddz = s.x - p.x, s.z - p.z
                        dl = math.hypot(ddx, ddz)
                        s.pdx, s.pdz = (ddx / dl, ddz / dl) if dl > EPS else (1.0, 0.0)
                        self._event("player_hit", {"by": "shade", "flames": p.flames, "dropped": dropped})
                        break

        # 10 spawns (new entities interact from next tick)
        if not self.bench:
            self._spawn(nt)

        # 11 win / lose (after every update of the tick): no flames always loses first;
        # at dawn Mây wins if lit lanterns >= ceil(win_ratio * total). No early win any more.
        if self.bench:
            pass
        elif p.flames <= 0:
            self._end("lost", "no_flames", nt)
        elif nt >= self.total_ticks:
            if sum(l.lit for l in self.lanterns) >= self.need_lit:
                self._end("won", "dawn_survived", nt)
            else:
                self._end("lost", "dawn", nt)

        self.sim_tick = nt
        self.tick += 1
        return self.events

    def _drop_motes_at(self, n, x, z, nt):
        g = self._ground(x, z)
        for _ in range(n):
            self.motes.append(Mote(f"M{self.next_mote}", x, g if g is not None else 0.0, z, "dropped", T.DROP_TTL, None, nt + 1))
            self.next_mote += 1

    def _end(self, result, reason, nt):
        self.state, self.reason = result, reason
        if result == "won":
            sc = self.t["score"]
            for l in self.lanterns:
                if l.lit:
                    self.score += T.SCORE_DAWN_LANTERN + l.fuel_u // T.FUEL_UNIT
            self.score += self.player.flames * sc["per_flame_left"]
        self._event("game_over", {"result": result, "reason": reason})

    # ------------------------------------------------------------------ movement
    def _blocked(self, x, z, y):
        g = self._ground(x, z)
        if g is not None and g > y + T.STEP_HEIGHT:
            return True
        return self.map.obstacle(x, z, y)

    def _move_player(self, inp, edge):
        p, t, dt = self.player, self.t, T.DT
        if p.respawn_wait > 0:
            p.respawn_wait -= 1
            if p.respawn_wait == 0:
                p.x, p.y, p.z = self.map.start
                p.vx = p.vy = p.vz = 0.0
                p.grounded, p.launched, p.dash_ticks = True, False, 0
                p.invuln = round(t["invuln_s"] * 60)
            return
        mx, mz = float(inp.move[0]), float(inp.move[1])
        ln = math.hypot(mx, mz)
        if ln > 1.0:
            mx, mz = mx / ln, mz / ln
        th = math.radians(inp.cam_yaw_deg)
        wx = mx * math.cos(th) + mz * math.sin(th)
        wz = -mx * math.sin(th) + mz * math.cos(th)
        moving = math.hypot(wx, wz) > EPS
        if moving:
            wl = math.hypot(wx, wz)
            p.fx, p.fz = wx / wl, wz / wl
        speed = T.CHARM_SPEED if p.charm > 0 else t["player_speed"]
        if edge["dash"] and p.dash_ticks == 0 and (p.dash_cd == 0 or p.charm > 0):
            p.dash_dx, p.dash_dz = p.fx, p.fz   # facing == current move dir when moving
            p.dash_ticks = round(t["dash_duration_s"] * 60)
            p.dash_cd = 0 if p.charm > 0 else round(t["dash_cooldown_s"] * 60)
            self._event("dash", {})
        dashing = p.dash_ticks > 0
        if dashing:
            hx, hz = p.dash_dx * t["dash_speed"], p.dash_dz * t["dash_speed"]
            p.dash_ticks -= 1
        elif p.launched:
            hx, hz = p.lvx, p.lvz
        else:
            hx, hz = wx * speed, wz * speed
        if self.wind_left > 0 and self.wind_dir is not None:
            hx += T.WIND_SPEED * math.cos(math.radians(self.wind_dir))
            hz += T.WIND_SPEED * math.sin(math.radians(self.wind_dir))
        if edge["jump"] and p.grounded and not dashing:
            p.vy, p.grounded = T.JUMP_SPEED, False
        # horizontal with walls (cliffs, tower); slide along axes
        nx, nz = p.x + hx * dt, p.z + hz * dt
        if self._blocked(nx, nz, p.y):
            if not self._blocked(nx, p.z, p.y):
                nz = p.z
            elif not self._blocked(p.x, nz, p.y):
                nx = p.x
            else:
                nx, nz = p.x, p.z
        p.vx, p.vz = (nx - p.x) / dt, (nz - p.z) / dt
        p.x, p.z = nx, nz
        # vertical
        g = self._ground(p.x, p.z)
        if dashing:
            p.vy = 0.0
            p.grounded = g is not None and abs(p.y - g) <= T.STEP_HEIGHT
            if p.grounded:
                p.y = g
        elif p.grounded and g is not None and p.vy <= 0 and abs(p.y - g) <= T.STEP_HEIGHT:
            p.y, p.vy = g, 0.0
        else:
            p.vy -= T.GRAVITY * dt
            p.y += p.vy * dt
            if g is not None and p.y <= g and p.vy <= 0:
                p.y, p.vy, p.grounded, p.launched = g, 0.0, True, False
            else:
                p.grounded = False
        # launch pads
        if p.grounded and not p.launched:
            for pad in self.map.pads:
                if dxz(p.x, p.z, pad.x, pad.z) <= 1.0 + EPS and abs(p.y - pad.y) <= .5:
                    p.vy, p.lvx, p.lvz = pad.vy, pad.hx, pad.hz
                    p.launched, p.grounded = True, False
                    break
        # fall off the island
        if p.y < T.FALL_Y and p.respawn_wait == 0:
            p.flames = max(0, p.flames - 1)
            lost, p.carried = p.carried, 0
            p.respawn_wait = T.RESPAWN_WAIT
            p.vx = p.vy = p.vz = 0.0
            p.dash_ticks, p.launched = 0, False
            self._event("player_hit", {"by": "fall", "flames": p.flames, "dropped": 0, "lost": lost})

    def _shade_try(self, s, nx, nz):
        """Move a shade if the target is over ground, not in the tower, not inside a lit safe zone."""
        g = self._ground(nx, nz)
        if g is None or self.map.obstacle(nx, nz, g + s.hover):
            return False
        sr = self.t["safe_radius"]
        for l in self.lanterns:
            if self._safe(l):
                d = dxz(nx, nz, l.x, l.z)
                if d < sr:  # blocked at the 6 m edge
                    ux, uz = ((nx - l.x) / d, (nz - l.z) / d) if d > EPS else (1.0, 0.0)
                    nx, nz = l.x + ux * sr, l.z + uz * sr
                    g = self._ground(nx, nz)
                    if g is None or self._in_safe(nx, nz):
                        return False
        s.x, s.z, s.y = nx, nz, g + s.hover
        return True

    def _move_shades(self):
        p, dt = self.player, T.DT
        speed = self.map.shade_speed if self.night == 3 else self.t["shade_speed"]
        player_ok = p.respawn_wait == 0
        by_id = {l.id: l for l in self.lanterns}           # computed once per tick (bench: 200 shades)
        weak = [l for l in self.lanterns if l.lit and l.fuel_u < self.low_u]
        unlit = [l for l in self.lanterns if not l.lit]
        for s in self.shades:
            if s.state == "spawning":
                continue
            if s.evict > 0:
                s.evict -= 1
                zones = self._in_safe(s.x, s.z)
                if not zones:
                    s.evict = 0
                else:
                    l = zones[0]
                    d = dxz(s.x, s.z, l.x, l.z)
                    ux, uz = ((s.x - l.x) / d, (s.z - l.z) / d) if d > EPS else (1.0, 0.0)
                    step = max(self.t["safe_radius"] / T.EVICT_MAX_TICKS, 0.0)
                    nd = min(self.t["safe_radius"], d + step)
                    if s.evict == 0:
                        nd = self.t["safe_radius"]
                    s.x, s.z = l.x + ux * nd, l.z + uz * nd
                    g = self._ground(s.x, s.z)
                    if g is not None:
                        s.y = g + s.hover
                    if nd >= self.t["safe_radius"]:
                        s.evict = 0
                continue
            if s.state == "stunned":
                if s.push_left > 0:
                    s.push_left -= 1
                    step = self.t["pulse_push_m"] / T.PUSH_TICKS
                    if not self._shade_try(s, s.x + s.pdx * step, s.z + s.pdz * step):
                        s.push_left = 0
                continue
            if s.state == "recoil":
                step = T.RECOIL_DIST / T.RECOIL_TICKS
                self._shade_try(s, s.x + s.pdx * step, s.z + s.pdz * step)
                s.timer -= 1
                if s.timer <= 0:
                    s.state, s.timer = "wander", 0
                continue
            d = dxz(s.x, s.z, p.x, p.z)
            if s.state == "drain":
                lan = by_id.get(s.target)
                if player_ok and d <= T.DRAIN_BREAK_DIST + EPS:
                    s.state, s.target, s.drain_ticks = "chase", None, 0
                elif (lan is None or not lan.lit or lan.fuel_u >= self.low_u
                      or dxz(s.x, s.z, lan.x, lan.z) > T.LOW_FUEL_DIST + EPS):
                    s.state, s.target, s.drain_ticks = "wander", None, 0
                else:
                    continue  # stays still and drains (fuel is handled in step 2)
            if s.state == "chase" and (d > T.SHADE_LOSE or not player_ok):
                s.state = "wander"
            elif s.state == "wander" and player_ok and d <= T.SHADE_DETECT + EPS:
                s.state = "chase"
            if s.state == "chase":
                s.target = None
                tx, tz, v = p.x, p.z, speed
            else:
                if weak:  # wander shades are drawn to the nearest weak lantern
                    lan = min(weak, key=lambda l: (dxz(s.x, s.z, l.x, l.z), _idnum(l.id), l.id))
                    s.target = lan.id
                    if dxz(s.x, s.z, lan.x, lan.z) <= T.LOW_FUEL_DIST + EPS:
                        s.state, s.drain_ticks = "drain", 0
                        continue
                    tx, tz, v = lan.x, lan.z, speed
                else:
                    s.target = None
                    near = min(unlit, key=lambda l: (dxz(s.x, s.z, l.x, l.z), _idnum(l.id), l.id)) if unlit else None
                    if near is not None and dxz(s.x, s.z, near.x, near.z) > 4.0:
                        tx, tz = near.x, near.z   # drift back towards the nearest dark lantern
                    else:
                        if s.tx is None or dxz(s.x, s.z, s.tx, s.tz) < .5:
                            s.tx, s.tz = self._random_ground_point(s.x, s.z, 8.0)
                        tx, tz = s.tx, s.tz
                    v = T.SHADE_WANDER_SPEED
            dd = dxz(s.x, s.z, tx, tz)
            stepl = v * dt
            if dd <= stepl:
                nx, nz = tx, tz
            else:
                nx, nz = s.x + (tx - s.x) / dd * stepl, s.z + (tz - s.z) / dd * stepl
            if not self._shade_try(s, nx, nz) and s.state == "wander":
                s.tx = None

    def _random_ground_point(self, x, z, r):
        for _ in range(8):
            a = self.rng.uniform(0, 2 * math.pi)
            rr = self.rng.uniform(1.0, r)
            nx, nz = x + rr * math.cos(a), z + rr * math.sin(a)
            if self._ground(nx, nz) is not None:
                return nx, nz
        return x, z

    def _move_drifters(self):
        p, dt = self.player, T.DT
        for d in self.drifters:
            if d.state == "removed":
                continue
            dist = dxz(d.x, d.z, p.x, p.z)
            want = p.respawn_wait == 0 and p.carried >= T.DRIFTER_CHASE_CARRY and dist <= T.DRIFTER_CHASE_DIST + EPS
            if d.state == "idle" and want:
                d.state = "chase"
            elif d.state == "chase" and not want:
                d.state = "idle"
            if d.state == "chase":
                ux, uz = ((p.x - d.x) / dist, (p.z - d.z) / dist) if dist > EPS else (0.0, 0.0)
                stepl = min(T.DRIFTER_SPEED * dt, dist)
            elif d.state == "flee":
                ux, uz = ((d.x - p.x) / dist, (d.z - p.z) / dist) if dist > EPS else (1.0, 0.0)
                stepl = T.DRIFTER_SPEED * dt
            else:
                if d.tx is None or dxz(d.x, d.z, d.tx, d.tz) < .5:
                    d.tx, d.tz = self._random_ground_point(d.x, d.z, 10.0)
                dd = dxz(d.x, d.z, d.tx, d.tz)
                ux, uz = ((d.tx - d.x) / dd, (d.tz - d.z) / dd) if dd > EPS else (0.0, 0.0)
                stepl = min(T.DRIFTER_IDLE_SPEED * dt, dd)
            d.x += ux * stepl
            d.z += uz * stepl
            g = self._ground(d.x, d.z)
            if g is not None:
                d.y = g + 1.2

    def _spawn(self, nt):
        p = self.player
        if self.random_motes and nt % T.MOTE_SPAWN_EVERY == 0:
            if sum(1 for m in self.motes if m.kind == "random") < T.MOTE_CAP:
                used = {m.point for m in self.motes if m.kind == "random" and m.point is not None}
                for m in self.motes:  # scenario motes occupy the point they sit on
                    if m.kind == "random" and m.point is None:
                        for i, (x, _, z) in enumerate(self.map.mote_points):
                            if dxz(m.x, m.z, x, z) < 1e-6:
                                used.add(i)
                free = [i for i in range(len(self.map.mote_points)) if i not in used]
                if free:
                    self._add_mote(self.rng.choice(free))
        if self.random_shades and nt >= T.SHADE_FIRST and (nt - T.SHADE_FIRST) % self.map.shade_every == 0:
            for _ in range(2 if nt == T.SHADE_FIRST else 1):
                if len(self.shades) >= self.map.shade_max:
                    break
                pts = [q for q in self.map.shade_points if dxz(q[0], q[2], p.x, p.z) >= T.SHADE_SPAWN_MIN_DIST
                       and not any(dxz(q[0], q[2], s.x, s.z) < 1.0 for s in self.shades)]
                if not pts:
                    break
                x, y, z = self.rng.choice(pts)
                s = Shade(f"S{self.next_shade}", x, y, z, "spawning", T.SHADE_SPAWNING_TICKS, hover=1.0)
                self.next_shade += 1
                self.shades.append(s)
                self._event("shade_spawned", {"id": s.id})
        if self.random_drifters and self.night in (2, 3) and nt % T.DRIFTER_EVERY == 0:
            if sum(1 for d in self.drifters if d.state != "removed") < T.DRIFTER_MAX:
                x, _, z = self.rng.choice(self.map.shade_points)
                g = self._ground(x, z) or 0.0
                self.drifters.append(Drifter(f"D{self.next_drifter}", x, g + 1.2, z))
                self.next_drifter += 1

    # ------------------------------------------------------------------ output
    def snapshot(self) -> dict:
        p = self.player
        return {
            "type": "snapshot", "tick": self.tick, "sim_tick": self.sim_tick, "night": self.night,
            "state": "paused" if self.paused and self.state == "playing" else self.state,
            "time_left_s": r3(max(0.0, self.time_left_s)), "score": self.score,
            "wind": {"active": self.wind_left > 0, "dir_deg": r3(self.wind_dir) if self.wind_left > 0 else None},
            "player": {"pos": v3(p.x, p.y, p.z), "vel": v3(p.vx, p.vy, p.vz), "grounded": p.grounded, "capacity": self.capacity,
                       "invuln": p.invuln > 0, "dash_cd_s": r3(p.dash_cd / 60), "pulse_cd_s": r3(p.pulse_cd / 60),
                       "charm_s": r3(p.charm / 60), "flames": p.flames, "carried": p.carried},
            "lanterns": [{"id": l.id, "pos": v3(l.x, l.y, l.z), "lit": l.lit, "deposited": l.deposited,
                          "fuel": r1(l.fuel_u / T.FUEL_UNIT) if l.lit else 0.0, "ever_lit": l.ever_lit, "relit_count": l.relit_count}
                         for l in self.lanterns],
            "shades": [{"id": s.id, "pos": v3(s.x, s.y, s.z), "state": s.state} for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [{"id": m.id, "pos": v3(m.x, m.y, m.z), "kind": m.kind,
                       "ttl_s": r3(m.ttl / 60) if m.ttl is not None else None} for m in self.motes],
            "drifters": [{"id": d.id, "pos": v3(d.x, d.y, d.z), "state": d.state, "stolen": d.stolen} for d in self.drifters],
            "charms": [{"id": c.id, "pos": v3(c.x, c.y, c.z), "available": c.available, "respawn_s": r3(c.respawn / 60)}
                       for c in self.charms],
        }


def r3(x):
    v = round(x, 3)
    return 0.0 if v == 0 else v


def v3(x, y, z):
    return [r3(x), r3(y), r3(z)]


def r1(x):
    v = round(x, 1)
    return 0.0 if v == 0 else v
