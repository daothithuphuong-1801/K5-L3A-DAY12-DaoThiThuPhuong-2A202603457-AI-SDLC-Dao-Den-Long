"""HUD + screens. Layout follows Ticket-02 (flames top-left, timer top-centre, lanterns+score top-right,
mote bar bottom-centre, dash/pulse cooldowns bottom-right, lantern prompt, off-screen arrow).
Ticket-04: every UI text >= 18 px at 1280x720 (Text scale 1.0 = 0.025 * 720 = 18 px), optional large text x1.25,
captions for important events, key rebinding, leaderboard screens.
Look: rounded Mali font, night-navy glass panels, UI text #F5F1E6, gold #F2C14E, danger #FF5A5F."""
import math
import textwrap
from pathlib import Path

from panda3d.core import Filename
from ursina import Button, Entity, InputField, Quad, Slider, Text, camera, color, time

FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"


def _font(name):
    return Filename.fromOsSpecific(str(FONT_DIR / name)).getFullpath()


REG, SEMI, BOLD = _font("Mali-Regular.ttf"), _font("Mali-SemiBold.ttf"), _font("Mali-Bold.ttf")
Text.default_font = REG

H, C, A = color.hex, color.rgb, color.rgba
TXT = H("#F5F1E6")
GOLD = H("#F2C14E")
DANGER = H("#FF5A5F")
DANGER_CB = H("#FFFFFF")  # colour-blind palette: white + warning icon
SCARF = H("#C8102E")
LIT = H("#FFB347")
OFF = H("#5B5F6E")
SHADE_ARROW = H("#B58CFF")
PANEL = A(.055, .078, .19, .82)       # #0E1430 glass
CARD = A(.07, .10, .23, .97)
SOFT = A(.96, .95, .90, .75)
GHOST = A(1, 1, 1, .14)
DARK = C(.10, .09, .14)

L_PANEL, L_ICON, L_FILL, L_TEXT = 10, 20, 25, 40
M_DIM, M_CARD, M_ICON, M_TEXT = 60, 65, 70, 80

MIN_TEXT = 1.0   # Text scale 1.0 == 18 px line at 720 p
FS = 1.0         # 1.25 when "Chữ lớn" is on (set before building the UI)

ACTIONS = (("up", "Đi lên"), ("down", "Đi xuống"), ("left", "Sang trái"), ("right", "Sang phải"), ("jump", "Nhảy"),
           ("dash", "Lướt"), ("interact", "Tương tác (E)"), ("pulse", "Tỏa Sáng"), ("pause", "Tạm dừng"))
KEY_NAMES = {"up arrow": "↑", "down arrow": "↓", "left arrow": "←", "right arrow": "→", "space": "Space", "shift": "Shift",
             "escape": "Esc", "enter": "Enter", "tab": "Tab", "backspace": "Backspace", "control": "Ctrl", "alt": "Alt"}


def key_label(k):
    return KEY_NAMES.get(k, k.upper() if len(k) == 1 else k)


def layer(e, n):
    for x in [e] + list(e.get_descendants() if hasattr(e, "get_descendants") else []):
        try:
            x.setBin("fixed", n)
            x.setDepthTest(False)
            x.setDepthWrite(False)
        except Exception:  # noqa: BLE001
            pass
    return e


def txt(s, x, y, size=1.0, font=REG, col=TXT, origin=(-.5, 0), parent=None, lay=L_TEXT):
    sc = max(size, MIN_TEXT) * FS
    return layer(Text(s, parent=parent or camera.ui, position=(x, y), origin=origin, scale=sc, font=font, color=col), lay)


def rbox(x, y, w, h, col=PANEL, r=.02, parent=None, lay=L_PANEL, border=True):
    parent = parent or camera.ui
    e = layer(Entity(parent=parent, model=Quad(radius=min(.5, r / h), aspect=w / h), position=(x, y), scale=(w, h), color=col), lay)
    e.border = None
    if border:
        e.border = layer(Entity(parent=parent, model=Quad(radius=min(.5, (r + .002) / (h + .004)), aspect=(w + .004) / (h + .004)),
                                position=(x, y), scale=(w + .004, h + .004), color=A(.95, .76, .31, .35)), lay - 1)
    return e


