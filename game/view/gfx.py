"""Rendering helpers: world shader, flat-shaded mesh baking, path/ring meshes, additive glows."""
import math

from panda3d.core import ColorBlendAttrib
from ursina import Entity, Mesh, Shader, Vec3, color, load_model
from ursina.shaders import unlit_shader


def U(**kw):
    """Unlit entity (emissive things: glows, motes, eyes, labels) - ignores the sun."""
    e = Entity(shader=unlit_shader, **kw)
    e.setLightOff()
    return e

WORLD_SHADER = Shader(language=Shader.GLSL, name="island_shader", vertex="""
#version 150
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat3 p3d_NormalMatrix;
uniform struct {
    vec4 position; vec3 color; vec3 attenuation; vec3 spotDirection;
    float spotCosCutoff; float spotExponent; sampler2DShadow shadowMap; mat4 shadowViewMatrix;
} p3d_LightSource[1];
in vec4 vertex;
in vec3 normal;
in vec4 p3d_Color;
out vec3 vpos; out vec3 vnorm; out vec3 wpos; out vec3 wnorm; out vec4 shad; out vec4 vcol;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * vertex;
    vpos = (p3d_ModelViewMatrix * vertex).xyz;
    vnorm = normalize(p3d_NormalMatrix * normal);
    wpos = (p3d_ModelMatrix * vertex).xyz;
    wnorm = normalize(mat3(p3d_ModelMatrix) * normal);
    shad = p3d_LightSource[0].shadowViewMatrix * vec4(vpos, 1.0);
    vcol = p3d_Color;
}
""", fragment="""
#version 150
uniform struct {
    vec4 position; vec3 color; vec3 attenuation; vec3 spotDirection;
    float spotCosCutoff; float spotExponent; sampler2DShadow shadowMap; mat4 shadowViewMatrix;
} p3d_LightSource[1];
uniform vec4 p3d_ColorScale;
uniform vec3 sky_amb; uniform vec3 ground_amb; uniform vec3 fog_col;
uniform vec2 fog_range;
uniform vec4 lamp0; uniform vec4 lamp1; uniform vec4 lamp2; uniform vec4 lamp3; uniform vec4 lamp4; uniform vec4 lamp5; uniform vec4 lamp6; uniform vec4 lamp7;
uniform vec4 lamp_col;
in vec3 vpos; in vec3 vnorm; in vec3 wpos; in vec3 wnorm; in vec4 shad; in vec4 vcol;
out vec4 p3d_FragColor;
float pool(vec4 l) {
    float d = distance(wpos.xz, vec2(l.x, l.z));
    float small = l.y > 50.0 ? 0.45 : 1.0;
    float h = l.y > 50.0 ? l.y - 100.0 : l.y;
    float dh = clamp(1.0 - abs(wpos.y - h) / 4.0, 0.0, 1.0);
    return l.w * dh * (1.0 - smoothstep(0.0, lamp_col.w * small, d));
}
void main() {
    vec4 base = p3d_ColorScale * vcol;
    vec3 N = normalize(vnorm);
    vec3 L = normalize(p3d_LightSource[0].position.xyz);
    float ndl = max(dot(N, L), 0.0);
    vec4 sc = shad; sc.z += 0.004 + 0.008 * (1.0 - ndl);
    float lit = textureProj(p3d_LightSource[0].shadowMap, sc);
    vec3 amb = mix(ground_amb, sky_amb, clamp(wnorm.y * 0.5 + 0.5, 0.0, 1.0));
    float warm = pool(lamp0) + pool(lamp1) + pool(lamp2) + pool(lamp3) + pool(lamp4) + pool(lamp5) + pool(lamp6) + pool(lamp7);
    vec3 light = amb + p3d_LightSource[0].color * ndl * mix(0.35, 1.0, lit) + lamp_col.rgb * warm;
    vec3 c = base.rgb * light;
    float f = smoothstep(fog_range.x, fog_range.y, length(vpos));
    p3d_FragColor = vec4(mix(c, fog_col, f), base.a);
}
""")


def _tris(model):
    if model.triangles:
        flat = []
        for t in model.triangles:
            if isinstance(t, int):
                flat.append(t)
            elif len(t) == 3:
                flat.extend(t)
            elif len(t) == 4:
                flat.extend([t[0], t[1], t[2], t[2], t[3], t[0]])
        return flat
    return list(range(len(model.vertices)))


def bake(root: Entity, destroy_children=True):
    """Merge every child model under root into one flat-shaded, vertex-coloured mesh (low-poly look)."""
    from ursina import destroy
    verts, norms, cols = [], [], []
    kids = [e for e in _walk(root) if e is not root and getattr(e, "model", None) is not None]
    for e in kids:
        m = e.model
        if not getattr(m, "vertices", None):
            m = load_model(m.name, use_deepcopy=True)
        mat = e.model.getTransform(root).getMat()
        centre = mat.xformPoint(Vec3(0, 0, 0))
        wv = [Vec3(*mat.xformPoint(Vec3(*v))) for v in m.vertices]
        vc = m.colors if m.colors else None
        idx = _tris(m)
        for i in range(0, len(idx) - 2, 3):
            a, b, c = wv[idx[i]], wv[idx[i + 1]], wv[idx[i + 2]]
            n = (b - a).cross(c - a)
            if n.length() < 1e-9:
                continue
            n = n.normalized()
            fc = (a + b + c) / 3
            d = n.dot(fc - centre)
            if d < -1e-6 or (abs(d) <= 1e-6 and n.y < 0):
                n = -n
            for k in (idx[i], idx[i + 1], idx[i + 2]):
                verts.append(wv[k])
                norms.append(n)
                cols.append(color.Color(*vc[k]) * e.color if vc else e.color)
    if destroy_children:
        for e in kids:
            if e is not root:
                destroy(e)
    root.model = Mesh(vertices=verts, normals=norms, colors=cols, mode="triangle")
    root.color = color.white
    root.shader = WORLD_SHADER
    root.double_sided = True
    return root


