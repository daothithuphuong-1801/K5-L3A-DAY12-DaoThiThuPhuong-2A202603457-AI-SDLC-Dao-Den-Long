"""Island scenery (built from the standard map of each Night) + character/prop factories.
Decor is view-only (not in the sim). Colours of the listed components follow the Ticket-02 palette."""
import math
import random

from panda3d.core import BitMask32
from ursina import DirectionalLight, Entity, Text, Vec3, color, scene
from ursina.models.procedural.cone import Cone
from ursina.models.procedural.cylinder import Cylinder

from game.view import gfx
from game.view.gfx import WORLD_SHADER, U, bake, glow

H = color.hex
C = color.rgb
NO_SHADOW = BitMask32.bit(5)

# --- Ticket-02 standard palette (listed components) ---
SKY, FOG = H("#0E1430"), H("#1B2350")
GRASS, SAND, WOOD, SEA = H("#2F5D50"), H("#C9B48A"), H("#6B4A2F"), H("#12384A")
LIT, CORE, OFF = H("#FFB347"), H("#FFE9B0"), H("#5B5F6E")
MOTE, HALO = H("#FFF6C2"), H("#FFE58A")
SHADE, RIM, STUN = H("#120A1A"), H("#7A3CFF"), H("#3A3450")
SHIRT, SCARF = H("#E8E2D0"), H("#C8102E")
GOLD, DRIFT = H("#F2C14E"), H("#8FA3B8")
RIM_CB = H("#00B3FF")   # colour-blind palette: shade rim + eyes
# --- own choices for other details ---
CLIFF = C(.36, .30, .26)
UNDER = C(.20, .18, .24)
GRASS_TUFT = (C(.22, .44, .36), C(.27, .50, .40), C(.33, .56, .44))
FLOWERS = (C(1, .92, .55), C(1, 1, .95), C(.98, .58, .50), C(.85, .70, 1))
STONE = C(.58, .58, .60)
BAMBOO = (C(.44, .62, .34), C(.38, .56, .30))
LEAF = C(.30, .50, .26)
BLOSSOM = (C(1.0, .62, .72), C(1.0, .76, .82), C(.95, .54, .66))
CANOPY = (C(.16, .34, .28), C(.20, .40, .32))


def W(**kw):
    e = Entity(shader=WORLD_SHADER, **kw)
    e.double_sided = True
    return e


def islands(m):
    n = m.night
    if n == 1:
        return [(0.0, 0.0, 40.0)]
    if n == 2:
        return [(0.0, 0.0, 28.0), (70.0, 0.0, 28.0)]
    return [(0.0, 0.0, 45.0)]


def _slab(parent, cx, cz, R, rng):
    g = Entity(parent=parent)
    Entity(parent=g, model=Cylinder(40, R, -1.6, 1.55), position=(cx, 0, cz), color=CLIFF)
    Entity(parent=g, model=Cone(12, R * .97, R * .3), rotation_x=180, position=(cx, -1.6, cz), color=UNDER)
    for _ in range(int(R / 2.5)):
        a = rng.uniform(0, 6.283)
        Entity(parent=g, model="icosphere", position=(cx + R * .96 * math.cos(a), -2, cz + R * .96 * math.sin(a)),
               scale=(rng.uniform(2, 3.5), rng.uniform(2, 4), rng.uniform(2, 3.5)), color=UNDER)
    bake(g)
    g.hide(NO_SHADOW)
    top = W(parent=parent, model=gfx.disc_mesh(R, 72, 0.0), position=(cx, 0, cz), color=GRASS)
    top.hide(NO_SHADOW)


