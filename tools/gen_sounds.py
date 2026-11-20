"""Synthesize all game sounds (original, no external assets) into game/assets/sounds/*.wav.
Run: python tools/gen_sounds.py   (deterministic output)"""
import math
import random
import struct
import wave
from pathlib import Path

SR = 22050
OUT = Path(__file__).resolve().parents[1] / "game" / "assets" / "sounds"


def env(i, n, a=.01, r=.3):
    t = i / SR
    dur = n / SR
    k = min(1.0, t / a) if a > 0 else 1.0
    return k * max(0.0, min(1.0, (dur - t) / (r * dur)))


def tone(freqs, dur, vol=.4, wave_="sine", a=.01, r=.4, slide=0.0):
    n = int(dur * SR)
    out = []
    for i in range(n):
        t = i / SR
        s = 0.0
        for f in freqs:
            ff = f * (1 + slide * t / dur)
            ph = 2 * math.pi * ff * t
            s += math.sin(ph) if wave_ == "sine" else (2 * (ph / (2 * math.pi) % 1) - 1) * .5 if wave_ == "saw" else (1 if math.sin(ph) > 0 else -1) * .4
        out.append(s / len(freqs) * vol * env(i, n, a, r))
    return out


def noise(dur, vol=.3, lp=.1, seed=1, a=.01, r=.6):
    rng = random.Random(seed)
    n = int(dur * SR)
    out, y = [], 0.0
    for i in range(n):
        y += lp * (rng.uniform(-1, 1) - y)
        out.append(y * vol * 3 * env(i, n, a, r))
    return out


def seq(*parts, gap=0.0):
    out = []
    for p in parts:
        out += p + [0.0] * int(gap * SR)
    return out


def mix(*tracks):
    n = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(n)]


def save(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32000)) for s in data))


def music():
    """16 s pentatonic night lullaby: soft pad + plucked melody (loops)."""
    notes = [392, 440, 523, 587, 659, 784]
    rng = random.Random(7)
    pad = mix(*[tone([f, f * 1.5], 16, .10, a=2, r=.3) for f in (196, 147)])
    mel = []
    for _ in range(32):
        f = rng.choice(notes)
        mel += tone([f, f * 2], .5, .16, a=.005, r=.9)
    return mix(pad, mel)


SOUNDS = {
    "pickup": lambda: tone([1320, 1980], .12, .35, r=.8, slide=.2),
    "lantern": lambda: seq(tone([523, 784], .18, .4), tone([659, 988], .18, .4), tone([784, 1175], .5, .45, r=.8)),
    "pulse": lambda: mix(noise(.5, .35, .25, 2, a=.02), tone([220, 330], .5, .3, slide=1.2)),
    "hit": lambda: mix(noise(.3, .5, .05, 3, a=.001), tone([90], .3, .5, slide=-.5)),
    "jump": lambda: tone([440], .15, .3, wave_="square", slide=.8),
    "dash": lambda: noise(.25, .45, .4, 4, a=.005, r=.9),
    "win": lambda: seq(*[tone([f, f * 1.5], .2, .4) for f in (523, 659, 784)], tone([1047, 1568], .8, .45, r=.7)),
    "lose": lambda: seq(*[tone([f], .3, .4, wave_="saw") for f in (392, 349, 311)], tone([262], .9, .4, wave_="saw", r=.8)),
    "shade": lambda: mix(tone([70, 73], .9, .45, wave_="saw", a=.3), noise(.9, .25, .03, 5, a=.3)),
    "tick": lambda: tone([1760], .06, .35, r=.9),
    "wind": lambda: noise(2.0, .5, .02, 6, a=.6, r=.5),
    "charm": lambda: seq(tone([880, 1320], .1, .35), tone([1175, 1760], .25, .35, r=.8)),
    "steal": lambda: tone([660, 990], .35, .35, slide=-.6),
    "music": music,
}

if __name__ == "__main__":
    for name, fn in SOUNDS.items():
        save(name, fn())
    print("wrote", len(SOUNDS), "sounds to", OUT)