def ent(lay=L_ICON, **kw):
    kw.setdefault("parent", camera.ui)
    return layer(Entity(**kw), lay)


def button(label, x, y, w, h, on_click, parent, primary=True, lay=M_ICON):
    label = label or " "  # Ursina creates no text_entity for an empty label
    b = Button(parent=parent, model=Quad(radius=.5, aspect=w / h), position=(x, y), scale=(w, h),
               color=GOLD if primary else A(1, 1, 1, .09), highlight_color=C(1, .86, .45) if primary else A(1, 1, 1, .2),
               pressed_color=GOLD if primary else A(1, 1, 1, .25), text=label, text_size=MIN_TEXT * FS)
    style_button(b, primary, lay)
    b.on_click = on_click
    return b


def style_button(b, primary=True, lay=M_ICON):
    b.text_entity.font = BOLD if primary else SEMI
    b.text_entity.color = DARK if primary else TXT
    layer(b, lay)
    layer(b.text_entity, lay + 2)


def set_button_text(b, label, primary=False, lay=M_ICON):
    b.text = label or " "
    style_button(b, primary, lay)


def flame_icon(x, y, parent, s=1.0, lay=L_ICON):
    root = ent(lay, parent=parent, position=(x, y))
    ent(lay, parent=root, model="circle", scale=.024 * s, color=LIT)
    ent(lay, parent=root, model="quad", y=.009 * s, rotation_z=45, scale=.017 * s, color=LIT)
    ent(lay + 1, parent=root, model="circle", y=-.003 * s, scale=.011 * s, color=H("#FFE9B0"))
    return root


def lantern_icon(x, y, parent, s=1.0, lay=L_ICON, col=LIT):
    root = ent(lay, parent=parent, position=(x, y))
    for yy in (.017, -.017):
        ent(lay, parent=root, model="quad", y=yy * s, scale=(.012 * s, .004 * s), color=GOLD)
    root.body = ent(lay, parent=root, model=Quad(radius=.5, aspect=.8), scale=(.024 * s, .03 * s), color=col)
    return root


def warn_icon(x, y, parent, col=GOLD, lay=L_ICON):
    """Small diamond with '!' (works in every font, also in colour-blind mode)."""
    root = ent(lay, parent=parent, position=(x, y))
    root.shape = ent(lay, parent=root, model=Quad(radius=.15), rotation_z=45, scale=.024, color=col)
    t = txt("!", x, y - .001, .8, BOLD, DARK, origin=(0, 0), parent=parent, lay=lay + 1)
    t.parent = root
    t.position = (0, -.001)
    return root


class Cooldown:
    """Round cooldown badge: key label + 16 dots filling clockwise + caption below."""

    def __init__(self, x, y, key, label, parent):
        self.bg = ent(L_ICON, parent=parent, model="circle", position=(x, y), scale=.074, color=PANEL)
        self.dots = [ent(L_FILL, parent=parent, model="circle", position=(x + .042 * math.sin(i / 16 * 6.283), y + .042 * math.cos(i / 16 * 6.283)),
                         scale=.008, color=GHOST) for i in range(16)]
        self.key = txt(key, x, y + .002, 1.0, BOLD, TXT, origin=(0, 0), parent=parent)
        self.lab = txt(label, x, y - .066, 1.0, SEMI, TXT, origin=(0, 0), parent=parent)

    def set(self, frac, usable, key=None):
        n = round(frac * 16)
        for i, d in enumerate(self.dots):
            d.color = GOLD if (i < n and usable) else GHOST
        self.key.color = TXT if usable and frac >= 1 else A(.96, .95, .90, .45)
        if key is not None and self.key.text != key:
            self.key.text = key