def _night3_tiers(parent):
    t = Entity(parent=parent)
    a0, a1 = 0.0, math.pi
    W(parent=t, model=gfx.sector_mesh(12, 24, a0, a1, 3.0, 48), color=GRASS)
    W(parent=t, model=gfx.arc_wall(24, a0, a1, 0, 3, 48), color=CLIFF)
    W(parent=t, model=gfx.arc_wall(12, a0, a1, 0, 3, 32), color=CLIFF)
    for a in (a0, a1):
        W(parent=t, model=gfx.quad_mesh(gfx.P(12, a, 0), gfx.P(24, a, 0), gfx.P(24, a, 3), gfx.P(12, a, 3)), color=CLIFF)
    W(parent=t, model=gfx.sector_mesh(0, 8, 0, 2 * math.pi, 6.0, 40), color=GRASS)
    W(parent=t, model=gfx.arc_wall(8, 0, 2 * math.pi, 0, 6, 40), color=CLIFF)
    for deg in (30, 150):
        a = math.radians(deg)
        ux, uz = math.cos(a), math.sin(a)
        px, pz = -uz * 1.5, ux * 1.5
        p0 = Vec3(30 * ux + px, .02, 30 * uz + pz)
        p1 = Vec3(30 * ux - px, .02, 30 * uz - pz)
        p2 = Vec3(24 * ux - px, 3.02, 24 * uz - pz)
        p3 = Vec3(24 * ux + px, 3.02, 24 * uz + pz)
        W(parent=t, model=gfx.quad_mesh(p0, p1, p2, p3), color=SAND)
        for side in (1, -1):
            b0 = Vec3(30 * ux + side * px, 0, 30 * uz + side * pz)
            b1 = Vec3(24 * ux + side * px, 0, 24 * uz + side * pz)
            b2 = Vec3(24 * ux + side * px, 3, 24 * uz + side * pz)
            W(parent=t, model=gfx._mesh([b0, b1, b2]), color=CLIFF)
    tw = Entity(parent=parent)  # bell tower (8 m, r = 2) on tier 2
    Entity(parent=tw, model=Cylinder(10, 2.0, 6, 6.2), color=C(.62, .55, .50))
    Entity(parent=tw, model=Cylinder(10, 2.2, 12.2, .3), color=WOOD)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        Entity(parent=tw, model=Cylinder(6, .15, 12.5, 1.5), position=(1.6 * math.cos(a), 0, 1.6 * math.sin(a)), color=WOOD)
    Entity(parent=tw, model=Cone(4, 2.8, 1.6), y=14.0, rotation_y=45, color=C(.45, .22, .18))
    Entity(parent=tw, model=Cone(12, .9, 1.1), y=12.6, color=GOLD)
    bake(tw)


def _bridge(parent):
    b = Entity(parent=parent)
    for k in range(37):
        Entity(parent=b, model="cube", position=(26 + k * .5, -.04, 0), scale=(.42, .12, 4.0), color=WOOD if k % 2 else C(.50, .36, .24))
    for x in (26.5, 35, 43.5):
        for z in (-2.1, 2.1):
            Entity(parent=b, model=Cylinder(6, .15, -6, 6.1), position=(x, 0, z), color=WOOD)
    bake(b)


