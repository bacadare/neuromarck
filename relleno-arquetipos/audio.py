"""Genera la voz y el sonido del relleno y los une a los MP4.

Voz: Piper (TTS neuronal que corre en local, `pip install piper-tts`).
Sonido: ambiente, barridos y campanas sintetizados con numpy.

    python3 audio.py RUTA/es_MX-claude-high.onnx

El modelo de voz no está en el repo (67 MB). Se descarga de
https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-es_MX-claude-high.tar.bz2
"""
import subprocess, sys, os, wave, tempfile
import numpy as np

SR, DUR, INTRO, SEG = 48000, 30.0, 3.0, 2.0
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = sys.argv[1]

NOMBRES = ['El Inocente', 'El Sabio', 'El Explorador', 'El Rebelde', 'El Mago', 'El Héroe', 'El Amante',
           'El Bufón', 'La Persona Común', 'El Cuidador', 'El Gobernante', 'El Creador']
# (texto, segundo de inicio, duración máxima)
LINEAS = [('Los doce arquetipos de marca.', 0.55, 2.3)]
LINEAS += [(n + '.', INTRO + i * SEG + 0.30, 1.55) for i, n in enumerate(NOMBRES)]
LINEAS += [('¿Cuál es tu arquetipo?', 27.35, 2.2)]

N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(12)


def hablar(texto, maximo):
    """Sintetiza una frase y la acelera lo justo si no cabe en su hueco."""
    escala = 1.0
    while True:
        with tempfile.TemporaryDirectory() as d:
            wav = os.path.join(d, 'v.wav')
            subprocess.run(['piper', '-m', MODEL, '-f', wav, '--length-scale', f'{escala:.2f}'],
                           input=texto.encode(), check=True, capture_output=True)
            pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', wav, '-af',
                                  'silenceremove=start_periods=1:start_threshold=-45dB,areverse,'
                                  'silenceremove=start_periods=1:start_threshold=-45dB,areverse',
                                  '-ar', str(SR), '-ac', '1', '-f', 'f32le', '-'], check=True, capture_output=True).stdout
        x = np.frombuffer(pcm, dtype=np.float32).astype(np.float64)
        if len(x) / SR <= maximo or escala < 0.7:
            return x / (np.abs(x).max() + 1e-9), escala
        escala *= max(0.85, maximo / (len(x) / SR) * 0.98)


def poner(pista, x, inicio, gan=1.0, pan=0.0):
    i = int(inicio * SR)
    x = x[:max(0, N - i)]
    pista[i:i + len(x), 0] += x * gan * np.sqrt((1 - pan) / 2)
    pista[i:i + len(x), 1] += x * gan * np.sqrt((1 + pan) / 2)


def ruido_filtrado(n, f0, f1, ancho=0.35):
    """Ruido con un pasabanda que barre de f0 a f1 (por bloques, vía FFT)."""
    out, blk, hop = np.zeros(n + 4096), 2048, 512
    win = np.hanning(blk)
    fr = np.fft.rfftfreq(blk, 1 / SR)
    for k in range(0, n, hop):
        fc = f0 * (f1 / f0) ** (k / n)
        spec = np.fft.rfft(rng.standard_normal(blk) * win)
        spec *= np.exp(-0.5 * (np.log(np.maximum(fr, 1) / fc) / ancho) ** 2)
        out[k:k + blk] += np.fft.irfft(spec) * win
    return out[:n]


def barrido(dur=0.6):
    n = int(dur * SR)
    x = ruido_filtrado(n, 350, 5200)
    return x * np.sin(np.pi * np.arange(n) / n) ** 2 / (np.abs(x).max() + 1e-9)


def campana(freq, dur=1.6):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * freq * m * tt) * np.exp(-tt * d)
            for m, a, d in [(1, 1, 3.2), (2.01, 0.35, 5), (3.02, 0.18, 8), (4.2, 0.08, 12)])
    return x * np.minimum(1, tt / 0.004)


def eco(pista, retardo=0.31, mezcla=0.28, rep=4):
    out, d = pista.copy(), int(retardo * SR)
    for r in range(1, rep + 1):
        out[r * d:] += pista[:-r * d][:, ::-1] * mezcla ** r
    return out


