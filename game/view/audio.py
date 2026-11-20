"""Sound + persistent settings (volume, mouse sensitivity). Sounds are synthesized by tools/gen_sounds.py."""
import json
from pathlib import Path

SETTINGS_PATH = Path.home() / ".dao_den_long" / "settings.json"
DEFAULTS = {"volume": 0.7, "mouse_sensitivity": 1.0, "colorblind": 0.0}
SOUND_DIR = Path(__file__).resolve().parents[1] / "assets" / "sounds"


def load_settings(path=SETTINGS_PATH):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return {k: float(data.get(k, v)) for k, v in DEFAULTS.items()}
    except (OSError, ValueError, TypeError):
        return dict(DEFAULTS)


def save_settings(s, path=SETTINGS_PATH):
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(s, indent=2), encoding="utf-8")
    except OSError:
        pass


class Sfx:
    def __init__(self, settings, enabled=True):
        self.settings = settings
        self.enabled = enabled
        self.clips = {}
        self.music = None
        if not enabled:
            return
        from panda3d.core import Filename
        from ursina import Audio, application
        for f in sorted(SOUND_DIR.glob("*.wav")):
            clip = application.base.loader.loadSfx(Filename.fromOsSpecific(str(f.resolve())))
            if clip is None:
                continue
            self.clips[f.stem] = Audio(clip, autoplay=False, loop=f.stem == "music")
        self.music = self.clips.get("music")
        self.apply_volume()

    def apply_volume(self):
        v = self.settings["volume"]
        for name, a in self.clips.items():
            a.volume = v * (.45 if name == "music" else 1.0)

    def play(self, name):
        if self.enabled and name in self.clips:
            self.clips[name].play()

    def start_music(self):
        if self.music and not self.music.playing:
            self.music.play()
