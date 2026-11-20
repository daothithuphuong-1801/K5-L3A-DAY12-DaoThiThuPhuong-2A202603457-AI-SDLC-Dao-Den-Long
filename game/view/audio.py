"""Sound + persistent settings (volume, mouse sensitivity). Sounds are synthesized by tools/gen_sounds.py."""
import json
from pathlib import Path

SETTINGS_PATH = Path.home() / ".dao_den_long" / "settings.json"
DEFAULTS = {"volume": 0.7, "mouse_sensitivity": 1.0, "colorblind": 0.0, "reduce_motion": 0.0, "large_text": 0.0}
DEFAULT_KEYS = {"up": "up arrow", "down": "down arrow", "left": "left arrow", "right": "right arrow", "jump": "space",
                "dash": "shift", "interact": "e", "pulse": "f", "pause": "escape"}


def key_conflict(keys, action, key):
    """Return the other action already using `key`, or None."""
    for a, k in keys.items():
        if a != action and k == key:
            return a
    return None
SOUND_DIR = Path(__file__).resolve().parents[1] / "assets" / "sounds"


def load_settings(path=SETTINGS_PATH):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        s = {k: float(data.get(k, v)) for k, v in DEFAULTS.items()}
        keys = dict(DEFAULT_KEYS)
        if isinstance(data.get("keys"), dict):
            keys.update({a: str(k) for a, k in data["keys"].items() if a in DEFAULT_KEYS and isinstance(k, str)})
        if len(set(keys.values())) != len(keys):  # corrupted file with duplicates -> defaults
            keys = dict(DEFAULT_KEYS)
        s["keys"] = keys
        return s
    except (OSError, ValueError, TypeError):
        return {**DEFAULTS, "keys": dict(DEFAULT_KEYS)}


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
