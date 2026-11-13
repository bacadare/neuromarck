import numpy as np, wave
SR = 48000; DUR = 26.4; N = int(SR * DUR)
L = np.zeros(N + SR * 4); R = np.zeros(N + SR * 4)
rs = np.random.RandomState(3)

def bp(x, lo, hi):  # fft brickwall-ish bandpass with soft edges
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = 1 / (1 + (lo / np.maximum(f, 1e-6)) ** 6) / (1 + (f / hi) ** 6)
    return np.fft.irfft(X * m, len(x))
def add(x, t, g=1.0, pan=0.0):
    i = int(t * SR); n = len(x)
    L[i:i + n] += x * g * (1 - max(pan, 0)); R[i:i + n] += x * g * (1 + min(pan, 0))
def env(n, a, d):  # attack sec, exponential decay rate
    t = np.arange(n) / SR; return np.minimum(t / max(a, 1e-4), 1) * np.exp(-t * d)

def impact(big=1.0):
    n = int(SR * 1.6); t = np.arange(n) / SR
    f = 34 + 75 * np.exp(-t * 16); ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.tanh(np.sin(ph) * 2.2) * np.exp(-t * (3.2 / big))
    thump = bp(rs.randn(n), 60, 900) * np.exp(-t * 22) * 1.3
    click = bp(rs.randn(n), 1500, 9000) * np.exp(-t * 70) * 0.5
    tail = bp(rs.randn(n), 120, 1800) * np.exp(-t * 4.5) * 0.14
    return (sub * 0.95 + thump + click + tail) * big
def whoosh(d=0.6, lo=300, hi=6000, rev=False):
    n = int(SR * d); t = np.arange(n) / SR; x = rs.randn(n); out = np.zeros(n)
    # sweep: sum of bands weighted by moving center
    for k, fc in enumerate(np.geomspace(lo, hi, 9)):
        c = k / 8; pos = t / d; w = np.exp(-((pos - (0.15 + 0.6 * c)) ** 2) / 0.02)
        out += bp(x, fc * 0.75, fc * 1.3) * w
    out *= np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.5
    return out[::-1] if rev else out
def riser(d=1.6):
    n = int(SR * d); t = np.arange(n) / SR; p = t / d
    f = 110 * 2 ** (p * 2.6); ph = 2 * np.pi * np.cumsum(f) / SR
    tone = (np.sin(ph) + 0.5 * np.sin(ph * 1.5) + 0.3 * np.sin(ph * 2.01)) * 0.25
    noise = bp(rs.randn(n), 800, 12000) * 0.5
    return (tone + noise) * p ** 2.5
def chime(f0=1320, d=1.6):
    n = int(SR * d); t = np.arange(n) / SR; out = np.zeros(n)
    for m, a, dc in [(1, 1, 3), (2.76, .5, 4.5), (5.4, .28, 6), (8.93, .15, 8), (1.5, .3, 3.5)]:
        out += a * np.sin(2 * np.pi * f0 * m * t) * np.exp(-t * dc)
    return out * np.minimum(t / 0.003, 1) * 0.3
def braam(d=2.6, f0=55):
    n = int(SR * d); t = np.arange(n) / SR; out = np.zeros(n)
    for det in [0.994, 1, 1.006, 2.003, 1.498, 0.5]:
        ph = (f0 * det * t) % 1; out += 2 * ph - 1
    out = bp(out, 35, 900 + 0 * t[0]) * np.minimum(t / 0.04, 1) * np.exp(-t * 1.4)
    return np.tanh(out * 0.5) * 0.7
def tick(f=2400):
    n = int(SR * 0.05); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) * 0.5 + bp(rs.randn(n), 2000, 10000) * 0.5) * np.exp(-t * 110)
def swish_short():
    return whoosh(0.28, 900, 9000)

_i, _w, _t = impact, whoosh, tick
impact = lambda big=1.0: _i(big) * 0.42
whoosh = lambda d=0.6, lo=300, hi=6000, rev=False: _w(d * 1.5, lo, hi * 0.6, rev) * 0.55
tick = lambda f=2400: _t(f) * 0.5
# soft pad (D minor) for a more refined bed
_tt = np.arange(N) / SR; pad = np.zeros(N)
for f, a_ in [(146.83, .5), (174.61, .4), (220.0, .45), (293.66, .3), (440.0, .12)]:
    for det in (0.997, 1.003):
        pad += a_ * np.sin(2 * np.pi * f * det * _tt + rs.rand() * 6)
