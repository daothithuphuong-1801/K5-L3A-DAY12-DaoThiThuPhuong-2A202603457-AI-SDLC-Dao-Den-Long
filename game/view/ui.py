"""HUD + screens. Layout follows Ticket-02 (flames top-left, timer top-centre, lanterns+score top-right,
10-cell mote bar bottom-centre, dash/pulse cooldowns bottom-right, lantern prompt, off-screen arrow).
Look: rounded Mali font, night-navy glass panels, UI text #F5F1E6, gold #F2C14E, danger #FF5A5F."""
import math
from pathlib import Path

from panda3d.core import Filename
from ursina import Button, Entity, Quad, Slider, Text, camera, color, time

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
PANEL = A(.055, .078, .19, .78)       # #0E1430 glass
CARD = A(.07, .10, .23, .96)
SOFT = A(.96, .95, .90, .55)
GHOST = A(1, 1, 1, .14)
DARK = C(.10, .09, .14)

L_PANEL, L_ICON, L_FILL, L_TEXT = 10, 20, 25, 40
M_DIM, M_CARD, M_ICON, M_TEXT = 60, 65, 70, 80


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
    return layer(Text(s, parent=parent or camera.ui, position=(x, y), origin=origin, scale=size, font=font, color=col), lay)


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
               color=GOLD if primary else A(1, 1, 1, .08), highlight_color=C(1, .86, .45) if primary else A(1, 1, 1, .18),
               pressed_color=GOLD if primary else A(1, 1, 1, .22), text=label, text_size=.95)
    b.text_entity.font = BOLD if primary else SEMI
    b.text_entity.color = DARK if primary else TXT
    layer(b, lay)
    layer(b.text_entity, lay + 2)
    b.on_click = on_click
    return b


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


class Cooldown:
    """Round cooldown badge: key label + 16 dots filling clockwise."""

    def __init__(self, x, y, key, label, parent):
        self.bg = ent(L_ICON, parent=parent, model="circle", position=(x, y), scale=.062, color=PANEL)
        self.dots = [ent(L_FILL, parent=parent, model="circle", position=(x + .036 * math.sin(i / 16 * 6.283), y + .036 * math.cos(i / 16 * 6.283)),
                         scale=.007, color=GHOST) for i in range(16)]
        self.key = txt(key, x, y + .002, .75, BOLD, TXT, origin=(0, 0), parent=parent)
        self.lab = txt(label, x, y - .052, .55, SEMI, TXT, origin=(0, 0), parent=parent)

    def set(self, frac, usable):
        n = round(frac * 16)
        for i, d in enumerate(self.dots):
            d.color = GOLD if (i < n and usable) else GHOST
        self.key.color = TXT if usable and frac >= 1 else A(.96, .95, .90, .45)