def _walk(e):
    yield e
    for c in e.children:
        yield from _walk(c)


def flat(model_or_name):
    """Flat-shaded copy of a single model (for dynamic entities)."""
    tmp = Entity()
    Entity(parent=tmp, model=model_or_name)
    bake(tmp)
    m = tmp.model
    tmp.model = None
    from ursina import destroy
    destroy(tmp)
    return m


def strip_mesh(points, width, y=0.02, closed=False):
    """Flat ribbon along XZ points (paths)."""
    verts = []
    n = len(points)
    rng = range(n if closed else n - 1)
    for i in rng:
        p0, p1 = points[i], points[(i + 1) % n]
        dx, dz = p1[0] - p0[0], p1[1] - p0[1]
        ln = math.hypot(dx, dz) or 1
        ox, oz = -dz / ln * width / 2, dx / ln * width / 2
        a = Vec3(p0[0] + ox, y, p0[1] + oz)
        b = Vec3(p0[0] - ox, y, p0[1] - oz)
        c = Vec3(p1[0] - ox, y, p1[1] - oz)
        d = Vec3(p1[0] + ox, y, p1[1] + oz)
        verts += [a, b, c, a, c, d]
    for i in range(1, n - 1) if not closed else range(n):  # round joints
        p = points[i]
        for k in range(8):
            t0, t1 = k / 8 * 2 * math.pi, (k + 1) / 8 * 2 * math.pi
            r = width / 2
            verts += [Vec3(p[0], y, p[1]), Vec3(p[0] + r * math.cos(t0), y, p[1] + r * math.sin(t0)),
                      Vec3(p[0] + r * math.cos(t1), y, p[1] + r * math.sin(t1))]
    return Mesh(vertices=verts, normals=[Vec3(0, 1, 0)] * len(verts), mode="triangle")


def ring_points(r, n=96):
    return [(r * math.sin(2 * math.pi * i / n), r * math.cos(2 * math.pi * i / n)) for i in range(n)]


def ring_mesh(r, width, n=96):
    return strip_mesh(ring_points(r, n), width, y=0, closed=True)


def disc_mesh(r, n=48, y=0.0):
    verts = []
    for i in range(n):
        t0, t1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        verts += [Vec3(0, y, 0), Vec3(r * math.sin(t0), y, r * math.cos(t0)), Vec3(r * math.sin(t1), y, r * math.cos(t1))]
    return Mesh(vertices=verts, normals=[Vec3(0, 1, 0)] * len(verts), mode="triangle")


def additive(e: Entity):
    e.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add, ColorBlendAttrib.O_incoming_alpha, ColorBlendAttrib.O_one))
    e.setDepthWrite(False)
    e.setBin("transparent", 10)
    return e


def glow(parent=None, scale=1.0, col=(1, .8, .45, .8), **kw):
    e = U(parent=parent, model="quad", texture="radial_gradient", billboard=True, scale=scale,
          color=color.rgba(*col), **kw)
    return additive(e)


def _mesh(verts):
    """Triangle list -> Mesh with flat normals (double-sided use)."""
    norms = []
    for i in range(0, len(verts), 3):
        a, b, c = verts[i], verts[i + 1], verts[i + 2]
        n = (b - a).cross(c - a)
        n = n.normalized() if n.length() > 1e-9 else Vec3(0, 1, 0)
        if n.y < -1e-6:
            n = -n
        norms += [n, n, n]
    return Mesh(vertices=verts, normals=norms, mode="triangle")


def P(r, a, y):
    return Vec3(r * math.cos(a), y, r * math.sin(a))


def sector_mesh(r0, r1, a0, a1, y, n=40):
    """Flat annulus sector at height y. Angles in radians, CCW from +X (x = r cos a, z = r sin a)."""
    v = []
    for i in range(n):
        t0, t1 = a0 + (a1 - a0) * i / n, a0 + (a1 - a0) * (i + 1) / n
        v += [P(r0, t0, y), P(r1, t0, y), P(r1, t1, y), P(r0, t0, y), P(r1, t1, y), P(r0, t1, y)]
    return _mesh(v)


def arc_wall(r, a0, a1, y0, y1, n=40):
    v = []
    for i in range(n):
        t0, t1 = a0 + (a1 - a0) * i / n, a0 + (a1 - a0) * (i + 1) / n
        b0, b1, u0, u1 = P(r, t0, y0), P(r, t1, y0), P(r, t0, y1), P(r, t1, y1)
        v += [b0, b1, u1, b0, u1, u0]
    m = Mesh(vertices=v, normals=[Vec3(math.cos((a0 + a1) / 2), 0, math.sin((a0 + a1) / 2))] * len(v), mode="triangle")
    ns = []
    for i in range(0, len(v), 6):
        t = a0 + (a1 - a0) * (i // 6 + .5) / n
        ns += [Vec3(math.cos(t), 0, math.sin(t))] * 6
    m.normals = ns
    m.generate()
    return m


def quad_mesh(a, b, c, d):
    return _mesh([a, b, c, a, c, d])
