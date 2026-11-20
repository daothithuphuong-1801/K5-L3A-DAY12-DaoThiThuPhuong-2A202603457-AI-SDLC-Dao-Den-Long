"""3D game (Ursina). Renders the deterministic sim from game.core; contains no game rules.

python3 -m game.app [--night N] [--seed N] [--scenario s.json]
Proof:  --screenshot out.png --frames 120 [--autoplay] [--ui menu|intro|play|pause|settings|result|dawn]
Bench:  --bench 20  (plays N seconds with scripted input, prints average FPS)

Night chain: menu -> intro (island + Ông Đăng) -> play -> result -> next night ... -> Bình Minh.
Camera: fixed 3/4 view following Mây; hold right mouse to orbit (sensitivity in settings).
"""
import argparse
import json
import math
import random
import sys
import time as _time
from pathlib import Path

if __package__ in (None, ""):  # allow `python game/app.py` / VS Code "Run Python File"
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from panda3d.core import loadPrcFileData

loadPrcFileData("", "framebuffer-multisample 1\nmultisamples 2\nsync-video 0")

from ursina import Entity, Ursina, Vec3, application, camera, color, destroy, held_keys, mouse, time, window  # noqa: E402

from game.core.sim import InputState, Sim  # noqa: E402
from game.core import leaderboard  # noqa: E402
from game.view import audio, gfx, ui, world  # noqa: E402
from game.view.ui import Hud, Screens  # noqa: E402

STEP = 1 / 60
CAM_DIST, CAM_H = 19.5, 15.5
CAM_PITCH = math.degrees(math.atan2(CAM_H, CAM_DIST))
MENU_ORBIT = (82.0, 46.0)


def ease(cur, target, rate):
    return cur + (target - cur) * min(1.0, rate * time.dt)


def ease_angle(cur, target, rate):
    d = (target - cur + 180) % 360 - 180
    return cur + d * min(1.0, rate * time.dt)