class Hud:
    def __init__(self, tun):
        self.t = tun
        self.root = Entity(parent=camera.ui)
        P = self.root
        # top-left: flames + night label
        rbox(-.76, .45, .2, .062, parent=P, r=.031)
        self.flames = [flame_icon(-.815 + i * .05, .45, P, 1.1) for i in range(int(tun["flames"]))]
        self.night_lbl = txt("", -.86, .395, .65, SEMI, SOFT, parent=P)
        # top-centre: timer
        rbox(0, .45, .17, .068, parent=P, r=.034)
        self.timer = txt("", 0, .452, 1.55, BOLD, TXT, origin=(0, 0), parent=P)
        self.warn = ent(L_ICON, parent=P, position=(-.115, .452))
        ent(L_ICON, parent=self.warn, model=Quad(radius=0), rotation_z=45, scale=.026, color=DANGER_CB)
        txt("!", -.115, .451, .8, BOLD, DARK, origin=(0, 0), parent=P, lay=L_TEXT + 1).parent = self.warn
        self.colorblind = False
        # top-right: lanterns k/n + score
        rbox(.715, .45, .33, .062, parent=P, r=.031)
        lantern_icon(.575, .45, P, 1.0)
        self.lamps = txt("", .595, .451, .85, BOLD, TXT, parent=P)
        txt("Điểm", .765, .451, .6, REG, SOFT, parent=P)
        self.score = txt("0", .87, .452, 1.05, BOLD, GOLD, origin=(.5, 0), parent=P)
        self.shown_score = 0.0
        # bottom-centre: 10-cell firefly bar
        rbox(0, -.44, .66, .075, parent=P, r=.025)
        txt("Đom đóm", -.31, -.44, .62, SEMI, SOFT, parent=P)
        self.cells = [ent(L_FILL, parent=P, model=Quad(radius=.35, aspect=.6), position=(-.175 + i * .0195, -.44), scale=(.0145, .03), color=GHOST)
                      for i in range(int(tun["capacity_max"]))]
        self.count = txt("", .315, -.44, .8, BOLD, TXT, origin=(.5, 0), parent=P)
        # bottom-right: cooldowns + charm
        self.dash = Cooldown(.67, -.42, "Shift", "Lướt", P)
        self.pulse = Cooldown(.8, -.42, "F", "Tỏa Sáng", P)
        self.charm_box = rbox(.735, -.325, .24, .045, A(.78, .06, .18, .8), r=.022, parent=P, lay=L_PANEL, border=False)
        self.charm_txt = txt("", .735, -.325, .6, SEMI, TXT, origin=(0, 0), parent=P)
        # lantern prompt + off-screen arrow + toast + hit flash
        self.prompt_bg = rbox(0, -.3, .36, .05, PANEL, r=.025, parent=P, lay=L_PANEL)
        self.prompt = txt("", 0, -.3, .78, SEMI, TXT, origin=(0, 0), parent=P)
        self.arrow = ent(L_ICON, parent=P, model=Quad(radius=0), scale=(.028, .028), color=GOLD, rotation_z=45)
        self.arrow_tip = ent(L_ICON, parent=P, model="circle", scale=.02, color=GOLD)
        self.arrow_txt = txt("", 0, 0, .55, SEMI, GOLD, origin=(0, 0), parent=P)
        self.toast_bg = rbox(0, .34, .3, .055, PANEL, r=.027, parent=P, lay=L_PANEL + 2)
        self.toast = txt("", 0, .34, .78, SEMI, TXT, origin=(0, 0), parent=P, lay=L_TEXT + 2)
        self.toast_left = 0.0
        self.flash = ent(5, parent=P, model="quad", scale=(3, 1), color=A(1, .35, .37, 0))
        self._toast_alpha(0)

    def _toast_alpha(self, k):
        self.toast.alpha = k
        self.toast_bg.alpha = .78 * k
        if self.toast_bg.border:
            self.toast_bg.border.alpha = .35 * k

    def say(self, msg, secs=2.6):
        self.toast.text = msg
        w = self.toast.width * self.toast.scale_x + .06
        for e in (self.toast_bg, self.toast_bg.border):
            if e is not None:
                e.scale_x = w + (.004 if e is self.toast_bg.border else 0)
                e.model = Quad(radius=.5, aspect=e.scale_x / e.scale_y)
        self.toast_left = secs

    def hit(self):
        self.flash.color = A(1, .35, .37, .28)

    def set_prompt(self, text):
        on = bool(text)
        self.prompt.text = text or ""
        self.prompt_bg.enabled = on
        if self.prompt_bg.border:
            self.prompt_bg.border.enabled = on
        if on:
            w = self.prompt.width * self.prompt.scale_x + .05
            for e in (self.prompt_bg, self.prompt_bg.border):
                e.scale_x = w + (.004 if e is self.prompt_bg.border else 0)
                e.model = Quad(radius=.5, aspect=e.scale_x / e.scale_y)

    def set_arrow(self, sx, sy, dist):
        """sx, sy: direction on screen (unit) to an off-screen lantern, or None to hide."""
        on = sx is not None
        for e in (self.arrow, self.arrow_tip, self.arrow_txt):
            e.enabled = on
        if not on:
            return
        k = min(.78 / max(abs(sx), 1e-6), .40 / max(abs(sy), 1e-6))
        x, y = sx * k, sy * k
        self.arrow.position = (x, y)
        self.arrow.rotation_z = 45 - math.degrees(math.atan2(sy, sx)) + 45
        self.arrow_tip.position = (x + sx * .02, y + sy * .02)
        self.arrow_txt.position = (x - sx * .045, y - sy * .045)
        self.arrow_txt.text = f"{dist:.0f} m"

    def update(self, sim, clock, total_before):
        p, t = sim.player, self.t
        for i, f in enumerate(self.flames):
            on = i < p.flames
            for c in f.children:
                c.alpha = 1 if on else .18
            f.scale = 1 + (.06 * math.sin(clock * 5 + i) if on else 0)
        self.night_lbl.text = f"Đêm {sim.night} · {sim.map.name}"
        tl = max(0, math.ceil(sim.time_left_s))
        self.timer.text = f"{tl // 60:02d}:{tl % 60:02d}"
        danger = tl <= 30 and sim.state == "playing"
        self.timer.color = (DANGER_CB if self.colorblind else DANGER) if danger else TXT
        self.timer.alpha = (.35 + .65 * (math.sin(clock * 10) > 0)) if danger else 1
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
        self.dash.set(1 if p.charm > 0 else 1 - p.dash_cd / dcd, p.dash_ticks == 0)
        self.pulse.set(1 - p.pulse_cd / pcd, p.carried >= t["pulse_cost"])
        on = p.charm > 0
        self.charm_box.enabled = self.charm_txt.enabled = on
        self.charm_txt.text = f"Bùa Gió · {p.charm / 60:.0f}s" if on else ""
        if self.toast_left > 0:
            self.toast_left -= time.dt
            self._toast_alpha(min(1.0, self.toast_left * 3))
        else:
            self._toast_alpha(0)
        if self.flash.alpha > 0:
            self.flash.alpha = max(0, self.flash.alpha - time.dt * .8)