def build_world(m):
    """Static scenery for NightMap m. Returns (island root for shadow bounds, extra roots)."""
    rng = random.Random(23 + m.night)
    root = Entity()
    for cx, cz, R in islands(m):
        _slab(root, cx, cz, R, rng)
    if m.night == 2:
        _bridge(root)
    if m.night == 3:
        _night3_tiers(root)
    for pad in m.pads:
        U(parent=root, model=gfx.disc_mesh(1.0, 24, .05), position=(pad.x, pad.y, pad.z), color=GOLD)
        ring = U(parent=root, model=gfx.ring_mesh(1.25, .12, 40), position=(pad.x, pad.y + .06, pad.z), color=color.rgba(1, .9, .5, .8))
        gfx.additive(ring)
        ang = math.degrees(math.atan2(pad.hx, pad.hz))
        U(parent=root, model=Cone(3, .35, .7), position=(pad.x, pad.y + .1, pad.z), rotation=(90, ang, 0), color=SCARF)

    st = Entity(parent=root)  # sand stepping stones
    for _, (lx, ly, lz) in m.lanterns:
        for k in range(10):
            a = 2 * math.pi * k / 10
            Entity(parent=st, model=Cylinder(5, .33, ly, .05), position=(lx + 2.3 * math.cos(a), 0, lz + 2.3 * math.sin(a)), color=SAND)
    for cx, cz, R in islands(m):
        rr = R * .62
        n = int(2 * math.pi * rr / 1.3)
        for i in range(n):
            a = 2 * math.pi * i / n
            x, z = cx + rr * math.cos(a), cz + rr * math.sin(a)
            g = m.ground(x, z)
            if g is None or g != 0.0 or (m.night == 3 and 11.5 < math.hypot(x, z) < 31):
                continue
            Entity(parent=st, model=Cylinder(6, rng.uniform(.45, .62), 0, .05), position=(x, 0, z), rotation_y=rng.uniform(0, 60), color=SAND)
    bake(st)
    st.hide(NO_SHADOW)

    d = Entity(parent=root)
    lan_xz = [(p[0], p[2]) for _, p in m.lanterns]
    pad_xz = [(p.x, p.z) for p in m.pads]
    mote_xz = [(p[0], p[2]) for p in m.mote_points]

    def ok(x, z, pad):
        g = m.ground(x, z)
        if g is None or g not in (0.0, 3.0, 6.0):
            return None
        if any(math.hypot(x - a, z - b) < 4 + pad for a, b in lan_xz + pad_xz):
            return None
        if any(math.hypot(x - a, z - b) < 1.2 + pad * .6 for a, b in mote_xz):
            return None
        if math.hypot(x - m.start[0], z - m.start[2]) < 3 + pad:
            return None
        if m.night == 2 and 24 <= x <= 46 and abs(z) < 4:
            return None
        if m.night == 3:
            r = math.hypot(x, z)
            if r < 2.6 or any(abs(r - e) < .6 + pad * .3 for e in (8, 12, 24)):
                return None
        return g

    def spot(pad, tries=60):
        for _ in range(tries):
            cx, cz, R = rng.choice(islands(m))
            a, r = rng.uniform(0, 6.283), math.sqrt(rng.uniform(4, (R - 1.5) ** 2))
            x, z = cx + r * math.cos(a), cz + r * math.sin(a)
            g = ok(x, z, pad)
            if g is not None:
                return x, g, z
        return None

    area = sum(R * R for _, _, R in islands(m)) / 1600
    for _ in range(int(380 * area)):
        p = spot(0)
        if p:
            Entity(parent=d, model=Cone(3, rng.uniform(.05, .09), rng.uniform(.25, .45)), position=p,
                   rotation_y=rng.uniform(0, 120), color=rng.choice(GRASS_TUFT))
    for _ in range(int(150 * area)):
        p = spot(0)
        if p:
            Entity(parent=d, model="icosphere", position=(p[0], p[1] + .12, p[2]), scale=.13, color=rng.choice(FLOWERS))
    for _ in range(int(26 * area)):
        p = spot(.4)
        if p:
            s = rng.uniform(.4, 1.0)
            Entity(parent=d, model="icosphere", position=(p[0], p[1] + s * .25, p[2]), scale=(s * 1.3, s * .8, s),
                   rotation_y=rng.uniform(0, 360), color=STONE)
    for _ in range(int(8 * area)):
        p = spot(2.2)
        if not p:
            continue
        for _k in range(rng.randint(5, 8)):
            x, z = p[0] + rng.uniform(-1.1, 1.1), p[2] + rng.uniform(-1.1, 1.1)
            if ok(x, z, 1.0) is None:
                continue
            h = rng.uniform(4, 6.5)
            Entity(parent=d, model=Cylinder(6, .09, 0, h), position=(x, p[1], z), color=rng.choice(BAMBOO))
            for j in range(1, int(h)):
                Entity(parent=d, model=Cylinder(6, .11, j, .06), position=(x, p[1], z), color=C(.34, .48, .24))
            for _l in range(3):
                Entity(parent=d, model="icosphere", position=(x + rng.uniform(-.5, .5), p[1] + h - rng.uniform(0, 1.2), z + rng.uniform(-.5, .5)),
                       scale=(rng.uniform(.6, 1.0), .25, rng.uniform(.4, .7)), rotation_y=rng.uniform(0, 180), color=LEAF)
    for _ in range(int(11 * area)):
        p = spot(2.0)
        if not p:
            continue
        s = rng.uniform(.9, 1.25)
        Entity(parent=d, model=Cylinder(6, .2 * s, 0, 1.6 * s), position=p, color=WOOD)
        for _k in range(4):
            Entity(parent=d, model="icosphere", position=(p[0] + rng.uniform(-.8, .8) * s, p[1] + (1.9 + rng.uniform(0, .9)) * s,
                                                          p[2] + rng.uniform(-.8, .8) * s),
                   scale=rng.uniform(1.0, 1.4) * s, color=rng.choice(BLOSSOM))
    for cx, cz, R in islands(m):
        for _ in range(int(R * .55)):
            a = rng.uniform(0, 6.283)
            r = rng.uniform(R - 6, R - 1.8)
            x, z = cx + r * math.cos(a), cz + r * math.sin(a)
            g = ok(x, z, 1.5)
            if g is None:
                continue
            s = rng.uniform(1.0, 1.4)
            Entity(parent=d, model=Cylinder(6, .22 * s, 0, 1.2 * s), position=(x, g, z), color=WOOD)
            Entity(parent=d, model="icosphere", position=(x, g + 2.2 * s, z), scale=(2.3 * s, 2.1 * s, 2.3 * s), color=rng.choice(CANOPY))
        nf = int(2 * math.pi * R / 3)
        for k in range(nf):
            a = 2 * math.pi * k / nf
            x, z = cx + (R - .8) * math.cos(a), cz + (R - .8) * math.sin(a)
            if m.night == 2 and abs(z) < 3.5:
                continue
            Entity(parent=d, model="cube", position=(x, .45, z), scale=(.14, .9, .14), color=WOOD)
    bake(d)

    U(model="circle", position=(-60, 70, 160), scale=22, color=C(.98, .96, .86), billboard=True)
    glow(position=(-60, 70, 159), scale=80, col=(.75, .80, 1, .3))
    sk = Entity()
    for _ in range(160):
        a, el = rng.uniform(0, 6.283), rng.uniform(.25, 1.2)
        Entity(parent=sk, model="cube", scale=rng.uniform(.4, 1.0),
               position=(220 * math.cos(el) * math.sin(a), 220 * math.sin(el) - 20, 220 * math.cos(el) * math.cos(a)),
               color=color.rgba(1, 1, .9, rng.uniform(.4, .9)))
    sk.combine()
    sk.shader = gfx.unlit_shader
    sk.setLightOff()
    cl = Entity()
    off = 35.0 if m.night == 2 else 0.0
    for _ in range(110):
        a, r = rng.uniform(0, 6.283), rng.uniform(55, 170)
        s = rng.uniform(5, 12)
        Entity(parent=cl, model="icosphere", position=(off + r * math.sin(a), rng.uniform(-14, -7), r * math.cos(a)),
               scale=(s * 1.6, s * .45, s), color=rng.choice((SEA, C(.09, .26, .34), C(.14, .30, .38))))
    bake(cl)
    cl.hide(NO_SHADOW)
    return root, [sk, cl]