class Hud:
    def __init__(self, tun):
        self.t = tun
        self.root = Entity(parent=camera.ui)
        P = self.root
        self.colorblind = False
        self.reduce_motion = False
        self.keys = {}
        # top-left: flames + night label
        rbox(-.745, .445, .25, .072, parent=P, r=.036)
        self.flames = [flame_icon(-.82 + i * .06, .445, P, 1.25) for i in range(int(tun["flames"]))]
        self.night_lbl = txt("", -.865, .385, 1.0, SEMI, SOFT, parent=P)
        # top-centre: timer (+ warning icon in colour-blind mode)
        rbox(0, .445, .2, .076, parent=P, r=.038)
        self.timer = txt("", 0, .447, 1.7, BOLD, TXT, origin=(0, 0), parent=P)
        self.warn = warn_icon(-.135, .446, P, col=DANGER_CB)
        # top-right: lanterns k/n + score
        rbox(.675, .445, .4, .072, parent=P, r=.036)
        lantern_icon(.5, .445, P, 1.1)
        self.lamps = txt("", .522, .446, 1.0, BOLD, TXT, parent=P)
        txt("Điểm", .705, .446, 1.0, REG, SOFT, parent=P)
        self.score = txt("0", .862, .447, 1.25, BOLD, GOLD, origin=(.5, 0), parent=P)
        self.shown_score = 0.0
        # bottom-centre: firefly bar (capacity grows to 20)
        rbox(0, -.445, .84, .08, parent=P, r=.027)
        txt("Đom đóm", -.405, -.445, 1.0, SEMI, SOFT, parent=P)
        self.cells = [ent(L_FILL, parent=P, model=Quad(radius=.35, aspect=.6), position=(-.255 + i * .0222, -.445), scale=(.016, .034), color=GHOST)
                      for i in range(int(tun["capacity_max"]))]
        self.count = txt("", .405, -.445, 1.1, BOLD, TXT, origin=(.5, 0), parent=P)
        # bottom-right: cooldowns + charm
        self.dash = Cooldown(.64, -.385, "Shift", "Lướt", P)
        self.pulse = Cooldown(.8, -.385, "F", "Tỏa Sáng", P)
        self.charm_box = rbox(.72, -.27, .3, .05, A(.78, .06, .18, .85), r=.025, parent=P, lay=L_PANEL, border=False)
        self.charm_txt = txt("", .72, -.27, 1.0, SEMI, TXT, origin=(0, 0), parent=P)
        # lantern prompt, captions, off-screen arrows, toast, hit flash
        self.prompt_bg = rbox(0, -.345, .4, .056, PANEL, r=.028, parent=P, lay=L_PANEL)
        self.prompt = txt("", 0, -.345, 1.0, SEMI, TXT, origin=(0, 0), parent=P)
        self.caps = []
        for i in range(3):
            bg = rbox(0, -.27 + i * .062, .5, .052, A(0, 0, 0, .7), r=.026, parent=P, lay=L_PANEL + 4, border=False)
            ic = warn_icon(0, -.27 + i * .062, P, col=GOLD, lay=L_ICON + 6)
            tx = txt("", 0, -.27 + i * .062, 1.0, SEMI, TXT, origin=(0, 0), parent=P, lay=L_TEXT + 6)
            self.caps.append({"bg": bg, "icon": ic, "txt": tx})
        self.cap_items = []          # [text, seconds_left, key]
        self.arrow = self._arrow_parts(GOLD)
        self.shade_arrow = self._arrow_parts(SHADE_ARROW)
        self.toast_bg = rbox(0, .33, .3, .058, PANEL, r=.029, parent=P, lay=L_PANEL + 2)
        self.toast = txt("", 0, .33, 1.0, SEMI, TXT, origin=(0, 0), parent=P, lay=L_TEXT + 2)
        self.toast_left = 0.0
        self.flash = ent(5, parent=P, model="quad", scale=(3, 1), color=A(1, .35, .37, 0))
        self._toast_alpha(0)
        self._render_captions()

    def _arrow_parts(self, col):
        P = self.root
        return {"head": ent(L_ICON, parent=P, model=Quad(radius=0), scale=(.03, .03), color=col, rotation_z=45),
                "tip": ent(L_ICON, parent=P, model="circle", scale=.022, color=col),
                "txt": txt("", 0, 0, 1.0, SEMI, col, origin=(0, 0), parent=P)}

    # ---- toast / captions ----
    def _toast_alpha(self, k):
        self.toast.alpha = k
        self.toast_bg.alpha = .82 * k
        if self.toast_bg.border:
            self.toast_bg.border.alpha = .35 * k

    @staticmethod
    def _fit(box, text_e, pad):
        w = text_e.width * text_e.scale_x + pad
        for e in (box, box.border):
            if e is not None:
                e.scale_x = w + (.004 if e is box.border else 0)
                e.model = Quad(radius=.5, aspect=e.scale_x / e.scale_y)
        return w

    def say(self, msg, secs=2.6):
        self.toast.text = msg
        self._fit(self.toast_bg, self.toast, .06)
        self.toast_left = secs

    def caption(self, text, secs=3.0, key=None):
        """Subtitle / visual cue (accessibility). Same key replaces the previous caption."""
        self.cap_items = [c for c in self.cap_items if key is None or c[2] != key]
        self.cap_items.insert(0, [text, secs, key])
        self.cap_items = self.cap_items[:3]
        self._render_captions()

    def _render_captions(self):
        for i, slot in enumerate(self.caps):
            on = i < len(self.cap_items)
            for e in (slot["bg"], slot["icon"], slot["txt"]):
                e.enabled = on
            if on:
                slot["txt"].text = self.cap_items[i][0]
                w = self._fit(slot["bg"], slot["txt"], .09)
                slot["txt"].x = .018
                slot["icon"].x = -w / 2 + .03

    def hit(self):
        if not self.reduce_motion:
            self.flash.color = A(1, .35, .37, .28)

    def set_prompt(self, text):
        on = bool(text)
        self.prompt.text = text or ""
        self.prompt_bg.enabled = on
        if self.prompt_bg.border:
            self.prompt_bg.border.enabled = on
        if on:
            self._fit(self.prompt_bg, self.prompt, .05)

    def _place_arrow(self, parts, sx, sy, label):
        on = sx is not None
        for e in parts.values():
            e.enabled = on
        if not on:
            return
        k = min(.76 / max(abs(sx), 1e-6), .36 / max(abs(sy), 1e-6))
        x, y = sx * k, sy * k
        parts["head"].position = (x, y)
        parts["head"].rotation_z = 90 - math.degrees(math.atan2(sy, sx))
        parts["tip"].position = (x + sx * .022, y + sy * .022)
        parts["txt"].position = (x - sx * .06, y - sy * .05)
        parts["txt"].text = label

    def set_arrow(self, sx, sy, dist):
        self._place_arrow(self.arrow, sx, sy, f"{dist:.0f} m")

    def set_shade_arrow(self, sx, sy):
        self._place_arrow(self.shade_arrow, sx, sy, "Bóng Mực")

    def update(self, sim, clock, total_before):
        p, t = sim.player, self.t
        for i, f in enumerate(self.flames):
            on = i < p.flames
            for c in f.children:
                c.alpha = 1 if on else .18
            f.scale = 1 + (.06 * math.sin(clock * 5 + i) if on and not self.reduce_motion else 0)
        self.night_lbl.text = f"Đêm {sim.night} · {sim.map.name}"
        tl = max(0, math.ceil(sim.time_left_s))
        self.timer.text = f"{tl // 60:02d}:{tl % 60:02d}"
        danger = tl <= 30 and sim.state == "playing"
        self.timer.color = (DANGER_CB if self.colorblind else DANGER) if danger else TXT
        blink = danger and not self.reduce_motion
        self.timer.alpha = (.35 + .65 * (math.sin(clock * 10) > 0)) if blink else 1
        self.warn.enabled = danger and self.colorblind
        lit = sum(l.lit for l in sim.lanterns)
        self.lamps.text = f"{lit}/{len(sim.lanterns)} (cần {sim.need_lit})"
        self.lamps.color = TXT if lit >= sim.need_lit else (DANGER_CB if self.colorblind else DANGER)
        target = total_before + sim.score
        self.shown_score += (target - self.shown_score) * min(1, 10 * time.dt)
        if abs(self.shown_score - target) < .5:
            self.shown_score = target
        self.score.text = str(int(round(self.shown_score)))
        cap = sim.capacity
        for i, c in enumerate(self.cells):
            c.enabled = i < cap
            c.color = GOLD if i < p.carried else GHOST
        self.count.text = f"{p.carried}/{cap}"
        dcd, pcd = round(t["dash_cooldown_s"] * 60), round(t["pulse_cooldown_s"] * 60)
        self.dash.set(1 if p.charm > 0 else 1 - p.dash_cd / dcd, p.dash_ticks == 0, key_label(self.keys.get("dash", "shift")))
        self.pulse.set(1 - p.pulse_cd / pcd, p.carried >= t["pulse_cost"], key_label(self.keys.get("pulse", "f")))
        on = p.charm > 0
        self.charm_box.enabled = self.charm_txt.enabled = on
        self.charm_txt.text = f"Bùa Gió · {p.charm / 60:.0f}s" if on else ""
        if self.toast_left > 0:
            self.toast_left -= time.dt
            self._toast_alpha(min(1.0, self.toast_left * 3))
        else:
            self._toast_alpha(0)
        changed = False
        for c in self.cap_items:
            c[1] -= time.dt
        if any(c[1] <= 0 for c in self.cap_items):
            self.cap_items = [c for c in self.cap_items if c[1] > 0]
            changed = True
        if changed:
            self._render_captions()
        if self.flash.alpha > 0:
            self.flash.alpha = max(0, self.flash.alpha - time.dt * .8)


