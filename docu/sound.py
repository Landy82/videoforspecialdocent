"""부마 숏츠 v1.2 사운드트랙 = 작곡한 배경음악(score.py, 실제 악기 사운드폰트) + 화면에 맞춘 효과음
render.py 의 SHOTS·박자 격자(96BPM, 1마디 2.5초)를 그대로 읽는다.

  · 훅 타이핑: 글자마다 타자음 (32분음표 격자)
  · 5일 구간 시작(10s)·전환(27.5s): 서브 임팩트
  · 10.26 빌드업: 노이즈 라이저 → 전환 직전 1/8박 완전 정적 → 터짐
  · 대사 구간: 음악을 줄여(덕킹) 배우 목소리가 앞에 오게
  python3 docu/sound.py out.wav
"""
import math, os, sys, wave
import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R

SR = 48000
rng = np.random.default_rng(1979)


def ts(d):
    return np.arange(int(d * SR)) / SR


def noise(d):
    return rng.standard_normal(int(d * SR))


def filt(x, kind, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, kind, fs=SR, output='sos'), x)


def note(name):
    """'D4' → Hz"""
    names = {'C': -9, 'C#': -8, 'Db': -8, 'D': -7, 'Eb': -6, 'E': -5, 'F': -4, 'F#': -3, 'Gb': -3, 'G': -2,
             'Ab': -1, 'A': 0, 'Bb': 1, 'B': 2}
    return 440 * 2 ** ((names[name[:-1]] + 12 * (int(name[-1]) - 4)) / 12)


def sweep_noise(d, f0, f1, width=.35):
    """중심 주파수가 f0→f1 로 움직이는 대역 잡음 (STFT로 깎음)"""
    x = noise(d + .1)
    f, tt, Z = signal.stft(x, SR, nperseg=1024)
    fc = f0 * (f1 / f0) ** np.clip(tt / d, 0, 1)
    lf = np.log(np.maximum(f[:, None], 1))
    Z *= np.exp(-((lf - np.log(fc[None, :])) ** 2) / (2 * width ** 2))
    y = signal.istft(Z, SR, nperseg=1024)[1][:int(d * SR)]
    return y / (np.abs(y).max() + 1e-9)


# ── 소리 재료 ───────────────────────────────────────
def sub_hit(d=1.8, f0=120, f1=38, body=.5):
    t = ts(d)
    f = f1 + (f0 - f1) * np.exp(-t * 14)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.6)
    s += filt(noise(d), 'low', 2500) * np.exp(-t * 30) * body * .4
    return np.tanh(s * 1.6) * .8


def tick(f=1900):
    t = ts(.035)
    return filt(noise(.035), 'high', 2500) * np.exp(-t * 320) * .5 + np.sin(2 * np.pi * f * t) * np.exp(-t * 220) * .35


def key_click():
    t = ts(.07)
    g = .8 + .4 * rng.random()
    return (filt(noise(.07), 'band', [1200, 6000]) * np.exp(-t * 140) * .6 +
            np.sin(2 * np.pi * (180 + 60 * rng.random()) * t) * np.exp(-t * 70) * .5) * g


def typewriter_key(space=False):
    """기계식 타자기 한 타: 키 누름(딸깍) → 활자가 종이를 때림(금속성 탁) → 몸체 울림. 매번 조금씩 다르게"""
    d = .16
    t = ts(d)
    g = .8 + .35 * rng.random()
    press = filt(noise(d), 'high', 2500) * np.exp(-t * 1100) * .45
    off = int((.007 + .006 * rng.random()) * SR)
    strike = np.zeros_like(t)
    if not space:
        n = noise(d)
        f0 = 2300 * (1 + .07 * rng.standard_normal())
        body = (filt(n, 'band', [f0 * .9, f0 * 1.1]) * 1.0 + filt(n, 'band', [3900, 4500]) * .7 +
                filt(n, 'band', [6200, 7400]) * .45)
        strike[off:] = (body * np.exp(-t * 120))[:len(t) - off] * 1.6
    thump = filt(noise(d), 'low', 240) * np.exp(-t * 40) * (1.4 if space else .8)
    x = press + strike + thump
    return x / (np.abs(x).max() + 1e-9) * g