def setup_lighting(island):
    moon = DirectionalLight(shadows=True)
    moon.shadow_map_resolution = (1024, 1024)
    moon._light.setCameraMask(NO_SHADOW)
    moon.look_at(Vec3(.5, -1, -.35))
    moon.color = C(.95, .98, 1.12)
    moon.update_bounds(island)
    scene.set_shader_input("lamp_col", (1.0, .62, .28, 9.0))
    scene.set_shader_input("fog_col", (FOG[0], FOG[1], FOG[2]))
    scene.set_shader_input("fog_range", (70.0, 180.0))
    for i in range(8):
        scene.set_shader_input(f"lamp{i}", (0.0, 0.0, 0.0, 0.0))
    set_ambience(0.0)
    return moon


def set_ambience(ratio):
    """Ticket-02: ambient intensity = 0.15 + 0.55 * (lit / total)."""
    k = 0.15 + 0.55 * ratio
    scene.set_shader_input("sky_amb", (k * .92, k * .98, k * 1.12))
    scene.set_shader_input("ground_amb", (k * .62, k * .58, k * .70))


def set_lamp(i, x, y, z, intensity, small=False):
    scene.set_shader_input(f"lamp{i}", (x, (100.0 + y) if small else y, z, intensity))


# ---------------- characters & props ----------------
def make_may():
    """Mây: chibi lantern-keeper, cream shirt (#E8E2D0), red scarf (#C8102E), nón lá with a tiny lantern on the brim."""
    root = Entity(scale=1.65)
    body = Entity(parent=root)
    b = Entity(parent=body)
    for sx in (-.11, .11):
        Entity(parent=b, model=Cylinder(6, .07, 0, .26), position=(sx, 0, 0), color=C(.20, .17, .20))
    Entity(parent=b, model="icosphere", y=.48, scale=(.52, .56, .44), color=SHIRT)
    Entity(parent=b, model="cube", position=(0, .40, .21), scale=(.06, .3, .02), color=C(.55, .45, .35))
    Entity(parent=b, model=Cylinder(10, .2, .72, .1), color=SCARF)
    Entity(parent=b, model="cube", position=(.1, .66, .15), rotation_z=-25, scale=(.08, .22, .04), color=SCARF)
    Entity(parent=b, model="icosphere", y=1.05, scale=(.56, .54, .52), color=C(.99, .86, .73))
    Entity(parent=b, model="icosphere", position=(0, 1.1, -.06), scale=(.6, .52, .52), color=C(.12, .09, .10))
    for sx in (-.1, .1):
        Entity(parent=b, model="icosphere", position=(sx, 1.05, .26), scale=(.06, .08, .03), color=C(.12, .09, .10))
    Entity(parent=b, model=Cone(20, .58, .36), y=1.3, color=C(.94, .85, .62))
    Entity(parent=b, model=Cylinder(20, .59, 1.28, .03), color=C(.80, .68, .46))
    bake(b)
    pivot = Entity(parent=body, position=(.46, 1.29, .24))
    U(parent=pivot, model=Cylinder(4, .012, -.24, .24), color=C(.2, .15, .1))
    U(parent=pivot, model="sphere", scale=(.17, .21, .17), y=-.33, color=LIT)
    halo = glow(parent=pivot, y=-.33, scale=1.3, col=(1, .70, .28, .6))
    root.body, root.pivot, root.halo = body, pivot, halo
    return root


