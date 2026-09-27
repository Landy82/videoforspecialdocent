"""오리지널 BGM 합성기 — 샘플·외부 음원을 전혀 쓰지 않고 수식으로만 소리를 만든다(저작권 문제 없음).

25초 구성안에 맞춘 120BPM 트랙을 public/audio/bgm.wav 로 만든다.
  python3 scripts/make-bgm.py [--bpm 120] [--stop-at 16] [--stop-beats 2] [--out public/audio/bgm.wav]
BPM을 바꾸면 모든 섹션 경계가 마디 단위로 함께 움직인다(섹션은 '마디 번호'로 정의).
"""
import argparse, wave
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--bpm', type=float, default=120)
ap.add_argument('--duration', type=float, default=25)
ap.add_argument('--stop-bar', type=float, default=8, help='음악이 멈추는 마디(0부터). 120BPM에서 8마디 = 16초')
ap.add_argument('--stop-beats', type=float, default=2, help='멈추는 박 수')
ap.add_argument('--out', default='public/audio/bgm.wav')
a = ap.parse_args()

SR = 48000
BEAT = 60 / a.bpm
BAR = BEAT * 4
N = int(a.duration * SR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(1987)


def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N: return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * np.sqrt((1 - pan) / 2) * 1.414
    R[i:i + len(sig)] += sig * np.sqrt((1 + pan) / 2) * 1.414


def env(n, a_=0.002, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a_, 1e-4)) * np.exp(-t / d)


def lp(x, k):  # 한 극 저역통과
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc += k * (v - acc); y[i] = acc
    return y


def kick(g=1.0):
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 42 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(1.6 * np.sin(ph) * np.exp(-t * 7)) * g


def clap():
    n = int(0.3 * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    e = sum(np.exp(-np.clip(t - d, 0, None) * 60) * (t >= d) for d in (0, 0.011, 0.022)) * 0.4 + np.exp(-t * 14) * 0.6
    return (nz - lp(nz, 0.25)) * e * 0.5


def hat(open_=False):
    n = int((0.25 if open_ else 0.05) * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n); nz = nz - lp(nz, 0.5)
    return nz * np.exp(-t * (12 if open_ else 70)) * 0.18


def door_slam():
    """철문 닫히는 듯한 묵직한 타격: 저역 붐 + 금속성 공명 + 짧은 노이즈 어택"""
    n = int(2.2 * SR); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (38 + 60 * np.exp(-t * 18)) * t) * np.exp(-t * 2.2)
    metal = sum(np.sin(2 * np.pi * f * t + p) * np.exp(-t * dcy) for f, p, dcy in
                ((187, 0.3, 3.5), (263, 1.1, 4.2), (411, 2.0, 5.0), (587, 0.7, 6.5), (941, 1.9, 8.0))) * 0.09
    nz = rng.standard_normal(n); att = (nz - lp(nz, 0.1)) * np.exp(-t * 45) * 0.5
    return np.tanh(1.3 * (boom * 1.1 + metal + att))


def note_hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def bass(m, dur, g=0.5):
    n = int(dur * SR); t = np.arange(n) / SR; f = note_hz(m)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sign(np.sin(2 * np.pi * f * t))
    e = np.minimum(1, t / 0.005) * np.exp(-t * 3.0) * np.minimum(1, (dur - t) / 0.02)
    return lp(x, 0.12) * e * g


def pad(ms, dur, g=0.12):
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for m in ms:
        for det in (-0.08, 0.0, 0.08):
            f = note_hz(m) * 2 ** (det / 12)
            x += 2 * ((f * t + rng.random()) % 1) - 1  # 톱니파
    x = lp(x / len(ms), 0.035)
    e = np.minimum(1, t / 0.35) * np.minimum(1, (dur - t) / 0.3)
    return x * e * g


def pluck(m, g=0.12):
    n = int(0.4 * SR); t = np.arange(n) / SR; f = note_hz(m)
    x = np.sin(2 * np.pi * f * t) * 0.7 + np.sin(4 * np.pi * f * t + 0.5) * 0.3
    return x * np.exp(-t * 9) * np.minimum(1, t / 0.002) * g


def riser(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n); k = np.linspace(0.02, 0.6, n)
    y = np.empty(n); acc = 0.0
    for i in range(n):
        acc += k[i] * (nz[i] - acc); y[i] = nz[i] - acc
    return y * (t / dur) ** 2 * 0.25