class Game(Entity):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.scenario = None
        if args.scenario:
            with open(args.scenario, encoding="utf-8") as f:
                self.scenario = json.load(f)
        window.color = world.SKY
        camera.fov = 64
        camera.clip_plane_far = 450
        camera.ui_display_region.set_clear_depth_active(True)
        self.settings = audio.load_settings()
        self.sfx = audio.Sfx(self.settings, enabled=not (args.screenshot or args.bench or args.bench_scene))
        self.lb_path = args.leaderboard_file or leaderboard.LEADERBOARD_PATH
        self.run_seed = None
        self.frame, self.clock = 0, 0.0
        self.scenery, self.dyn, self.moon = [], [], None
        self.scores = {}
        self.cam_yaw = 0.0
        self.prev_state = "menu"
        self.night = args.night
        self.sim = Sim(1, night=self.night)
        self.state = "menu"
        self.build_ui()
        self.bench = None
        start = "bench" if args.bench_scene else (args.ui or ("play" if (args.autoplay or args.bench) else "menu"))
        self.load_night(self.night, start, seed=args.seed)
        if start == "result":
            self.screens.set_result(True, "dawn_survived", self.night, 512, 4, 5, 3, 3)
        if start == "dawn":
            self.screens.set_dawn(1536, {1: 512, 2: 498, 3: 526})
        if start == "board":
            self.screens.set_board(leaderboard.load(self.lb_path), 1)
        if start == "name":
            self.screens.set_name(1536, 3)
        self.sfx.start_music()

    # ---------- UI (rebuilt when "Chữ lớn" changes) ----------
    def build_ui(self):
        ui.FS = 1.25 if self.settings.get("large_text", 0) >= .5 else 1.0
        self.hud = Hud(self.sim.t)
        self.apply_prefs()
        self.screens = Screens({
            "start": self.start_run, "settings": self.open_settings, "quit": application.quit,
            "begin": self.begin, "resume": lambda: self.set_state("play"), "retry": lambda: self.load_night(self.night, "play"),
            "menu": lambda: self.load_night(1, "menu"), "settings_done": self.close_settings,
            "settings_changed": self.settings_changed, "result_main": self.result_main,
            "controls": lambda: self.set_state("controls"), "controls_done": self.close_controls, "keys_reset": self.reset_keys,
            "board": self.open_board, "board_back": lambda: self.set_state("menu"),
            "save_score": self.open_name, "name_save": self.save_name, "name_skip": lambda: self.load_night(1, "menu")},
            self.settings)

    def rebuild_ui(self):
        destroy(self.hud.root)
        self.screens.destroy_all()
        self.build_ui()
        self.screens.set_intro(self.night, self.sim.map.name, len(self.sim.lanterns), round(self.sim.total_ticks / 60))
        self.set_state(self.state)

    def apply_prefs(self):
        self.hud.colorblind = self.settings.get("colorblind", 0) >= .5
        self.hud.reduce_motion = self.settings.get("reduce_motion", 0) >= .5
        self.hud.keys = self.settings["keys"]

    def start_run(self):
        self.scores = {}
        self.run_seed = random.randrange(1 << 30)
        self.load_night(1, "intro", seed=self.run_seed)

    # ---------- leaderboard ----------
    def open_board(self, highlight=None):
        self.screens.set_board(leaderboard.load(self.lb_path), highlight)
        self.set_state("board")

    def open_name(self):
        self.screens.set_name(sum(self.scores.values()), len(self.scores))
        self.set_state("name")

    def save_name(self, name):
        try:
            _, rank = leaderboard.add(name, sum(self.scores.values()), len(self.scores),
                                      self.run_seed if self.run_seed is not None else self.sim_seed, self.lb_path)
        except ValueError as e:
            self.screens.set_name(sum(self.scores.values()), len(self.scores), msg=str(e))
            return
        self.scores = {}
        self.load_night(1, "menu")
        self.open_board(highlight=rank)

    # ---------- nights & states ----------
    def load_night(self, n, state, seed=None):
        for e in self.scenery + self.dyn:
            destroy(e)
        if self.moon is not None:
            destroy(self.moon)
        self.night = n
        if n == 1 and state == "menu":
            self.scores = {}
        if self.args.bench_scene:
            self.sim = Sim.bench_scene(seed if seed is not None else 42)
        else:
            if seed is None and self.run_seed is not None:
                seed = self.run_seed + n - 1      # one run seed -> nights seed, seed + 1, seed + 2
            self.sim_seed = seed if seed is not None else random.randrange(1 << 30)
            self.sim = Sim(self.sim_seed, night=n, scenario=self.scenario if n == self.args.night else None)
        island, extra = world.build_world(self.sim.map)
        self.scenery = [island] + extra
        self.moon = world.setup_lighting(island)
        self.dyn = []
        self.acc = 0.0
        self.mote_e, self.shade_e, self.drift_e, self.charm_e = {}, {}, {}, {}
        self.may = self._keep(world.make_may())
        self.face = 180.0
        self.lan = {}
        for l in self.sim.lanterns:
            v = world.make_lantern(l.id, l.x, l.y, l.z, self.sim.t["safe_radius"])
            self._keep(v["root"])
            v["k"] = 1.0 if l.lit else 0.0
            self.lan[l.id] = v
        for i in range(8):
            world.set_lamp(i, 0, 0, 0, 0)
        self.leaves = []
        self.last_sec = None
        self.wind_was = False
        self.low_fuel = set()
        self.shade_cue = None   # (shade id, seconds left) -> edge arrow after a shade spawns
        self._capture_prev()
        self.cam_yaw = 0.0
        p = self.sim.player
        camera.position = self._cam_target(p.x, p.y, p.z)
        camera.rotation = (CAM_PITCH, self.cam_yaw, 0)
        self.screens.set_intro(n, self.sim.map.name, len(self.sim.lanterns), round(self.sim.time_left_s))
        self.set_state(state)
        self._quiet()

    def _quiet(self):
        """Plain visual entities have no update(): let Ursina's per-frame loop skip them (11k+ entities)."""
        from ursina import scene
        # leftovers of mesh baking (disabled, no model) are never drawn: drop them from Ursina's per-frame list
        scene.entities[:] = [e for e in scene.entities if not (type(e) is Entity and not e.enabled and e.model is None)]
        for e in scene.entities:
            if type(e) is Entity and not e.ignore:
                e.ignore = True

    def set_state(self, s):
        self.state = s
        self.screens.show(s if s in Screens.NAMES else None)
        self.hud.root.enabled = s in ("play", "pause", "result", "intro", "settings", "controls") and self.prev_state != "menu" or s in ("play", "bench")

    def begin(self):
        self.set_state("play")
        self.hud.say(f"Đêm {self.night} · {self.sim.map.name}: giữ {self.sim.need_lit} đèn sáng tới bình minh!", 3)

    def open_settings(self):
        if self.state != "controls":
            self.prev_state = self.state
        self.set_state("settings")

    def close_controls(self):
        self.screens.capturing = None
        audio.save_settings(self.settings)
        self.set_state("settings")

    def reset_keys(self):
        self.settings["keys"] = dict(audio.DEFAULT_KEYS)
        self.screens.capturing = None
        self.apply_prefs()
        self.screens.refresh_keys("Đã khôi phục phím mặc định.")
        audio.save_settings(self.settings)

    def close_settings(self):
        audio.save_settings(self.settings)
        self.set_state(self.prev_state if self.prev_state != "settings" else "menu")

    def settings_changed(self, key=None):
        self.sfx.apply_volume()
        self.apply_prefs()
        audio.save_settings(self.settings)
        if key == "large_text":
            self.rebuild_ui()

    def result_main(self):
        if self.sim.state == "won":
            if self.night == 3:
                self.screens.set_dawn(sum(self.scores.values()), self.scores)
                self.set_state("dawn")
                self.sfx.play("win")
            else:
                self.load_night(self.night + 1, "intro")
        else:
            self.load_night(self.night, "play")

    def _keep(self, e):
        self.dyn.append(e)
        return e

    # ---------- input ----------
    def current_input(self):
        if self.args.autoplay or self.args.bench:
            ph = (self.frame // 120) % 4
            mv = ((0, 1), (1, 0), (0, -1), (-1, 0))[ph]
            return InputState(move=mv, cam_yaw_deg=self.cam_yaw, interact=self.frame % 30 == 0,
                              dash=self.frame % 97 == 0, pulse=self.frame % 211 == 0)
        k, b = held_keys, self.settings["keys"]
        mx = k[b["right"]] - k[b["left"]]
        mz = k[b["up"]] - k[b["down"]]
        return InputState(move=(float(mx), float(mz)), cam_yaw_deg=self.cam_yaw, jump=bool(k[b["jump"]]),
                          interact=bool(k[b["interact"]]), pulse=bool(k[b["pulse"]]), dash=bool(k[b["dash"]]))

    def input(self, key):
        if self.screens.capturing:
            self._capture_key(key)
            return
        if key == self.settings["keys"]["pause"] or key == "escape":
            if self.state == "controls":
                self.close_controls()
                return
            if self.state in ("board", "name"):
                self.set_state("menu") if self.state == "board" else self.load_night(1, "menu")
                return
            if self.state == "play":
                self.set_state("pause")
            elif self.state == "pause":
                self.set_state("play")
            elif self.state == "settings":
                self.close_settings()
        elif key in ("enter", "return"):
            self.screens.press_primary()
        elif key == "r" and self.state == "play" and "r" not in self.settings["keys"].values():
            self.load_night(self.night, "play")

    def _capture_key(self, key):
        """Key rebinding: refuse duplicates and tell the player which action already uses the key."""
        act = self.screens.capturing
        if key.endswith(" up") or key.startswith("mouse") or key.startswith("scroll") or key in ("left shift", "right shift",
                                                                                                   "left control", "right control"):
            return
        if key == "escape" and act != "pause":
            self.screens.capturing = None
            self.screens.refresh_keys("Đã hủy.")
            return
        other = audio.key_conflict(self.settings["keys"], act, key)
        if other:
            name = dict(ui.ACTIONS)[other]
            self.screens.capturing = None
            self.screens.refresh_keys(f"Phím {ui.key_label(key)} đang dùng cho \"{name}\". Hãy chọn phím khác.", warn=True)
            return
        self.settings["keys"][act] = key
        self.screens.capturing = None
        self.apply_prefs()
        audio.save_settings(self.settings)
        self.screens.refresh_keys(f"Đã đặt {dict(ui.ACTIONS)[act]} = {ui.key_label(key)}.")

    # ---------- loop ----------
    def _capture_prev(self):
        p = self.sim.player
        self.prev_p = (p.x, p.y, p.z)
        self.prev_s = {s.id: (s.x, s.y, s.z) for s in self.sim.shades}
        self.prev_d = {d.id: (d.x, d.y, d.z) for d in self.sim.drifters}

    def _cam_target(self, x, y, z):
        a = math.radians(self.cam_yaw)
        return (x - CAM_DIST * math.sin(a), CAM_H + y * .8, z - CAM_DIST * math.cos(a))

    def update(self):
        self.frame += 1
        if self.frame % 30 == 0:
            self._quiet()
        dt = STEP if self.args.screenshot else time.dt
        self.clock += dt
        inp = InputState()
        if self.state == "bench":
            self._bench_scene_tick()
            return
        if self.state == "play":
            if held_keys["right mouse"]:
                self.cam_yaw += mouse.velocity[0] * 220 * self.settings["mouse_sensitivity"]
            self.acc = min(self.acc + dt, 0.25)
            inp = self.current_input()
            while self.acc >= STEP and self.sim.state == "playing":
                self.acc -= STEP
                self._capture_prev()
                for ev in self.sim.step(inp):
                    self.on_event(ev)
        alpha = self.acc / STEP if self.state == "play" else 1.0
        self.sync(alpha, inp)
        self._bench_tick()
        if self.args.screenshot and self.frame == self.args.frames:
            from panda3d.core import Filename
            application.base.win.saveScreenshot(Filename.fromOsSpecific(self.args.screenshot))
            application.quit()

    # ---------- Ticket-04 benchmark scene ----------
    def _bench_scene_tick(self):
        """Fixed 60 Hz sim (no input), camera orbit r=30 at y=15 around (0,0,0), CCW seen from above, 15 s per lap,
        3 s warm-up, then `duration` seconds measured; writes bench.json and quits with code 0."""
        now = _time.perf_counter()
        b = self.bench
        if b is None:
            from game.core.sysinfo import process_start_time
            b = self.bench = {"t0": now, "last": now, "dts": [], "peak": 0.0,
                              "load_ms": round((_time.time() - process_start_time()) * 1000)}
        dt_ms = (now - b["last"]) * 1000
        b["last"] = now
        el = now - b["t0"]
        self.acc = min(self.acc + (now - b.get("prev_frame", now)), .25)
        b["prev_frame"] = now
        while self.acc >= STEP:
            self.acc -= STEP
            self._capture_prev()
            self.sim.step(InputState())
        a = 2 * math.pi * el / 15.0  # angle from +X, counter-clockwise seen from above (x = r cos a, z = r sin a)
        camera.position = (30 * math.cos(a), 15, 30 * math.sin(a))
        camera.look_at((0, 0, 0))
        self.sync(self.acc / STEP, InputState(), camera_free=True)
        warm = 3.0
        if el >= warm and b["dts"] is not None:
            if b.get("measuring"):
                b["dts"].append(dt_ms)
                from game.core.sysinfo import rss_mb
                m = rss_mb()
                if m is not None:
                    b["peak"] = max(b["peak"], m)
            b["measuring"] = True
            if el >= warm + self.args.duration:
                self._write_bench(b)

    def _write_bench(self, b):
        import platform
        dts = b["dts"]
        n = len(dts)
        k = max(1, math.ceil(0.01 * n))
        worst = sorted(dts, reverse=True)[:k]
        p95 = sorted(dts)[min(n - 1, max(0, math.ceil(0.95 * n) - 1))]
        try:
            gsg = application.base.win.gsg
            gl = f"{gsg.getDriverVendor()} {gsg.getDriverRenderer()} (OpenGL {gsg.getDriverVersion()})"
        except Exception:  # noqa: BLE001
            gl = "OpenGL"
        import panda3d
        import ursina
        out = {
            "contract_version": "1.3",
            "avg_fps": round(1000 * n / sum(dts), 1),
            "p1_low_fps": round(1000 / (sum(worst) / k), 1),
            "frame_ms_p95": round(p95, 2),
            "frames": n,
            "load_ms": b["load_ms"],
            "peak_mem_mb": round(b["peak"], 1),
            "vsync_off": True,
            "renderer": f"Ursina {getattr(ursina, '__version__', '7')} / Panda3D {panda3d.__version__}, {gl}",
            "os": f"{platform.platform()} ({platform.processor() or platform.machine()})",
            "window": [int(window.size[0]), int(window.size[1])],
            "seed": self.args.seed if self.args.seed is not None else 42,
            "duration_s": self.args.duration,
        }
        with open(self.args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(json.dumps(out, ensure_ascii=False), flush=True)
        b["dts"] = None
        application.quit()

    def _bench_tick(self):
        if not self.args.bench:
            return
        now = _time.perf_counter()
        if self.bench is None:
            self.bench = {"start": None, "frames": 0, "warm": now + 2.0}
        b = self.bench
        if now < b["warm"]:
            return
        if b["start"] is None:
            b["start"] = now
        b["frames"] += 1
        if now - b["start"] >= self.args.bench:
            fps = b["frames"] / (now - b["start"])
            msg = f"bench night={self.night} size={tuple(window.size)} frames={b['frames']} seconds={now - b['start']:.1f} avg_fps={fps:.1f}"
            print(msg, flush=True)
            if self.args.bench_out:
                with open(self.args.bench_out, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
            application.quit()

    def on_event(self, ev):
        n, d = ev["name"], ev["data"]
        p = self.sim.player
        play = self.sfx.play
        if n == "mote_picked":
            play("pickup")
            self.may.halo.scale = 2.6
        elif n == "deposit":
            self.hud.say(f"Nạp {d['amount']} đom đóm · Đèn {d['lantern_id'][1:]}: {d['deposited']}/{self.sim.t['lantern_cost']}", 1.6)
        elif n == "lantern_lit":
            play("lantern")
            self.hud.say(f"Đèn {d['lantern_id'][1:]} " + ("đã được thắp lại!" if d["relight"] else "đã sáng!"))
        elif n == "refuel":
            play("charm")
            self.hud.say(f"Châm {d['amount']} đom đóm · Đèn {d['lantern_id'][1:]}: dầu {d['fuel']:.0f}", 1.6)
        elif n == "lantern_out":
            play("lose")
            self.hud.caption(f"Đèn {d['lantern_id'][1:]} đã cạn dầu và tắt!", 3, key="out" + d["lantern_id"])
        elif n == "fuel_drain":
            self.hud.say(f"Bóng Mực đang hút dầu Đèn {d['lantern_id'][1:]}!", 1.4)
        elif n == "player_hit":
            play("hit")
            self.hud.hit()
            if not self.hud.reduce_motion:
                camera.shake(duration=.25, magnitude=.4)
            self.hud.say("Mây rơi khỏi đảo!" if d["by"] == "fall" else
                         (f"Bóng Mực chạm vào Mây! Rơi {d['dropped']} đom đóm" if d["dropped"] else "Bóng Mực chạm vào Mây!"))
        elif n == "shade_spawned":
            play("shade")
            self.hud.caption("Bóng Mực xuất hiện!", 3, key="shade")
            self.shade_cue = (d["id"], 3.0)
        elif n == "dash":
            play("dash")
        elif n == "charm_picked":
            play("charm")
            self.hud.say("Bùa Gió! Chạy nhanh hơn, Lướt không cần hồi.", 2.2)
        elif n == "drifter_steal":
            play("steal")
            self.hud.say(f"Gió Lạc cướp mất {d['amount']} đom đóm! Tỏa Sáng để đòi lại.", 2.4)
        elif n == "drifter_drop":
            self.hud.say(f"Gió Lạc đánh rơi {d['amount']} đom đóm!", 1.8)
        elif n == "pulse":
            play("pulse")
            ring = gfx.U(model=gfx.ring_mesh(1.0, .25, 64), position=(p.x, p.y + .15, p.z), color=color.rgba(1, .85, .5, .9))
            gfx.additive(ring)
            ring.animate_scale(self.sim.t["pulse_radius"], duration=.3)
            ring.fade_out(duration=.45)
            destroy(ring, delay=.5)
        elif n == "game_over":
            won = d["result"] == "won"
            if won:
                self.scores[self.night] = self.sim.score
            play("win" if won else "lose")
            lit = sum(l.lit for l in self.sim.lanterns)
            self.screens.set_result(won, d["reason"], self.night, self.sim.score, lit, len(self.sim.lanterns), p.flames, self.sim.need_lit)
            self.set_state("result")

    def _jump_sound(self, inp):
        if inp.jump and not getattr(self, "_jump_prev", False) and self.sim.player.vy > 6:
            self.sfx.play("jump")
        self._jump_prev = inp.jump

    def sync(self, alpha, inp, camera_free=False):
        s, p = self.sim, self.sim.player
        self._jump_sound(inp)

        def lerp3(a, b):
            return tuple(a[i] + (b[i] - a[i]) * alpha for i in range(3))

        px, py, pz = lerp3(self.prev_p, (p.x, p.y, p.z))
        m = self.may
        m.position = (px, py, pz)
        m.visible = p.respawn_wait == 0 and (p.invuln == 0 or (p.invuln // 6) % 2 == 0)
        moving = inp.move != (0.0, 0.0) and s.state == "playing"
        self.face = ease_angle(self.face, math.degrees(math.atan2(p.fx, p.fz)), 14) if moving or p.dash_ticks else self.face
        m.rotation_y = self.face
        m.body.y = ease(m.body.y, abs(math.sin(self.clock * 12)) * .1 if moving and p.grounded else 0, 20)
        m.body.rotation_x = ease(m.body.rotation_x, 14 if p.dash_ticks else (7 if moving else 0), 8)
        m.pivot.rotation_x = math.sin(self.clock * (9 if moving else 3)) * (16 if moving else 5)
        m.halo.scale = ease(m.halo.scale_x, 1.5 + .08 * math.sin(self.clock * 4), 6)
        world.set_lamp(7, px, py, pz, .32 + .03 * math.sin(self.clock * 6), small=True)

        if camera_free:
            pass
        elif self.state == "menu":
            a = self.clock * .05
            cx = 35.0 if self.night == 2 else 0.0
            camera.position = (cx + MENU_ORBIT[0] * math.sin(a), MENU_ORBIT[1], -MENU_ORBIT[0] * math.cos(a))
            camera.look_at((cx, -6, 0))
        else:
            tx, ty, tz = self._cam_target(px, py, pz)
            cx, cy, cz = camera.position
            camera.position = (ease(cx, tx, 7), ease(cy, ty, 5), ease(cz, tz, 7))
            camera.rotation = (CAM_PITCH, self.cam_yaw, 0)

        alive = {mo.id for mo in s.motes}
        for mid in list(self.mote_e):
            if mid not in alive:
                destroy(self.mote_e.pop(mid))
        for mo in s.motes:
            e = self.mote_e.get(mo.id)
            if e is None:
                e = self.mote_e[mo.id] = self._keep(world.make_mote(mo.kind == "dropped"))
            ph = int(mo.id[1:]) * 1.7
            # raw Panda calls (Ursina 7 is Y-up like Panda): much cheaper than Ursina setters with 100+ motes
            e.setPos(mo.x + .15 * math.sin(self.clock * .9 + ph), mo.y + .9 + .25 * math.sin(self.clock * 2 + ph), mo.z)
            if mo.ttl is not None:
                e.visible = not (mo.ttl < 120 and int(self.clock * 8) % 2)

        alive = {sh.id for sh in s.shades}
        for sid in list(self.shade_e):
            if sid not in alive:
                destroy(self.shade_e.pop(sid))
        for sh in s.shades:
            e = self.shade_e.get(sh.id) or self.shade_e.setdefault(sh.id, self._keep(world.make_shade()))
            sx, sy, sz = lerp3(self.prev_s.get(sh.id, (sh.x, sh.y, sh.z)), (sh.x, sh.y, sh.z))
            ph = sh.num % 97
            wob = math.sin(self.clock * 3 + ph)
            rise = min(1.0, 1 - sh.timer / 30) if sh.state == "spawning" else 1.0
            e.setPos(sx, sy - 1.6 * (1 - rise) + .15 * wob, sz)
            e.yaw = ease_angle(getattr(e, "yaw", 0.0), math.degrees(math.atan2(px - sx, pz - sz)), 6)
            e.setH(e.yaw * Entity.rotation_directions[1])
            stunned = sh.state == "stunned"
            cb = self.hud.colorblind
            key = (sh.state, cb)
            if e.state != key:  # colours only change on state / palette change (cheap with 200 shades)
                e.state = key
                e.eyes.color = world.RIM_CB if cb else color.rgb(.85, .75, 1)
                rc = world.RIM_CB if cb else world.RIM
                e.rim.color = color.rgba(rc[0], rc[1], rc[2], .2 if stunned else .55)
                e.body.color = world.STUN if stunned else world.SHADE
            e.body.setScale(1, 1 + (.1 * math.sin(self.clock * 22) if stunned else .25 * abs(math.sin(self.clock * 6)) if sh.state == "drain" else .04 * wob), 1)

        alive = {d.id for d in s.drifters if d.state != "removed"}
        for did in list(self.drift_e):
            if did not in alive:
                e = self.drift_e.pop(did)
                e.animate_scale(0, duration=.3)
                destroy(e, delay=.35)
        for d in s.drifters:
            if d.state == "removed":
                continue
            e = self.drift_e.get(d.id) or self.drift_e.setdefault(d.id, self._keep(world.make_drifter()))
            dx, dy, dz = lerp3(self.prev_d.get(d.id, (d.x, d.y, d.z)), (d.x, d.y, d.z))
            e.position = (dx, dy, dz)
            pdx, pdy, pdz = self.prev_d.get(d.id, (d.x, d.y, d.z))
            if abs(d.x - pdx) + abs(d.z - pdz) > 1e-6:
                e.rotation_y = ease_angle(e.rotation_y, math.degrees(math.atan2(d.x - pdx, d.z - pdz)), 8)
            for i, sg in enumerate(e.segs):
                sg.position = (.25 * math.sin(self.clock * 7 - i * .8), .12 * math.sin(self.clock * 5 - i), -.42 * i)
                sg.rotation_z = 25 * math.sin(self.clock * 7 - i * .8)

        for c in s.charms:
            e = self.charm_e.get(c.id) or self.charm_e.setdefault(c.id, self._keep(world.make_charm()))
            e.position = (c.x, c.y + 1.1 + .15 * math.sin(self.clock * 2), c.z)
            e.rotation_y = self.clock * 90
            e.visible = c.available

        cost = s.t["lantern_cost"]
        lit = 0
        prompt = None
        nearest = None
        for i, l in enumerate(s.lanterns):
            v = self.lan[l.id]
            lit += l.lit
            low = l.lit and l.fuel_u < s.low_u
            blink = 1.0 if not low else (.35 if int(self.clock * 2) % 2 else 1.0)  # 1 Hz slow blink when fuel < 30
            v["k"] = ease(v["k"], (1.0 if l.lit else 0.0) * blink, 6 if low else 2.5)
            k = v["k"]
            v["paper"].scale_y = 1.15 if l.lit else 1.15 * .8          # out: squashed 20 %
            for tr in v["tears"]:
                tr.visible = not l.lit                                  # out: torn paper
            v["bar"].enabled = l.lit
            if l.lit:
                v["fill"].scale_x = max(.001, 1.5 * l.fuel_u / s.fuel_max_u)
                v["fill"].color = (world.LIT if not low else color.rgb(1, .35, .3)) if blink > .5 else color.rgba(1, 1, 1, .15)
            v["lamp"].visible = v["core"].visible = k > .05
            v["lamp"].color = color.rgba(world.LIT[0], world.LIT[1], world.LIT[2], k)
            v["paper"].color = world.OFF
            v["halo"].color = color.rgba(1, .70, .28, .75 * k)
            v["halo"].scale = 5 * (1 + .05 * math.sin(self.clock * 2.5 + i))
            v["ring"].color = color.rgba(1, .7, .28, .45 * k)
            need_c = s.t["relight_cost"] if l.ever_lit else cost
            v["tag"].text = f"Đèn {l.id[1:]} · dầu {l.fuel_u // 60}" if l.lit else f"Đèn {l.id[1:]} · {l.deposited}/{need_c}"
            v["tag"].color = color.rgb(1, .8, .45) if l.lit else world.H("#F5F1E6")
            if i < 7:
                world.set_lamp(i, l.x + 1.05, l.y, l.z, .85 * k)
            dd = math.hypot(p.x - l.x, p.z - l.z)
            if dd <= s.t["interact_radius"] and abs(p.y - l.y) <= 1.5:
                if not l.lit:
                    prompt = (f"E — Thắp lại ({l.deposited}/{need_c})" if l.ever_lit else f"E — Nạp ánh sáng ({l.deposited}/{cost})")
                elif l.fuel_u < s.fuel_max_u:
                    prompt = f"E — Châm dầu ({l.fuel_u // 60}/100)"
            if not l.lit or l.fuel_u < s.low_u:
                if nearest is None or dd < nearest[0]:
                    nearest = (dd, l)
        world.set_ambience(lit / len(s.lanterns) if self.state != "menu" else .4)
        self.hud.set_prompt(prompt if self.state == "play" else None)
        self._arrow(nearest)
        self._shade_cue_arrow()
        self._wind(px, py, pz)
        tl = math.ceil(s.time_left_s)
        if self.state == "play" and tl <= 10 and tl != self.last_sec and s.state == "playing":
            self.sfx.play("tick")
            self.hud.caption(f"Còn {tl} giây tới bình minh!", 1.1, key="countdown")
        self.last_sec = tl
        for l in s.lanterns:  # caption when a lantern drops below 30 fuel
            low = l.lit and l.fuel_u < s.low_u
            if low and l.id not in self.low_fuel and self.state == "play":
                self.hud.caption(f"Đèn {l.id[1:]} sắp cạn dầu (dưới 30)!", 3, key="low" + l.id)
            (self.low_fuel.add if low else self.low_fuel.discard)(l.id)
        self.hud.update(s, self.clock, sum(v for n, v in self.scores.items() if n != self.night))

    def _arrow(self, nearest):
        if nearest is None or self.state != "play":
            self.hud.set_arrow(None, None, 0)
            return
        dist, l = nearest
        from panda3d.core import Point3
        rel = camera.getRelativePoint(application.base.render, Point3(l.x, l.z, l.y + 3))
        rx, fwd, up = rel.x, rel.y, rel.z
        on_screen = False
        if fwd > 0:
            sp = self.lan[l.id]["root"].screen_position
            on_screen = abs(sp[0]) < .85 and abs(sp[1]) < .46
        if on_screen:
            self.hud.set_arrow(None, None, 0)
            return
        n = math.hypot(rx, up) or 1
        self.hud.set_arrow(rx / n, up / n, dist)

    def _screen_dir(self, x, y, z, entity=None):
        """Unit screen direction to a world point, or None when it is on screen."""
        from panda3d.core import Point3
        rel = camera.getRelativePoint(application.base.render, Point3(x, y, z))
        if rel.y > 0 and entity is not None:
            sp = entity.screen_position
            if abs(sp[0]) < .85 and abs(sp[1]) < .46:
                return None
        n = math.hypot(rel.x, rel.z) or 1
        return rel.x / n, rel.z / n

    def _shade_cue_arrow(self):
        cue = self.shade_cue
        if cue is None or self.state != "play":
            self.hud.set_shade_arrow(None, None)
            return
        sid, left = cue
        left -= time.dt
        e = self.shade_e.get(sid)
        sh = next((x for x in self.sim.shades if x.id == sid), None)
        if left <= 0 or sh is None or e is None:
            self.shade_cue = None
            self.hud.set_shade_arrow(None, None)
            return
        self.shade_cue = (sid, left)
        d = self._screen_dir(sh.x, sh.y, sh.z, e)
        self.hud.set_shade_arrow(*(d if d else (None, None)))

    def _wind(self, px, py, pz):
        s = self.sim
        active = s.wind_left > 0
        warn = s.wind_warning
        if (warn or active) and not self.wind_was:
            self.sfx.play("wind")
            self.hud.caption("Lá bay xào xạc... gió sắp thổi!" if warn else "Gió mạnh đang thổi!", 3, key="wind")
        self.wind_was = warn or active
        if (warn or active) and len(self.leaves) < 40 and self.frame % 2 == 0:
            a = math.radians(s.wind_dir) if active and s.wind_dir is not None else self.clock * 2
            leaf = gfx.U(model="quad", scale=(.25, .12), color=color.rgb(.55, .75, .35), double_sided=True,
                         position=(px - 8 * math.cos(a) + random.uniform(-6, 6), py + random.uniform(.5, 4), pz - 8 * math.sin(a) + random.uniform(-6, 6)))
            leaf.v = Vec3(math.cos(a), random.uniform(-.1, .2), math.sin(a)) * (8 if active else 4)
            leaf.life = 2.2
            self.leaves.append(leaf)
        for leaf in list(self.leaves):
            leaf.position += leaf.v * time.dt
            leaf.rotation += Vec3(200, 300, 100) * time.dt
            leaf.life -= time.dt
            if leaf.life <= 0:
                self.leaves.remove(leaf)
                destroy(leaf)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="game.app")
    ap.add_argument("--export-leaderboard", metavar="OUT_JSON", help="write {entries: [...]} and exit (no window)")
    ap.add_argument("--leaderboard-file", help="leaderboard storage (default ~/.dao_den_long/leaderboard.json)")
    ap.add_argument("--bench-scene", action="store_true", help="Ticket-04 benchmark scene (see game.bench)")
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--out", default="bench.json")
    ap.add_argument("--night", type=int, default=1, choices=[1, 2, 3])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--scenario")
    ap.add_argument("--screenshot")
    ap.add_argument("--frames", type=int, default=240)
    ap.add_argument("--autoplay", action="store_true")
    ap.add_argument("--ui", choices=["menu", "intro", "play", "pause", "settings", "controls", "result", "dawn", "name", "board"])
    ap.add_argument("--bench", type=float)
    ap.add_argument("--bench-out")
    ap.add_argument("--size", default="1280x720")
    args = ap.parse_args(argv)
    if args.export_leaderboard:
        from game.core import leaderboard
        entries = leaderboard.export(args.export_leaderboard, args.leaderboard_file or leaderboard.LEADERBOARD_PATH)
        print(f"exported {len(entries)} entries to {args.export_leaderboard}")
        return 0
    app = Ursina(title="Dao Den Long", development_mode=False, borderless=False, fullscreen=False,
                 vsync=not (args.bench or args.bench_scene))
    window.size = tuple(int(v) for v in args.size.split("x"))
    window.fps_counter.enabled = False
    window.exit_button.visible = False
    Game(args)
    app.run()


if __name__ == "__main__":
    main()