def make_lantern(lid, x, y, z, safe_radius):
    root = Entity(position=(x, y, z))
    s = Entity(parent=root)
    Entity(parent=s, model="cube", y=.25, scale=(1.5, .5, 1.5), color=STONE)
    Entity(parent=s, model=Cylinder(8, .16, .5, 3.7), color=WOOD)
    Entity(parent=s, model="cube", position=(.55, 4.05, 0), scale=(1.3, .14, .14), color=WOOD)
    Entity(parent=s, model="cube", position=(1.15, 4.18, 0), rotation_z=-35, scale=(.4, .12, .12), color=WOOD)
    Entity(parent=s, model="icosphere", y=4.25, scale=.3, color=GOLD)
    bake(s)
    hx = 1.05
    W(parent=root, model=Cylinder(4, .015, 3.45, .6), x=hx, color=C(.2, .15, .1))
    silk = W(parent=root, model=gfx.flat("icosphere"), position=(hx, 2.85, 0), scale=(.95, 1.15, .95), color=OFF)
    for yy in (2.27, 3.38):
        W(parent=root, model=Cylinder(8, .3, 0, .1), position=(hx, yy, 0), color=GOLD)
    W(parent=root, model=Cone(6, .1, .45), position=(hx, 1.82, 0), rotation_x=180, color=GOLD)
    lamp = U(parent=root, model="sphere", position=(hx, 2.85, 0), scale=(.97, 1.17, .97), color=LIT, visible=False)
    core = U(parent=root, model="sphere", position=(hx, 2.85, 0), scale=.45, color=CORE, visible=False)
    halo = glow(parent=root, position=(hx, 2.85, 0), scale=5.5, col=(1, .70, .28, 0))
    ring = U(parent=root, model=gfx.ring_mesh(safe_radius, .1, 72), y=.07, color=color.rgba(1, .7, .28, 0))
    gfx.additive(ring)
    tag = Text("", parent=root, y=5.0, scale=15, origin=(0, 0), billboard=True, color=H("#F5F1E6"))
    tag.setLightOff()
    # torn paper (visible while the lantern is out) - shape cue that does not rely on colour
    tear = U(parent=silk, model="cube", position=(.18, -.05, .46), rotation=(0, 20, 35), scale=(.32, .45, .05), color=C(.10, .10, .13))
    tear2 = U(parent=silk, model="cube", position=(-.25, .2, .43), rotation=(0, -15, -20), scale=(.18, .3, .05), color=C(.10, .10, .13))
    # fuel bar (billboard) above lit lanterns
    bar = Entity(parent=root, y=4.45, billboard=True)
    U(parent=bar, model="quad", scale=(1.6, .2), color=color.rgba(0, 0, 0, .55))
    fill = U(parent=bar, model="quad", origin=(-.5, 0), x=-.75, z=-.01, scale=(1.5, .12), color=LIT)
    return {"root": root, "paper": silk, "lamp": lamp, "core": core, "halo": halo, "ring": ring, "tag": tag, "k": 0.0, "id": lid,
            "tears": [tear, tear2], "bar": bar, "fill": fill, "hx": hx}