def tick():
    n = int(0.03 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 180) * 0.12


# D단조: Dm – B♭ – F – C (i–VI–III–VII)
CHORDS = [(38, [62, 65, 69]), (34, [62, 65, 70]), (41, [60, 65, 69]), (36, [60, 64, 67])]
ARP = [0, 2, 1, 2, 0, 2, 1, 2]

bar_t = lambda b: b * BAR
stop0 = bar_t(a.stop_bar); stop1 = stop0 + a.stop_beats * BEAT
end_fade = a.duration - 0.5
n_bars = int(np.ceil(a.duration / BAR))

# 마디별 역할 (0부터): 0 훅, 1 반전, 2~6 몽타주(3번째 = 5·18은 절제), 7 가속, 8 정적→재개, 9~ 안내
ROLE = {0: 'hook', 1: 'reveal', 2: 'groove', 3: 'memorial', 4: 'groove', 5: 'groove', 6: 'groove', 7: 'rush', 8: 'restart'}

add(door_slam(), 0.0, 0.95)
for b in range(n_bars):
    t0 = bar_t(b); role = ROLE.get(b, 'cta')
    root, triad = CHORDS[b % 4]
    if role == 'hook':
        for k in range(1, 4): add(tick(), t0 + k * BEAT, 0.8)
        continue
    if role == 'reveal':
        add(pad(triad, BAR, 0.08), t0)
        add(riser(BAR), t0, 0.9)
        for k in range(4): add(kick(0.55), t0 + k * BEAT)
        continue
    # 코드 패드 (모든 이후 마디)
    add(pad(triad, BAR + 0.1, 0.13 if role != 'memorial' else 0.16), t0, pan=0)
    if role == 'memorial':  # 5·18: 드럼 빼고 패드와 느린 베이스만
        add(bass(root, BAR * 0.95, 0.4), t0)
        for k in range(0, 8, 2): add(pluck(triad[ARP[k]] + 12, 0.07), t0 + k * BEAT / 2, pan=0.3)
        continue
    # 베이스: 8분음표 펄스
    for k in range(8):
        add(bass(root, BEAT / 2 * 0.9, 0.42 if k % 2 == 0 else 0.3), t0 + k * BEAT / 2)
    # 아르페지오
    for k in range(8):
        add(pluck(triad[ARP[k]] + 12, 0.09), t0 + k * BEAT / 2, pan=(-0.35 if k % 2 else 0.35))
    # 드럼
    for k in range(4):
        add(kick(), t0 + k * BEAT, 0.85)
        if k in (1, 3): add(clap(), t0 + k * BEAT, 0.8, pan=0.05)
    steps = 16 if role == 'rush' else 8
    for k in range(steps):
        add(hat(open_=(steps == 8 and k % 2 == 1)), t0 + k * BAR / steps, 0.9 if k % 2 else 0.6, pan=0.25)
    if role == 'rush':
        for k in range(8): add(clap(), t0 + BAR / 2 + k * BAR / 16, 0.15 + 0.07 * k)
        add(riser(BAR), t0, 0.7)

# 정적: stop0~stop1 사이를 완전히 무음으로 (앞뒤 5ms 페이드)
f = int(0.005 * SR)
i0, i1 = int(stop0 * SR), int(stop1 * SR)
for ch in (L, R):
    ch[i0 - f:i0] *= np.linspace(1, 0, f)
    ch[i0:i1] = 0
    ch[i1:i1 + f] *= np.linspace(0, 1, f)
# 재개 순간 강조 타격
add(kick(1.0), stop1, 0.9); add(door_slam()[: int(0.8 * SR)] * np.linspace(1, 0, int(0.8 * SR)), stop1, 0.35)
# 루프 연결: 24.5초부터 무음으로 페이드
i_f, i_e = int(end_fade * SR), N
for ch in (L, R):
    ch[i_f:i_e] *= np.linspace(1, 0, i_e - i_f) ** 2

mix = np.stack([L, R], 1)
mix = np.tanh(mix * 0.9) * 0.85  # 부드러운 리미팅 (최종 음량 정규화는 렌더 후 -14 LUFS로)
mix /= np.max(np.abs(mix)) / 0.89
pcm = (mix * 32767).astype('<i2')
import os; os.makedirs(os.path.dirname(a.out), exist_ok=True)
with wave.open(a.out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print(f'{a.out}: {a.duration}s @ {a.bpm}BPM, 정적 {stop0:.2f}~{stop1:.2f}s')