ONG_DANG = {
    1: "Đảo Bến là nơi thuyền đầu tiên cập bờ. Thắp lại năm ngọn đèn nhé cháu,\nBóng Mực sợ ánh sáng ấm lắm.",
    2: "Đảo Cau có hai mỏm đất nối bằng cầu tre. Bục vàng sẽ hất cháu bay qua.\nCoi chừng Gió Lạc, nó mê đom đóm của cháu đấy!",
    3: "Đảo Chuông cao ba tầng. Theo dốc lên tầng giữa, nhờ bục nhảy lên tháp chuông.\nNghe tiếng lá xào xạc là gió sắp nổi, đứng vững nhé!",
}


class Screens:
    """menu / intro / pause / settings / result / dawn. Callbacks in cb."""

    def __init__(self, cb, settings):
        self.cb = cb
        self.settings = settings
        self.current = None
        self.primary = {}
        self.menu = self._menu()
        self.intro = self._intro()
        self.pause = self._pause()
        self.settings_g = self._settings()
        self.result = self._result()
        self.dawn = self._dawn()
        self.show(None)

    def _dim(self, alpha=.6):
        g = Entity(parent=camera.ui)
        ent(M_DIM, parent=g, model="quad", scale=(3, 1), color=A(.03, .04, .12, alpha))
        return g

    def _menu(self):
        g = Entity(parent=camera.ui)
        ent(M_DIM, parent=g, model="quad", texture="vertical_gradient", scale=(3, 1), color=A(.03, .04, .12, .55))
        lantern_icon(0, .29, g, 2.6, lay=M_ICON)
        txt("Đảo Đèn Lồng", 0, .17, 4.2, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        txt("Ba đêm, ba hòn đảo, và một cô bé đội nón lá giữ đèn.", 0, .085, 1.0, REG, SOFT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.primary["menu"] = button("Bắt đầu hành trình", 0, -.03, .3, .072, lambda: self.cb["start"](), g)
        button("Cài đặt", 0, -.12, .3, .062, lambda: self.cb["settings"](), g, primary=False)
        button("Thoát", 0, -.2, .3, .062, lambda: self.cb["quit"](), g, primary=False)
        txt("Enter: bắt đầu", 0, -.45, .65, REG, SOFT, origin=(0, 0), parent=g, lay=M_TEXT)
        return g

    def _intro(self):
        g = self._dim(.55)
        rbox(0, 0, .9, .44, CARD, r=.03, parent=g, lay=M_CARD)
        self.in_kicker = txt("", 0, .16, .7, SEMI, GOLD, origin=(0, 0), parent=g, lay=M_TEXT)
        self.in_title = txt("", 0, .1, 2.6, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.in_quote = txt("", 0, .015, .8, REG, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.in_goal = txt("", 0, -.07, .7, SEMI, SOFT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.primary["intro"] = button("Bắt đầu Đêm", 0, -.15, .26, .066, lambda: self.cb["begin"](), g)
        return g

    def set_intro(self, night, name, lanterns, secs):
        self.in_kicker.text = f"ĐÊM {night}"
        self.in_title.text = name
        self.in_quote.text = "Ông Đăng: " + ONG_DANG[night]
        need = -(-lanterns * 3 // 5)
        self.in_goal.text = (f"Giữ ít nhất {need}/{lanterns} ngọn đèn còn sáng tới bình minh ({secs // 60}:{secs % 60:02d}). "
                             f"Đèn hao dầu, nhớ châm thêm!")

    def _pause(self):
        g = self._dim()
        rbox(0, 0, .44, .5, CARD, r=.03, parent=g, lay=M_CARD)
        txt("Tạm nghỉ", 0, .18, 2.2, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.primary["pause"] = button("Tiếp tục", 0, .085, .32, .062, lambda: self.cb["resume"](), g)
        button("Chơi lại Đêm", 0, .005, .32, .058, lambda: self.cb["retry"](), g, primary=False)
        button("Cài đặt", 0, -.075, .32, .058, lambda: self.cb["settings"](), g, primary=False)
        button("Về menu", 0, -.155, .32, .058, lambda: self.cb["menu"](), g, primary=False)
        return g

    def _settings(self):
        g = self._dim(.65)
        rbox(0, 0, .62, .44, CARD, r=.03, parent=g, lay=M_CARD)
        txt("Cài đặt", 0, .16, 2.0, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        txt("Âm lượng", -.25, .065, .8, SEMI, TXT, parent=g, lay=M_TEXT)
        self.vol = Slider(0, 1, default=self.settings["volume"], step=.05, dynamic=True, parent=g, position=(-.05, .065), scale=.55)
        txt("Độ nhạy chuột", -.25, -.015, .8, SEMI, TXT, parent=g, lay=M_TEXT)
        self.sens = Slider(.2, 3, default=self.settings["mouse_sensitivity"], step=.1, dynamic=True, parent=g, position=(-.05, -.015), scale=.55)
        for s in (self.vol, self.sens):
            layer(s, M_ICON)
            s.on_value_changed = self._changed
        self.cb_btn = button("", 0, -.085, .5, .05, self._toggle_cb, g, primary=False)
        self._cb_label()
        self.primary["settings"] = button("Xong", 0, -.16, .2, .06, lambda: self.cb["settings_done"](), g)
        return g

    def _cb_label(self):
        on = self.settings.get("colorblind", 0) >= .5
        self.cb_btn.text = f"Bảng màu dễ phân biệt: {'BẬT' if on else 'TẮT'}"
        self.cb_btn.text_entity.font = SEMI
        self.cb_btn.text_entity.color = TXT
        layer(self.cb_btn.text_entity, M_ICON + 2)

    def _toggle_cb(self):
        self.settings["colorblind"] = 0.0 if self.settings.get("colorblind", 0) >= .5 else 1.0
        self._cb_label()
        self.cb["settings_changed"]()

    def _changed(self):
        self.settings["volume"] = round(float(self.vol.value), 2)
        self.settings["mouse_sensitivity"] = round(float(self.sens.value), 2)
        self.cb["settings_changed"]()

    def _result(self):
        g = self._dim(.5)
        rbox(0, 0, .66, .46, CARD, r=.03, parent=g, lay=M_CARD)
        self.res_icon = lantern_icon(0, .16, g, 2.0, lay=M_ICON)
        self.res_title = txt("", 0, .085, 2.1, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.res_body = txt("", 0, .03, .78, REG, SOFT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.res_stats = txt("", 0, -.035, .95, SEMI, GOLD, origin=(0, 0), parent=g, lay=M_TEXT)
        self.res_main = button("Tiếp tục", -.12, -.135, .22, .062, lambda: self.cb["result_main"](), g)
        self.primary["result"] = self.res_main
        button("Về menu", .12, -.135, .2, .062, lambda: self.cb["menu"](), g, primary=False)
        return g

    need = 0

    def set_result(self, won, reason, night, score, lit, total_l, flames, need=0):
        self.need = need
        self.res_icon.body.color = LIT if won else OFF
        self.res_title.text = f"Đêm {night}: đảo sáng tới bình minh!" if won else {"dawn": "Bình minh đến khi đảo còn tối...", "no_flames": "Ngọn lửa đã tắt..."}[reason]
        self.res_title.color = GOLD if won else TXT
        self.res_body.text = ("Mây giữ được đủ đèn cháy suốt đêm." if won else
                              f"Cần ít nhất {self.need} ngọn đèn còn sáng lúc bình minh." if reason == "dawn" else "Bóng Mực đã dập tắt lửa của Mây.")
        self.res_stats.text = f"Điểm đêm: {score}    ·    Đèn: {lit}/{total_l}    ·    Lửa: {flames}"
        self.res_main.text = ("Đón bình minh" if night == 3 else "Đêm tiếp theo") if won else "Chơi lại Đêm"
        self.res_main.text_entity.font = BOLD
        self.res_main.text_entity.color = DARK
        layer(self.res_main.text_entity, M_ICON + 2)

    def _dawn(self):
        g = Entity(parent=camera.ui)
        ent(M_DIM, parent=g, model="quad", texture="vertical_gradient", scale=(3, 1), color=A(1, .72, .4, .55))
        ent(M_ICON, parent=g, model="circle", position=(0, .23), scale=.16, color=C(1, .86, .5))
        txt("Bình Minh", 0, .1, 4.0, BOLD, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.dawn_txt = txt("", 0, -.0, 1.0, SEMI, TXT, origin=(0, 0), parent=g, lay=M_TEXT)
        self.primary["dawn"] = button("Về menu", 0, -.14, .24, .066, lambda: self.cb["menu"](), g)
        return g

    def set_dawn(self, total, per_night):
        parts = "   ·   ".join(f"Đêm {n}: {s}" for n, s in sorted(per_night.items()))
        self.dawn_txt.text = f"Ba hòn đảo đã sáng trở lại.\nTổng điểm: {total}\n{parts}"

    def show(self, name):
        self.current = name
        for n, g in (("menu", self.menu), ("intro", self.intro), ("pause", self.pause), ("settings", self.settings_g),
                     ("result", self.result), ("dawn", self.dawn)):
            g.enabled = n == name

    def press_primary(self):
        b = self.primary.get(self.current)
        if b:
            b.on_click()
