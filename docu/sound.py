"""부마 숏폼 사운드트랙 — 샘플·음원 없이 numpy/scipy 코드로 직접 합성 (저작권 걱정 없음)
render.py 의 SHOTS 타이밍을 그대로 읽어 컷·글자 등장에 소리를 맞춘다.

  0–3s     훅: 낮은 드론 + 심장박동 + 글자마다 타자음
  3–29.5s  연표: 시계 초침 + 컷마다 서브 임팩트, 날짜 숫자가 굴러갈 때 틱 소리, 드론이 점점 열림
           16~20일 구간은 심장박동이 빨라지고, 10.26 뒤로 상승음 → 정적
  29.5s    화이트 플래시와 함께 큰 임팩트 + 종소리 화음 (그 역사를, 몸으로 기억하다)
  32–40s   몽타주: 120BPM 비트, 컷마다 화음 전환(Dm–B♭–F–C–Dm) + 아르페지오
  40–45.5s 배우 원음 대사 아래 아주 작은 패드
  45.5–52s 엔딩: 부드러운 임팩트 + F장조 패드, 글자가 뜰 때마다 맑은 플럭
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


# ── 편곡 ────────────────────────────────────────────
def build(path):
    n = int(R.DURATION * SR) + SR
    dry = np.zeros((2, n))
    send = np.zeros(n)

    def add(sig, t, g=1.0, pan=0.0, rev=0.0):
        i = int(round(t * SR))
        if i >= n or g == 0:
            return
        s = sig[:n - i] * g
        a = (pan + 1) * math.pi / 4
        dry[0, i:i + len(s)] += s * math.cos(a) * 1.414
        dry[1, i:i + len(s)] += s * math.sin(a) * 1.414
        send[i:i + len(s)] += s * rev

    shots = R.SHOTS
    turn_t = next(s[0] for s in shots if s[5]['kind'] == 'turn')
    mont_t = next(s[0] for s in shots if s[5]['kind'] == 'montage')
    voice_t = next(s[0] for s in shots if s[5]['kind'] == 'voice')
    cta_t = next(s[0] for s in shots if s[5]['kind'] == 'cta')

    # 드론: 처음부터 전환 직전까지, 점점 열리며 커짐 → 직전에 뚝 끊김(정적)
    dd = turn_t - .08
    dr = drone(dd)
    env = np.minimum(1, ts(dd) / 1.2) * (.55 + .45 * ts(dd) / dd)
    env[-int(.04 * SR):] *= np.linspace(1, 0, int(.04 * SR))
    add(dr * env / np.abs(dr).max(), 0, .32, rev=.15)

    # 훅: 심장박동 + 타자음 (render.py 의 타이핑 시각과 동일)
    hook = shots[0][5]
    for hb in (0.0, 1.1, 2.2):
        add(heartbeat(), hb, .9)
    for li, txt in enumerate((hook['l1'], hook['l2'])):
        for j, ch in enumerate(txt):
            add(key_click(), R.HOOK_D[li] + j / R.CPS, .28 if ch != ' ' else .12, pan=-.3 + .6 * j / len(txt), rev=.1)

    # 연표: 초침 + 컷 임팩트 + 숫자 굴림 틱
    t = 3.0
    while t < turn_t - .6:
        add(tick(2300 if int(t * 2) % 2 else 1700), t, .16, pan=.25 if int(t * 2) % 2 else -.25, rev=.05)
        t += .5
    for s0, s1, _, _, _, card in shots:
        if s0 >= turn_t:
            break
        if s0 > 0:
            add(whoosh(.35), s0 - .3, .22, pan=.4 if int(s0) % 2 else -.4)
            add(sub_hit(), s0, .75 if card['kind'] == 'date' else .9, rev=.25)
        if card['kind'] == 'date':
            digits = sum(ch.isdigit() for ch in card['date'])
            for j in range(10 + digits * 2):          # 숫자가 굴러가는 동안
                add(tick(2600 + 300 * (j % 3)), s0 + .12 + j * .045, .09 * (1 - j / (12 + digits * 2)), pan=-.5 + j * .05)
            add(pluck(note('D5'), .8), s0 + .75, .12, rev=.3)
        if card['kind'] == 'day':
            # 날짜가 굴러와 멈추는 순간 '딱' + 빨라지는 심장박동
            add(tick(3200), s0 + .9, .25, rev=.2)
            period = 1.0 - .1 * card['day']
            hb = s0 + .1
            while hb < s1 - .1:
                add(heartbeat(), hb, .7 + .08 * card['day'])
                hb += period
    # 10.26 → 큰 종 + 상승음 → 정적
    t26 = shots[9][0]
    add(bell(note('D3'), 3.5), t26, .45, rev=.4)
    add(riser(turn_t - .1 - (t26 + .6)), t26 + .6, .45, rev=.2)
    add(rev_swell(.6), turn_t - .65, .35)

    # 전환: 큰 임팩트 + 종 화음 + Dm 패드
    add(sub_hit(2.5, 140, 34, .9), turn_t, 1.1, rev=.5)
    add(filt(noise(1.5), 'low', 5000) * np.exp(-ts(1.5) * 4), turn_t, .25, rev=.6)
    for nm, dl in (('D4', 0), ('F4', .06), ('A4', .12), ('D5', .6)):
        add(bell(note(nm)), turn_t + dl, .28, pan=(-.3, .3, 0, .2)[('D4', 'F4', 'A4', 'D5').index(nm)], rev=.5)
    add(pad(mont_t - turn_t + .3, ['D3', 'A3', 'F4'], 1600, .6, .4), turn_t, .22, rev=.3)
    add(pluck(note('A4'), 1.5), turn_t + .6, .2, rev=.4)
    add(riser(.8), mont_t - .8, .25)

    # 몽타주: 120BPM, 컷마다 화음 전환 + 아르페지오 + 베이스
    chords = [['D4', 'F4', 'A4', 'D5'], ['Bb3', 'D4', 'F4', 'Bb4'], ['F4', 'A4', 'C5', 'F5'],
              ['C4', 'E4', 'G4', 'C5'], ['D4', 'F4', 'A4', 'D5']]
    bass = ['D2', 'Bb1', 'F2', 'C2', 'D2']
    mshots = [s for s in shots if s[5]['kind'] == 'montage']
    beat = .5
    for ci, (s0, s1, *_rest) in enumerate(mshots):
        ch = chords[ci]
        add(sub_hit(1.0, 110, 40, .6), s0, .55, rev=.2)
        if ci:
            add(whoosh(.3), s0 - .25, .2, pan=.5 if ci % 2 else -.5)
        add(pad(s1 - s0 + .2, ch[:3], 2200, .05, .2), s0, .16, rev=.3)
        nb = int(round((s1 - s0) / beat))
        for b in range(nb):
            bt = s0 + b * beat
            add(kick(), bt, .62)
            add(hat(), bt + beat / 2, .16, pan=.3)
            if (int(round((bt - mont_t) / beat))) % 2 == 1:
                add(clap(), bt, .4, rev=.3)
            add(pluck(note(bass[ci]), .45, .6), bt + beat / 2, .35)
        steps = int(round((s1 - s0) / (beat / 4)))
        for j in range(steps):
            idx = (0, 1, 2, 3, 2, 1, 2, 3)[j % 8]
            add(pluck(note(ch[idx]), .6, 1.4), s0 + j * beat / 4, .12, pan=(-.4, -.1, .2, .45)[idx], rev=.35)

    # 대사: 작은 패드만 (B♭ → F)
    add(pad(2.9, ['Bb2', 'F3', 'D4'], 900, 1.0, 1.2), voice_t, .1, rev=.4)
    add(pad(3.0, ['F2', 'C4', 'A4'], 900, 1.2, 1.2), voice_t + 2.6, .1, rev=.4)
    add(bell(note('F5'), 3), voice_t + .1, .08, rev=.5)

    # 엔딩: 부드러운 임팩트 + F장조 패드 + 글자 등장 플럭 + 반짝임
    add(sub_hit(2.2, 90, 36, .3), cta_t, .7, rev=.6)
    end_d = R.DURATION - cta_t
    add(pad(end_d, ['F3', 'C4', 'G4', 'A4'], 1300, 1.2, 1.6), cta_t, .2, rev=.4)
    D = R.CTA_D
    for nm, key in (('C5', 'label'), ('F5', 'title'), ('A5', 'l3'), ('C6', 'l4')):
        add(pluck(note(nm), 1.8, 1.2), cta_t + D[key], .2, rev=.5)
    add(bell(note('F6'), 3), cta_t + D['title'] + .3, .1, pan=.3, rev=.6)
    add(whoosh(.5), cta_t + D['rule'] - .15, .12)
    add(sweep_noise(.9, 3000, 12000, .3) * np.sin(np.pi * ts(.9) / .9) ** 2, cta_t + D['shine'], .08, rev=.5)
    for j, nm in enumerate(('F6', 'C7', 'A6', 'G6')):
        add(bell(note(nm), 2.5), cta_t + 3.0 + j * .45, .05, pan=(-.5, .5, -.2, .3)[j], rev=.7)

    # 리버브 + 마스터
    ir = reverb_ir()
    wet = np.stack([signal.fftconvolve(send, ir[c])[:n] for c in range(2)])
    mix = dry + wet * .35
    mix = filt(mix, 'high', 30)
    tail = int(1.2 * SR)
    end = int(R.DURATION * SR)
    mix = mix[:, :end]
    mix[:, -tail:] *= np.linspace(1, 0, tail) ** 1.5
    mix = np.tanh(mix / np.abs(mix).max() * 1.3) / np.tanh(1.3) * .89
    pcm = (mix.T * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'music.wav')