def heartbeat():
    t = ts(.45)
    one = np.sin(2 * np.pi * 52 * t) * np.exp(-t * 16) * (1 - np.exp(-t * 400))
    out = one.copy()
    j = int(.2 * SR)
    out[j:] += one[:len(out) - j] * .65
    return filt(out, 'low', 180)


def whoosh(d=.4, up=True):
    t = ts(d)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return sweep_noise(d, 400 if up else 5000, 5000 if up else 400, .5) * env


def riser(d):
    t = ts(d)
    x = sweep_noise(d, 300, 9000, .4) * (t / d) ** 2.5
    f = 110 * 4 ** (t / d)
    x += signal.sawtooth(2 * np.pi * np.cumsum(f) / SR) * (t / d) ** 3 * .25
    return filt(x, 'low', 9000)


def rev_swell(d):
    t = ts(d)
    return filt(noise(d), 'high', 1500) * (t / d) ** 4


def pluck(f, d=1.2, bright=1.0):
    t = ts(d)
    s = np.zeros_like(t)
    for k in range(1, 9):
        s += np.sin(2 * np.pi * f * k * (1 + .0004 * k * k) * t) / k ** 1.2 * np.exp(-t * (2.2 + k * 1.6 / bright))
    return s * (1 - np.exp(-t * 600)) * .5


def bell(f, d=4.0):
    t = ts(d)
    s = np.zeros_like(t)
    for r, a, dc in ((1, 1, .9), (2.0, .45, 1.4), (3.01, .25, 2.2), (4.17, .18, 3.0), (5.43, .1, 4.5)):
        s += np.sin(2 * np.pi * f * r * t) * a * np.exp(-t * dc)
    return s * (1 - np.exp(-t * 300)) * .35


def kick():
    t = ts(.5)
    f = 46 + 120 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) + filt(noise(.5), 'high', 3000) * np.exp(-t * 300) * .2


def hat():
    t = ts(.08)
    return filt(noise(.08), 'high', 7000) * np.exp(-t * 70)


def clap():
    t = ts(.3)
    x = filt(noise(.3), 'band', [900, 4000])
    env = np.exp(-t * 22)
    for o in (.0, .011, .022):
        env += (t >= o) * np.exp(-np.clip(t - o, 0, None) * 160) * .6
    return x * env * .5


def pad(d, notes, cutoff=1400, att=.8, rel=1.0):
    """디튠된 톱니파 화음 → 저역통과"""
    t = ts(d)
    s = np.zeros_like(t)
    for nm in notes:
        f = note(nm)
        for det in (-.004, 0, .004):
            s += signal.sawtooth(2 * np.pi * f * (1 + det) * t + rng.random() * 6.28)
    s = filt(s / (3 * len(notes)), 'low', cutoff, 2)
    env = np.minimum(1, t / att) * np.minimum(1, (d - t) / rel)
    return s * np.clip(env, 0, 1) * (1 + .06 * np.sin(2 * np.pi * .3 * t))


def drone(d, f=73.42, c0=220, c1=1500):
    """D2+A2 가산합성 드론, 시간에 따라 필터가 열림"""
    t = ts(d)
    fc = c0 * (c1 / c0) ** (t / d)
    s = np.zeros_like(t)
    for base, g in ((f, 1), (f * 1.5, .55), (f / 2, .5)):
        for kh in range(1, 28):
            fk = base * kh
            if fk > 6000:
                break
            amp = g / kh / np.sqrt(1 + (fk / fc) ** 4)
            s += np.sin(2 * np.pi * fk * (1 + .0015 * math.sin(kh)) * t + kh) * amp
    return s * (1 + .08 * np.sin(2 * np.pi * .25 * t))


def reverb_ir(d=2.6, decay=2.8):
    t = ts(d)
    ir = np.stack([filt(noise(d), 'low', 6000) * np.exp(-t * decay) for _ in range(2)])
    return ir / np.sqrt((ir ** 2).sum(axis=1, keepdims=True))


