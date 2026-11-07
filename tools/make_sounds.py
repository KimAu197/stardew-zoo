"""Synthesize distinct default animal WAVs (PCM 16-bit 22050 Hz mono)."""

import math
import struct
import wave
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "StardewZoo" / "sounds"
RATE = 22050
DURATION = 1.6


def write_wav(path: Path, samples):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        frames = b"".join(struct.pack("<h", max(-32767, min(32767, int(s * 32767)))) for s in samples)
        wav.writeframes(frames)


def tone(freq, length, volume=0.35, wave_fn=math.sin):
    n = int(RATE * length)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(1.0, i / 400) * min(1.0, (n - i) / 800)
        out.append(volume * env * wave_fn(2 * math.pi * freq * t))
    return out


def saw(freq, length, volume=0.3):
    def fn(x):
        frac = (x / (2 * math.pi)) % 1.0
        return 2 * frac - 1
    return tone(freq, length, volume, fn)


def noise(length, volume=0.2, band=0.02):
    n = int(RATE * length)
    x = 0.0
    out = []
    state = 1
    for i in range(n):
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        x = (1 - band) * x + band * ((state / 0x40000000) - 1)
        env = min(1.0, i / 200) * min(1.0, (n - i) / 400)
        out.append(volume * env * x)
    return out


def concat(*parts):
    samples = []
    for part in parts:
        samples.extend(part)
        samples.extend([0.0] * int(RATE * 0.04))
    return samples


ANIMALS = {
    "Penguin": concat(tone(880, 0.18), tone(1320, 0.22), tone(990, 0.3)),
    "Panda": concat(saw(140, 0.4, 0.4), saw(110, 0.5, 0.35)),
    "Lion": concat(saw(90, 0.7, 0.45), noise(0.3, 0.25, 0.08)),
    "Giraffe": concat(tone(420, 0.25, 0.3), tone(380, 0.4, 0.28)),
    "Monkey": concat(tone(1400, 0.08, 0.3), tone(900, 0.08, 0.3), tone(1500, 0.08, 0.3), tone(1000, 0.2, 0.3)),
    "Capybara": concat(tone(700, 0.12, 0.28), tone(500, 0.18, 0.28), noise(0.2, 0.12)),
    "Elephant": concat(saw(220, 0.35, 0.4), saw(160, 0.5, 0.4), tone(300, 0.4, 0.25)),
    "Dinosaur": concat(saw(70, 0.8, 0.45), noise(0.4, 0.3, 0.05)),
    "Gorilla": concat(noise(0.15, 0.4, 0.2), saw(100, 0.4, 0.4), noise(0.15, 0.35, 0.2)),
    "Raccoon": concat(tone(1600, 0.07, 0.25), tone(1200, 0.07, 0.25), tone(1800, 0.1, 0.25), tone(1100, 0.15, 0.25)),
    "Alpaca": concat(tone(520, 0.35, 0.28), tone(560, 0.4, 0.22)),
    "SeaLion": concat(tone(480, 0.12, 0.4), tone(360, 0.18, 0.4), tone(500, 0.12, 0.4), tone(340, 0.25, 0.35)),
    "Bear": concat(saw(80, 0.55, 0.42), saw(60, 0.6, 0.38)),
    "Flamingo": concat(tone(980, 0.12, 0.28), tone(720, 0.18, 0.3), tone(1100, 0.22, 0.25)),
    "Owl": concat(tone(310, 0.35, 0.32), tone(240, 0.45, 0.28)),
    "Deer": concat(tone(640, 0.18, 0.28), tone(480, 0.28, 0.26), tone(700, 0.16, 0.22)),
    "NightHeron": concat(tone(860, 0.1, 0.3), tone(540, 0.16, 0.28), tone(780, 0.22, 0.26)),
}


def main():
    defaults = OUT / "defaults"
    for name, samples in ANIMALS.items():
        write_wav(defaults / f"{name}.wav", samples)
    print(f"Wrote {len(ANIMALS)} default WAVs to {defaults}")


if __name__ == "__main__":
    main()