pad *= (0.6 + 0.4 * np.sin(2 * np.pi * 0.09 * _tt)) * np.minimum(_tt / 2.5, 1) * np.minimum((DUR - _tt) / 1.5, 1)
add(pad, 0, 0.035)
# ---- bed: dark drone + pulse (D) ----
t = np.arange(N) / SR
drone = np.zeros(N)
for f, a in [(36.71, .5), (73.42, .5), (110.0, .22), (146.83, .15), (220.0, .06), (293.66, .04)]:
    drone += a * np.sin(2 * np.pi * f * t + rs.rand() * 6) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t + rs.rand() * 6))
air = bp(rs.randn(N), 3000, 9000) * 0.012 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t))
bed = (drone * 0.11 + air) * np.minimum(t / 0.6, 1) * np.minimum((DUR - t) / 0.8, 1)
# intensity lift from the title on
bed *= 0.7 + 0.3 * np.clip((t - 4.0) / 2.0, 0, 1)
add(bed, 0, 1.0)
# heartbeat-ish pulse, 100 bpm (0.6 s) — drives pace
beat = 0.6
for k in range(int(DUR / beat)):
    tb = 0.45 + k * beat
    if tb > DUR - 1.2: break
    n = int(SR * 0.35); tt = np.arange(n) / SR
    f = 42 + 40 * np.exp(-tt * 30); p = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 13)
    g = 0.1 if tb < 5.87 else 0.14
    add(p, tb, g)
    if tb > 5.87 and k % 2 == 1: add(tick(5200) * 0.5, tb + beat / 2, 0.09, (-1) ** k * 0.4)

# ---- events (video time) ----
T = dict(s2=4.0, s3=7.0, s4=11.95, s5=17.55, s6=23.45)
add(whoosh(0.5), 0.05, 0.3)
add(impact(1.0), 0.45, 0.62); add(impact(1.2), 1.95, 0.66); add(chime(990), 1.97, 0.25)
add(whoosh(0.3, rev=False), 1.7, 0.3)
for k in range(8): add(tick(1800 + k * 150), 2.0 + k * 0.045, 0.12, (k % 2) * 0.8 - 0.4)   # cubes snapping into order
add(whoosh(0.55), T['s2'] - 0.3, 0.45)
add(riser(1.75), 4.1, 0.42)
add(impact(1.9), 5.87, 0.8); add(braam(2.8), 5.87, 0.42); add(chime(660, 2.4), 5.9, 0.4); add(chime(1320, 2.0), 5.95, 0.22)
for key, pan in [('s3', -0.5), ('s4', 0.0), ('s5', 0.5), ('s6', 0.0)]:
    add(whoosh(0.6), T[key] - 0.33, 0.5, pan); add(impact(0.7), T[key] + 0.06, 0.34)
add(chime(880), 7.5, 0.2)
add(swish_short(), 8.0, 0.3, -0.3); add(impact(0.6), 8.2, 0.3)
add(swish_short(), 9.45, 0.3, 0.3); add(impact(0.9), 9.65, 0.42)
add(swish_short(), 10.15, 0.25); add(tick(), 10.35, 0.25)
for k in range(7): add(tick(2600 + 120 * k), 10.4 + k * 0.07, 0.09)
add(impact(0.5), 10.95, 0.3)
for i, tc in enumerate([13.2, 14.6, 15.38, 16.03]):
    pan = -0.5 if i % 2 == 0 else 0.5
    add(whoosh(0.34, 500, 7000), tc - 0.3, 0.42, pan); add(impact(1.0), tc + 0.03, 0.5); add(chime([660, 880, 990, 1320][i], 1.2), tc + 0.05, 0.22, -pan)
for i, tc in enumerate([18.7, 19.73, 20.78, 21.78]):
    pan = -0.5 if i % 2 == 0 else 0.5
    add(whoosh(0.36, 500, 8000), tc - 0.3, 0.44, pan); add(impact(1.0), tc + 0.05, 0.5); add(chime([1320, 1485, 1760, 1980][i], 1.3), tc + 0.06, 0.26, -pan)
add(riser(1.2), 23.7, 0.3)
add(impact(1.0), 23.7, 0.4)
add(impact(2.0), 24.9, 0.8); add(braam(2.4), 24.9, 0.4); add(chime(660, 2.6), 24.92, 0.4); add(chime(990, 2.2), 24.96, 0.25)
add(chime(1980, 1.5), 25.25, 0.12)

mix = np.stack([L[:N], R[:N]], 1)
fade = np.minimum((DUR - t) / 0.45, 1)[:, None]; mix *= fade
mix = np.tanh(mix * 1.1) * 0.9
w = wave.open('sfx_e.wav', 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype('<i2').tobytes()); w.close()
print('peak', np.abs(mix).max(), 'rms', np.sqrt((mix ** 2).mean()))