# ── 믹스 ────────────────────────────────────────────
def build(path):
    import score
    dur = R.DURATION
    n = int(dur * SR)
    if os.environ.get('VSCO') or os.environ.get('ORCH'):
        import orchestra                                    # 실제 오케스트라 녹음 샘플 (VSCO 2 CE, CC0)
        stems = orchestra.render_stems(dur)
        gains = {'piano': .9, 'strings': 1.0, 'perc': 1.0, 'choir': .8, 'brass': .9, 'color': .8}
        sends = {'piano': .2, 'strings': .22, 'perc': .15, 'choir': .25, 'brass': .2, 'color': .35}
    else:
        stems = score.render_stems(dur)                     # 사운드폰트 (GeneralUser GS)
        gains = {'piano': 1.0, 'strings': .9, 'perc': .95, 'choir': .55, 'brass': .6, 'color': .6}
        sends = {'piano': .25, 'strings': .35, 'perc': .18, 'choir': .5, 'brass': .35, 'color': .4}
    dry = np.zeros((2, n))
    send = np.zeros(n)
    for k, st in stems.items():
        x = st[:n].T.astype(np.float64) * gains[k]
        dry += x
        send += x.mean(axis=0) * sends[k]

    def add(sig, t, g=1.0, pan=0.0, rev=0.0):
        i = int(round(t * SR))
        if i >= n:
            return
        s = sig[:n - i] * g
        a = (pan + 1) * math.pi / 4
        dry[0, i:i + len(s)] += s * math.cos(a) * 1.414
        dry[1, i:i + len(s)] += s * math.sin(a) * 1.414
        send[i:i + len(s)] += s * rev

    # 0~25초 타자기: 화면에 글자가 찍히는 바로 그 시각에 한 타씩 (render.typing_events 와 공유)
    for j, (tt, ch) in enumerate(R.typing_events()):
        add(typewriter_key(ch == ' '), tt, .16 if ch != ' ' else .11, pan=-.25 + .5 * ((j * 7) % 11) / 10, rev=.05)
    t_turn = next(s[0] for s in R.SHOTS if s[5]['kind'] == 'turn')
    t_days = next(s[0] for s in R.SHOTS if s[5]['kind'] == 'day')
    t_build = next(s[0] for s in R.SHOTS if s[5]['kind'] == 'build')
    add(sub_hit(1.6, 110, 36, .4), t_days, .22, rev=.2)
    add(sub_hit(2.6, 140, 32, .8), t_turn, .28, rev=.3)
    gap = R.BEAT / 8
    add(riser(t_turn - gap - t_build), t_build, .12, rev=.15)

    ir = reverb_ir(2.8, 2.2)
    wet = np.stack([signal.fftconvolve(send, ir[c])[:n] for c in range(2)])
    mix = dry + wet * .32
    mix = filt(mix, 'high', 28)
    # 전환 직전 1/8박 정적
    g = np.ones(n)
    a, b = int((t_turn - gap) * SR), int(t_turn * SR)
    g[a - 240:a] = np.linspace(1, 0, 240); g[a:b] = 0
    # 대사 구간 덕킹 (-9dB)
    vt, _, _, vlen = R.VOICE
    duck = np.ones(n)
    v0, v1 = int(vt * SR), int((vt + vlen) * SR)
    ramp = int(.25 * SR)
    dk = .55 if (os.environ.get('VSCO') or os.environ.get('ORCH')) else .35
    duck[v0 - ramp:v0] = np.linspace(1, dk, ramp); duck[v0:v1] = dk; duck[v1:v1 + ramp] = np.linspace(dk, 1, ramp)
    # 구간 자동화: 몽타주를 가장 크게, 엔딩은 여유 있게
    t_m = next(s[0] for s in R.SHOTS if s[5]['kind'] == 'montage')
    auto = np.interp(np.arange(n) / SR, [0, t_m - .05, t_m, vt - .3, vt], [1, 1, 1.45, 1.45, 1])
    mix *= g * duck * auto
    tail = int(1.0 * SR)
    mix[:, -tail:] *= np.linspace(1, 0, tail) ** 1.5
    mix = np.tanh(mix / np.abs(mix).max() * 1.2) / np.tanh(1.2) * .89
    pcm = (mix.T * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'music.wav')