ONG_DANG = {
    1: "Đảo Bến là nơi thuyền đầu tiên cập bờ. Thắp lại năm ngọn đèn nhé cháu, Bóng Mực sợ ánh sáng ấm lắm.",
    2: "Đảo Cau có hai mỏm đất nối bằng cầu tre. Bục vàng sẽ hất cháu bay qua. Coi chừng Gió Lạc, nó mê đom đóm của cháu đấy!",
    3: "Đảo Chuông cao ba tầng. Theo dốc lên tầng giữa, nhờ bục nhảy lên tháp chuông. Nghe tiếng lá xào xạc là gió sắp nổi, đứng vững nhé!",
}


def wrap(s, width=58):
    return "\n".join(textwrap.wrap(s, width))


class Screens:
    """menu / intro / pause / settings / controls / result / dawn / name / board. Callbacks in cb."""

    NAMES = ("menu", "intro", "pause", "settings", "controls", "result", "dawn", "name", "board")

    def __init__(self, cb, settings):
        self.cb = cb
        self.settings = settings
        self.current = None
        self.primary = {}
        self.capturing = None
        self.groups = {"menu": self._menu(), "intro": self._intro(), "pause": self._pause(), "settings": self._settings(),
                       "controls": self._controls(), "result": self._result(), "dawn": self._dawn(), "name": self._name(),
                       "board": self._board()}
        self.show(None)

    def destroy_all(self):
        from ursina import destroy
        for g in self.groups.values():
            destroy(g)

    def _dim(self, alpha=.62):
        g = Entity(parent=camera.ui)
        ent(M_DIM, parent=g, model="quad", scale=(3, 1), color=A(.03, .04, .12, alpha))
        return g

    # ---------- menu ----------
    def _menu(self):
        g = Entity(parent=camera.ui)
        ent(M_DIM, parent=g, model="quad", texture="vertical_gradient", scale=(3, 1), color=A(.03, .04, .12, .6))
        lantern_icon(0, .3, g, 2.6, lay=M_ICON)
        txt("Đảo Đèn Lồng", 0, .19, 4.2, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        txt("Ba đêm, ba hòn đảo, và một cô bé đội nón lá giữ đèn.", 0, .1, 1.0, REG, SOFT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.primary["menu"] = button("Bắt đầu hành trình", 0, .01, .36, .075, lambda: self.cb["start"](), g)
        button("Bảng xếp hạng", 0, -.075, .36, .066, lambda: self.cb["board"](), g, primary=False)
        button("Cài đặt", 0, -.155, .36, .066, lambda: self.cb["settings"](), g, primary=False)
        button("Thoát", 0, -.235, .36, .066, lambda: self.cb["quit"](), g, primary=False)
        txt("Enter: bắt đầu", 0, -.44, 1.0, REG, SOFT, origin=(0, 0), parent=g, lay=M_TEXT)
        return g

    # ---------- intro ----------
    def _intro(self):
        g = self._dim(.55)
        rbox(0, 0, 1.1, .56, CARD, r=.03, parent=g, lay=M_CARD)
        self.in_kicker = txt("", 0, .21, 1.0, SEMI, GOLD, origin=(0, 0), parent=g, lay=M_TEXT)
        self.in_title = txt("", 0, .15, 2.6, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.in_quote = txt("", 0, .04, 1.0, REG, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.in_goal = txt("", 0, -.09, 1.0, SEMI, SOFT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.primary["intro"] = button("Bắt đầu Đêm", 0, -.19, .3, .07, lambda: self.cb["begin"](), g)
        return g

    def set_intro(self, night, name, lanterns, secs):
        self.in_kicker.text = f"ĐÊM {night}"
        self.in_title.text = name
        self.in_quote.text = wrap("Ông Đăng: " + ONG_DANG[night], 66)
        need = -(-lanterns * 3 // 5)
        self.in_goal.text = wrap(f"Giữ ít nhất {need}/{lanterns} ngọn đèn còn sáng tới bình minh "
                                 f"({secs // 60}:{secs % 60:02d}). Đèn hao dầu, nhớ châm thêm!", 66)

    # ---------- pause ----------
    def _pause(self):
        g = self._dim()
        rbox(0, 0, .5, .6, CARD, r=.03, parent=g, lay=M_CARD)
        txt("Tạm nghỉ", 0, .22, 2.2, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.primary["pause"] = button("Tiếp tục", 0, .12, .38, .068, lambda: self.cb["resume"](), g)
        button("Chơi lại Đêm", 0, .035, .38, .064, lambda: self.cb["retry"](), g, primary=False)
        button("Cài đặt", 0, -.05, .38, .064, lambda: self.cb["settings"](), g, primary=False)
        button("Về menu", 0, -.135, .38, .064, lambda: self.cb["menu"](), g, primary=False)
        return g

    # ---------- settings ----------
    def _settings(self):
        g = self._dim(.68)
        rbox(0, 0, .8, .86, CARD, r=.03, parent=g, lay=M_CARD)
        txt("Cài đặt", 0, .36, 2.0, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        txt("Âm lượng", -.35, .27, 1.0, SEMI, TXT, parent=g, lay=M_TEXT)
        self.vol = Slider(0, 1, default=self.settings["volume"], step=.05, dynamic=True, parent=g, position=(-.05, .27), scale=.6)
        txt("Độ nhạy chuột", -.35, .2, 1.0, SEMI, TXT, parent=g, lay=M_TEXT)
        self.sens = Slider(.2, 3, default=self.settings["mouse_sensitivity"], step=.1, dynamic=True, parent=g, position=(-.05, .2), scale=.6)
        self.vol_txt = txt("", .3, .27, 1.0, SEMI, GOLD, parent=g, lay=M_TEXT)
        self.sens_txt = txt("", .3, .2, 1.0, SEMI, GOLD, parent=g, lay=M_TEXT)
        for s in (self.vol, self.sens):
            layer(s, M_ICON)
            s.on_value_changed = self._changed
            for t in (getattr(s.knob, "text_entity", None), getattr(s, "label", None)):
                if t is not None:
                    t.enabled = False   # tiny built-in labels (< 18 px): shown in our own text instead
        self._slider_text()
        self.toggles = {}
        for i, (k, label) in enumerate((("colorblind", "Bảng màu dễ phân biệt"), ("reduce_motion", "Giảm chuyển động"),
                                        ("large_text", "Chữ lớn (×1.25)"))):
            self.toggles[k] = (button(" ", 0, .115 - i * .075, .64, .062, lambda k=k: self._toggle(k), g, primary=False), label)
            self._toggle_label(k)
        button("Phím điều khiển", 0, -.12, .64, .062, lambda: self.cb["controls"](), g, primary=False)
        txt("Giữ chuột phải và kéo để xoay góc nhìn.", 0, -.2, 1.0, REG, SOFT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.primary["settings"] = button("Xong", 0, -.3, .26, .068, lambda: self.cb["settings_done"](), g)
        return g

    def _toggle_label(self, k):
        b, label = self.toggles[k]
        on = self.settings.get(k, 0) >= .5
        set_button_text(b, f"{label}: {'BẬT' if on else 'TẮT'}")

    def _toggle(self, k):
        self.settings[k] = 0.0 if self.settings.get(k, 0) >= .5 else 1.0
        self._toggle_label(k)
        self.cb["settings_changed"](k)

    def _slider_text(self):
        self.vol_txt.text = f"{round(self.settings['volume'] * 100)}%"
        self.sens_txt.text = f"×{self.settings['mouse_sensitivity']:.1f}"

    def _changed(self):
        self.settings["volume"] = round(float(self.vol.value), 2)
        self.settings["mouse_sensitivity"] = round(float(self.sens.value), 2)
        self._slider_text()
        self.cb["settings_changed"](None)

    # ---------- controls (key rebinding) ----------
    def _controls(self):
        g = self._dim(.7)
        rbox(0, 0, .86, .92, CARD, r=.03, parent=g, lay=M_CARD)
        txt("Phím điều khiển", 0, .39, 2.0, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.key_btns = {}
        for i, (act, label) in enumerate(ACTIONS):
            y = .305 - i * .06
            txt(label, -.37, y, 1.0, SEMI, TXT, parent=g, lay=M_TEXT)
            self.key_btns[act] = button(" ", .22, y, .3, .05, lambda a=act: self._capture(a), g, primary=False)
        self.ctl_msg = txt("Bấm vào một phím để đổi, rồi nhấn phím mới.", 0, -.26, 1.0, REG, SOFT, origin=(0, 0), parent=g, lay=M_TEXT)
        button("Khôi phục mặc định", -.17, -.36, .34, .066, lambda: self.cb["keys_reset"](), g, primary=False)
        self.primary["controls"] = button("Xong", .19, -.36, .24, .066, lambda: self.cb["controls_done"](), g)
        self.refresh_keys()
        return g

    def refresh_keys(self, msg=None, warn=False):
        keys = self.settings["keys"]
        for act, b in self.key_btns.items():
            label = "..." if self.capturing == act else key_label(keys[act])
            set_button_text(b, label)
        if msg is not None:
            self.ctl_msg.text = msg
            self.ctl_msg.color = DANGER if warn else SOFT

    def _capture(self, act):
        self.capturing = act
        self.refresh_keys(f"Nhấn phím mới cho \"{dict(ACTIONS)[act]}\" (Esc để hủy).")

    # ---------- result / dawn ----------
    def _result(self):
        g = self._dim(.5)
        rbox(0, 0, .96, .56, CARD, r=.03, parent=g, lay=M_CARD)
        self.res_icon = lantern_icon(0, .2, g, 2.0, lay=M_ICON)
        self.res_title = txt("", 0, .12, 2.1, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.res_body = txt("", 0, .05, 1.0, REG, SOFT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.res_stats = txt("", 0, -.01, 1.0, SEMI, GOLD, origin=(0, 0), parent=g, lay=M_TEXT)
        self.res_main = button("Tiếp tục", -.27, -.17, .26, .066, lambda: self.cb["result_main"](), g)
        self.res_save = button("Lưu điểm", 0, -.17, .22, .066, lambda: self.cb["save_score"](), g, primary=False)
        self.primary["result"] = self.res_main
        button("Về menu", .26, -.17, .22, .066, lambda: self.cb["menu"](), g, primary=False)
        return g

    need = 0

    def set_result(self, won, reason, night, score, lit, total_l, flames, need=0):
        self.need = need
        self.res_icon.body.color = LIT if won else OFF
        self.res_title.text = f"Đêm {night}: đảo sáng tới bình minh!" if won else {"dawn": "Bình minh đến khi đảo còn tối...", "no_flames": "Ngọn lửa đã tắt..."}[reason]
        self.res_title.color = GOLD if won else TXT
        self.res_body.text = ("Mây giữ được đủ đèn cháy suốt đêm." if won else
                              f"Cần ít nhất {self.need} ngọn đèn còn sáng lúc bình minh." if reason == "dawn" else "Bóng Mực đã dập tắt lửa của Mây.")
        self.res_stats.text = f"Điểm đêm: {score}   ·   Đèn: {lit}/{total_l}   ·   Lửa: {flames}"
        set_button_text(self.res_main, ("Đón bình minh" if night == 3 else "Đêm tiếp theo") if won else "Chơi lại Đêm", primary=True)
        self.res_save.enabled = not won  # after a loss the run can be saved to the leaderboard

    def _dawn(self):
        g = Entity(parent=camera.ui)
        ent(M_DIM, parent=g, model="quad", texture="vertical_gradient", scale=(3, 1), color=A(1, .72, .4, .55))
        ent(M_ICON, parent=g, model="circle", position=(0, .25), scale=.16, color=C(1, .86, .5))
        txt("Bình Minh", 0, .12, 4.0, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.dawn_txt = txt("", 0, -.0, 1.1, SEMI, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.primary["dawn"] = button("Lưu điểm", -.15, -.16, .26, .07, lambda: self.cb["save_score"](), g)
        button("Về menu", .15, -.16, .24, .07, lambda: self.cb["menu"](), g, primary=False)
        return g

    def set_dawn(self, total, per_night):
        parts = "   ·   ".join(f"Đêm {n}: {s}" for n, s in sorted(per_night.items()))
        self.dawn_txt.text = f"Ba hòn đảo đã sáng trở lại.\nTổng điểm: {total}\n{parts}"

    # ---------- name entry / leaderboard ----------
    def _name(self):
        g = self._dim(.7)
        rbox(0, 0, .8, .5, CARD, r=.03, parent=g, lay=M_CARD)
        txt("Lưu điểm", 0, .18, 2.0, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.name_info = txt("", 0, .11, 1.0, SEMI, GOLD, origin=(0, 0), parent=g, lay=M_TEXT)
        self.name_field = InputField(parent=g, position=(0, .03), scale=(.5, .06), character_limit=12, max_lines=1)
        layer(self.name_field, M_ICON)
        self.name_msg = txt("Tên 3–12 ký tự: chữ (có dấu được), số hoặc _", 0, -.05, 1.0, REG, SOFT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.primary["name"] = button("Lưu", -.12, -.15, .22, .066, lambda: self.cb["name_save"](self.name_field.text.strip()), g)
        button("Bỏ qua", .12, -.15, .22, .066, lambda: self.cb["name_skip"](), g, primary=False)
        return g

    def set_name(self, score, nights_won, msg=None):
        self.name_info.text = f"Tổng điểm: {score}   ·   Đêm thắng: {nights_won}/3"
        self.name_msg.text = msg or "Tên 3–12 ký tự: chữ (có dấu được), số hoặc _"
        self.name_msg.color = DANGER if msg else SOFT
        if msg is None:
            self.name_field.text = ""
        self.name_field.active = True

    def _board(self):
        g = self._dim(.75)
        rbox(0, 0, 1.12, .9, CARD, r=.03, parent=g, lay=M_CARD)
        txt("Bảng xếp hạng", 0, .38, 2.0, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        cols = (-.5, -.43, -.07, .1, .24)
        for x, h in zip(cols, ("#", "Tên", "Điểm", "Đêm", "Ngày")):
            txt(h, x, .3, 1.0, SEMI, GOLD, parent=g, lay=M_TEXT)
        self.board_rows = [[txt("", x, .245 - i * .052, 1.0, REG, TXT, parent=g, lay=M_TEXT) for x in cols] for i in range(10)]
        self.board_empty = txt("Chưa có ai. Hãy là người đầu tiên!", 0, .1, 1.0, REG, SOFT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.primary["board"] = button("Về menu", 0, -.37, .26, .066, lambda: self.cb["board_back"](), g)
        return g

    def set_board(self, entries, highlight=None):
        self.board_empty.enabled = not entries
        for i, row in enumerate(self.board_rows):
            e = entries[i] if i < len(entries) else None
            vals = ("", "", "", "", "") if e is None else (str(i + 1), e["name"], str(e["score"]), f"{e['nights_won']}/3",
                                                         e["achieved_at"][:16].replace("T", " "))
            for t, v in zip(row, vals):
                t.text = v
                t.color = GOLD if highlight == i + 1 else TXT

    # ---------- common ----------
    def show(self, name):
        self.current = name
        for n, g in self.groups.items():
            g.enabled = n == name
        if name == "name":
            self.name_field.active = True

    def press_primary(self):
        b = self.primary.get(self.current)
        if b:
            b.on_click()