# ---- Ambiente: acorde grave que respira, en bucle exacto de 30 s --------
amb = np.zeros((N, 2))
for f, g in [(73.42, 1.0), (110.0, 0.7), (146.83, 0.55), (220.0, 0.30), (261.63, 0.16), (329.63, 0.12)]:  # Re menor 9
    for canal, des in ((0, -0.25), (1, 0.25)):
        fq = round((f + des) * DUR) / DUR                     # nº entero de ciclos -> bucle perfecto
        lfo = 0.72 + 0.28 * np.sin(2 * np.pi * t * round(rng.integers(2, 6)) / DUR + rng.uniform(0, 6.28))
        amb[:, canal] += g * lfo * (np.sin(2 * np.pi * fq * t) + 0.25 * np.sin(2 * np.pi * 2 * fq * t))
aire = ruido_filtrado(N, 2400, 2400, 0.5)
amb += 0.5 * np.stack([aire, np.roll(aire, SR // 3)], 1) / np.abs(aire).max()
amb *= 0.11 / np.abs(amb).max() * 4

# ---- Efectos ------------------------------------------------------------
fx = np.zeros((N, 2))
ESCALA = [293.66, 349.23, 392.0, 440.0, 523.25, 587.33, 698.46, 783.99, 880.0, 1046.5, 1174.66, 1396.91]  # Re menor pentatónica
sw = barrido()
for i in range(12):
    t0 = INTRO + i * SEG
    poner(fx, sw, t0 - 0.05, 0.22, pan=(-0.5 if i % 2 else 0.5))   # giro de la rueda
    poner(fx, campana(ESCALA[i]), t0 + 0.27, 0.20)                  # se enciende el nodo
for i in range(12):                                                 # nodos apareciendo en la intro
    poner(fx, campana(1760 * 2 ** (i / 12), 0.25), 0.35 + i * 0.13, 0.035, pan=np.sin(i))
subida = ruido_filtrado(int(1.6 * SR), 300, 7000) * np.linspace(0, 1, int(1.6 * SR)) ** 2.5
poner(fx, subida / np.abs(subida).max(), INTRO - 1.62, 0.20)        # subida hacia el primer arquetipo
for f, g in [(146.83, 0.30), (293.66, 0.22), (440.0, 0.16), (587.33, 0.12), (698.46, 0.09)]:
    poner(fx, campana(f, 3.0), 27.0, g)                             # acorde de cierre
poner(fx, barrido(1.0), 26.75, 0.25)
fx = eco(fx)

# ---- Voz ----------------------------------------------------------------
voz = np.zeros((N, 2))
for texto, inicio, maximo in LINEAS:
    x, escala = hablar(texto, maximo)
    print(f'{inicio:6.2f}s  {len(x) / SR:4.2f}s  x{escala:.2f}  {texto}')
    poner(voz, x, inicio, 0.80)
voz += (eco(voz, 0.11, 0.22, 3) - voz) * 0.5                        # un poco de sala

# La música baja cuando habla la voz
env = np.abs(voz).max(1)
k = int(0.12 * SR)
env = np.convolve(np.maximum.reduceat(np.pad(env, (0, k)), np.arange(0, N, 480)).repeat(480)[:N], np.ones(k) / k, 'same')
duck = 1 - 0.45 * np.clip(env * 4, 0, 1)

mezcla = (amb + fx) * 0.62 * duck[:, None] + voz
fade = np.minimum(1, np.minimum(t / 0.4, (DUR - t) / 0.5))          # mismas entradas/salidas que el video
mezcla *= fade[:, None]
mezcla = np.tanh(mezcla * 1.15)
mezcla *= 0.80 / np.abs(mezcla).max()

salida = os.path.join(HERE, 'arquetipos-audio.wav')
with wave.open(salida, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mezcla * 32767).astype('<i2').tobytes())

for nombre in ('vertical', 'horizontal'):
    mudo = os.path.join(HERE, f'arquetipos-{nombre}.mp4')
    if os.path.exists(mudo):
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', mudo, '-i', salida, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                        '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart',
                        os.path.join(HERE, f'arquetipos-{nombre}-con-voz.mp4')], check=True)
print('listo')
