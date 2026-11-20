"""Standard maps (Ticket-02, Part 2). Angles: from +X, counter-clockwise seen from above -> (r cos a, r sin a) on XZ."""
import math
from dataclasses import dataclass, field


def ring(r, degs, y=0.0, cx=0.0, cz=0.0):
    return [(round(cx + r * math.cos(math.radians(d)), 6), y, round(cz + r * math.sin(math.radians(d)), 6)) for d in degs]


@dataclass
class Pad:
    x: float
    y: float
    z: float
    vy: float
    hx: float
    hz: float


@dataclass
class NightMap:
    night: int
    name: str
    start: tuple
    lanterns: list
    mote_points: list
    shade_points: list
    shade_every: int
    shade_max: int
    shade_speed: float
    charms: list = field(default_factory=list)
    pads: list = field(default_factory=list)
    drifters: bool = False
    wind: bool = False

    def ground(self, x, z):
        """Ground height (Y) at XZ, or None over the cloud sea."""
        raise NotImplementedError

    def obstacle(self, x, z, y):
        return False


class Night1(NightMap):
    R = 40.0

    def ground(self, x, z):
        return 0.0 if math.hypot(x, z) <= self.R else None


class Night2(NightMap):
    R = 28.0
    B = (70.0, 0.0)

    def ground(self, x, z):
        if math.hypot(x, z) <= self.R or math.hypot(x - self.B[0], z - self.B[1]) <= self.R:
            return 0.0
        if 26.0 <= x <= 44.0 and -2.0 <= z <= 2.0:
            return 0.0
        return None


class Night3(NightMap):
    R = 45.0
    RAMPS = (30.0, 150.0)
    TOWER_R = 2.0
    TOWER_TOP = 14.0  # tier 2 (6) + 8 m

    def ground(self, x, z):
        r = math.hypot(x, z)
        if r > self.R:
            return None
        if r <= 8.0:
            return 6.0
        if 12.0 <= r <= 24.0 and z > 0:
            return 3.0
        for a in self.RAMPS:
            ux, uz = math.cos(math.radians(a)), math.sin(math.radians(a))
            s = x * ux + z * uz
            perp = abs(x * uz - z * ux)
            if perp <= 1.5 and 24.0 <= s <= 30.0:
                return 3.0 * (30.0 - s) / 6.0
        return 0.0

    def obstacle(self, x, z, y):
        return math.hypot(x, z) < self.TOWER_R and y < self.TOWER_TOP


def _pad_to(px, pz, tx, tz, vy, h, py=0.0):
    dx, dz = tx - px, tz - pz
    d = math.hypot(dx, dz)
    return Pad(px, py, pz, vy, h * dx / d, h * dz / d)


def make_map(night: int) -> NightMap:
    if night == 1:
        return Night1(
            1, "Đảo Bến", (0.0, 0.0, 0.0),
            [("L1", (0.0, 0.0, 25.0)), ("L2", (23.8, 0.0, 7.7)), ("L3", (14.7, 0.0, -20.2)),
             ("L4", (-14.7, 0.0, -20.2)), ("L5", (-23.8, 0.0, 7.7))],
            ring(12, range(0, 360, 45)) + ring(33, [i * 22.5 for i in range(16)]),
            ring(37, range(15, 360, 30), y=1.0),
            shade_every=480, shade_max=6, shade_speed=4.0)
    if night == 2:
        motes, shades = [], []
        for cx in (0.0, 70.0):
            motes += ring(10, (0, 90, 180, 270), cx=cx) + ring(22, range(0, 360, 45), cx=cx)
            shades += ring(26, [22.5 + 45 * i for i in range(8)], y=1.0, cx=cx)
        return Night2(
            2, "Đảo Cau", (0.0, 0.0, 0.0),
            [("L1", (0.0, 0.0, 20.0)), ("L2", (17.0, 0.0, -10.0)), ("L3", (-17.0, 0.0, -10.0)),
             ("L4", (70.0, 0.0, 20.0)), ("L5", (87.0, 0.0, -10.0)), ("L6", (53.0, 0.0, -10.0))],
            motes, shades, shade_every=420, shade_max=8, shade_speed=4.0,
            charms=[("C1", (35.0, 0.0, 0.0))],
            pads=[_pad_to(20, 18, 70, 0, 14.0, 24.0), _pad_to(50, -18, 0, 0, 14.0, 24.0)],
            drifters=True)
    if night == 3:
        return Night3(
            3, "Đảo Chuông", (0.0, 0.0, -30.0),
            [("L1", (0.0, 6.0, 6.0)), ("L2", (18.0, 3.0, 10.0)), ("L3", (-18.0, 3.0, 10.0)),
             ("L4", (35.0, 0.0, -10.0)), ("L5", (-35.0, 0.0, -10.0)), ("L6", (20.0, 0.0, -35.0)),
             ("L7", (-20.0, 0.0, -35.0))],
            ring(34, range(0, 360, 20)) + ring(18, range(20, 161, 20), y=3.0) + ring(5, (45, 135, 225, 315), y=6.0),
            ring(43, [i * 22.5 for i in range(16)], y=1.0),
            shade_every=360, shade_max=10, shade_speed=4.5,
            charms=[("C1", (30.0, 0.0, 25.0)), ("C2", (-30.0, 0.0, 25.0))],
            pads=[Pad(0.0, 3.0, 13.0, 12.0, 0.0, -8.0)],
            drifters=True, wind=True)
    raise ValueError(f"unknown night {night}")
