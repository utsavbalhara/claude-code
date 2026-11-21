"""Synthesizes the soundtrack: sad piano progression + SFX synced to render.py events."""
import sys, wave
import numpy as np

SR = 48000
DUR = 33.6
N = int(SR * DUR)
rng = np.random.default_rng(7)
mus = np.zeros(N)
fx = np.zeros(N)

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

def add(buf, t, sig):
    i = int(t * SR)
    j = min(N, i + len(sig))
    if i < N: buf[i:j] += sig[: j - i]

def piano(m, dur=3.0, vel=0.3):
    t = np.arange(int(SR * dur)) / SR
    f = hz(m)
    s = sum((0.6 ** k) * np.sin(2 * np.pi * f * (k + 1) * t * (1 + 0.0004 * k)) for k in range(5))
    env = np.exp(-t * (1.6 + m / 60)) * np.minimum(1, t / 0.004)
    env *= np.minimum(1, (dur - t) / 0.3)
    return vel * s * env

def pad(ms, dur, vel=0.05):
    t = np.arange(int(SR * dur)) / SR
    s = sum(np.sin(2 * np.pi * hz(m) * t) + 0.3 * np.sin(2 * np.pi * hz(m) * 2.003 * t) for m in ms)
    env = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.5)
    return vel * s * env

# chords (bass, voicing) ~ Am F C G — melancholic, loops 2.2s per chord
CH = {"Am": (45, [57, 60, 64]), "F": (41, [57, 60, 65]), "C": (48, [55, 60, 64]),
      "G": (43, [55, 59, 62]), "Em": (40, [55, 59, 64]), "Fmaj7": (41, [57, 60, 64])}
prog = ["Am", "F", "C", "G"] * 3 + ["Am", "F", "Fmaj7", "F", "C", "C"]
t = 0.0
step = 2.15
melody = {0: 76, 2: 72, 4: 74, 6: 71, 8: 72, 10: 69, 12: 76, 14: 77, 16: 79, 18: 76}
for k, name in enumerate(prog):
    if t >= DUR - 1: break
    b, v = CH[name]
    last = t >= 28.7
    add(mus, t, piano(b - 12 if last else b, 4.0, 0.28))
    for j, m in enumerate(v):  # gentle arpeggio
        add(mus, t + 0.18 * j, piano(m, 3.4, 0.16))
    if not last:
        add(mus, t + 1.1, piano(v[-1] + 12, 2.0, 0.07))
    if k in melody and t > 8:
        add(mus, t + 0.6, piano(melody[k], 2.5, 0.09))
    t += step if not last else 2.6
# swell pad under the emotional twist + ending
add(mus, 21.8, pad([45, 52, 57], 7.0, 0.035))
add(mus, 28.8, pad([41, 48, 57, 64], 4.8, 0.05))

# ---------------------------------------------------------------- SFX
def blip(f0=700, f1=1100, d=0.09, v=0.25):
    t = np.arange(int(SR * d)) / SR
    f = np.linspace(f0, f1, len(t))
    return v * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30)

def buzz(d=0.35, v=0.25):
    t = np.arange(int(SR * d)) / SR
    s = np.sign(np.sin(2 * np.pi * 150 * t)) * 0.6 + np.sin(2 * np.pi * 300 * t) * 0.4
    return v * s * (0.6 + 0.4 * np.sin(2 * np.pi * 35 * t)) * np.minimum(1, (d - t) / 0.03)

def click(v=0.3):
    t = np.arange(int(SR * 0.03)) / SR
    return v * rng.standard_normal(len(t)) * np.exp(-t * 300)

def whoosh(d=0.45, v=0.15):
    t = np.arange(int(SR * d)) / SR
    n = rng.standard_normal(len(t))
    n = np.convolve(n, np.ones(25) / 25, "same")
    return v * 4 * n * np.sin(np.pi * t / d) ** 2

def ding(f=1320, v=0.13):
    return piano(88, 1.2, v) + piano(95, 1.2, v * 0.6)

def thud(v=0.5):
    t = np.arange(int(SR * 0.35)) / SR
    return v * np.sin(2 * np.pi * (60 + 40 * np.exp(-t * 20)) * t) * np.exp(-t * 12)

def step_snd(v=0.12):
    t = np.arange(int(SR * 0.08)) / SR
    return v * (np.sin(2 * np.pi * 90 * t) + 0.4 * rng.standard_normal(len(t)) * 0.3) * np.exp(-t * 50)

def chuckle(v=0.1):  # soft warm "ha" — short rising pitched puffs
    out = np.zeros(int(SR * 0.9))
    for i in range(4):
        b = blip(330 + 30 * i, 280, 0.12, v)
        o = int(i * 0.18 * SR); out[o:o + len(b)] += b
    return out

POPS = [0.35, 2.3, 6.4, 8.6 + 2.3, 15.2 + 2.6, 21.8 + 1.5, 21.8 + 2.0, 21.8 + 3.9]
for p in POPS: add(fx, p, blip())
for tt in np.arange(3.7, 6.3, 0.36): add(fx, tt, step_snd())
for tt in np.arange(15.5, 17.6, 0.34): add(fx, tt, step_snd(0.08))
for tt in np.arange(22.1, 23.6, 0.25): add(fx, tt, step_snd(0.06))
add(fx, 4.6, thud(0.15)); add(fx, 26.9, thud(0.45))
# phone
for base in (8.6 + 0.6,):
    add(fx, base, buzz()); add(fx, base + 0.5, buzz())
add(fx, 8.6 + 2.1, click(0.4)); add(fx, 8.6 + 2.6, thud(0.2))
add(fx, 8.6 + 3.6, ding()); add(fx, 8.6 + 4.8, blip(500, 500, 0.05, 0.1))
for tt in np.arange(8.6 + 3.0, 8.6 + 6.2, 0.17): add(fx, tt + rng.uniform(0, 0.05), click(0.08))
add(fx, 15.2 + 0.6, ding()); add(fx, 15.2 + 2.1, whoosh()); add(fx, 15.2 + 3.0, ding())
add(fx, 21.8 + 0.5, ding(v=0.08)); add(fx, 21.8 + 1.2, blip(880, 880, 0.15, 0.15))
add(fx, 28.8, whoosh(0.8, 0.1))
# laughs / warmth
for tt in (5.4, 8.6 + 3.6, 21.8 + 5.2): add(fx, tt, chuckle())
for tt in (6.6, 15.2 + 5.0, 21.8 + 5.6): add(fx, tt, ding(v=0.05))
# room tone
room = np.convolve(rng.standard_normal(N), np.ones(60) / 60, "same") * 0.012
mix = mus * 0.9 + fx + room
# simple reverb on music
d = int(0.09 * SR)
for k in range(1, 6):
    mix[d * k:] += mus[:-d * k] * (0.28 ** k) * 0.9
fade = np.ones(N); fl = int(0.6 * SR); fade[-fl:] = np.linspace(1, 0, fl)
mix *= fade
mix = mix / np.max(np.abs(mix)) * 0.9
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