_SHADE_MESH = None
_EYES_MESH = None


def _shade_meshes():
    """Shared meshes: one flat-shaded ink droplet (body + cap + tail) and one mesh for both eyes."""
    global _SHADE_MESH, _EYES_MESH
    if _SHADE_MESH is None:
        tmp = Entity()
        Entity(parent=tmp, model="icosphere", scale=(1.2, 1.15, 1.2))
        Entity(parent=tmp, model=Cone(10, .48, .8), y=.4)
        for i in range(3):
            Entity(parent=tmp, model="icosphere", position=(0, -.25 - .1 * i, -.55 - .35 * i), scale=.5 - .12 * i)
        bake(tmp)
        _SHADE_MESH, tmp.model = tmp.model, None
        tmp.disable()
        ey = Entity()
        for dx in (-.2, .2):
            Entity(parent=ey, model="icosphere", scale=(.16, .2, .08), position=(dx, .08, .55))
        ey.combine()
        _EYES_MESH, ey.model = ey.model, None
        ey.disable()
    return _SHADE_MESH, _EYES_MESH


def make_shade():
    """Bóng Mực: ink droplet (#120A1A) with a violet rim glow (#7A3CFF). 3 nodes per shade (bench: 200 shades)."""
    body_m, eyes_m = _shade_meshes()
    root = Entity()
    body = W(parent=root, model=body_m, color=SHADE)
    rim = glow(parent=root, scale=2.0, col=(RIM[0], RIM[1], RIM[2], .6))
    eyes = U(parent=root, model=eyes_m, color=C(.85, .75, 1))
    eyes.hide(NO_SHADOW)
    root.body, root.rim, root.eyes = body, rim, eyes
    root.state = None
    return root


def make_mote(dropped=False):
    e = U(model="icosphere", scale=.22, color=MOTE)
    e.hide(NO_SHADOW)
    glow(parent=e, scale=6.0, col=(HALO[0], HALO[1], HALO[2], .4 if dropped else .55))
    return e


def make_drifter():
    """Gió Lạc: a grey-blue silk ribbon (#8FA3B8) made of fluttering segments."""
    root = Entity()
    root.segs = [U(parent=root, model="cube", scale=(.7 - .07 * i, .05, .45), color=color.rgba(DRIFT[0], DRIFT[1], DRIFT[2], 1 - .1 * i))
                 for i in range(7)]
    for dx in (-.12, .12):
        U(parent=root.segs[0], model="sphere", scale=(.12, 2.0, .18), position=(dx, 1.2, .25), color=C(.15, .18, .25))
    return root


def make_charm():
    """Bùa Gió: red talisman (#C8102E) with a gold border (#F2C14E)."""
    root = Entity()
    U(parent=root, model="cube", scale=(.62, .9, .04), color=GOLD)
    U(parent=root, model="cube", scale=(.5, .78, .06), color=SCARF)
    U(parent=root, model="cube", scale=(.08, .5, .07), color=GOLD)
    glow(parent=root, scale=2.6, col=(1, .35, .3, .45))
    return root
