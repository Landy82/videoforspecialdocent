"""부마 숏츠 v1.2 배경음악 — 직접 작곡한 악보를 오픈 사운드폰트(GeneralUser GS, 상업 이용 자유)로 연주
96BPM · D단조 → F장조. 1마디 = 2.5초, 영상의 모든 컷이 마디(또는 2박) 위에 떨어지도록 render.py 와 같은 격자를 쓴다.

  마디 0       훅        피아노 모티프(A–D–E) 위로 첼로 지속음
  마디 1–3     배경      피아노 8분 오스티나토, 첼로·콘트라베이스, 팀파니      Dm | B♭ | A
  마디 4–8     5일       16분 현 오스티나토 + 타이코, 매일 한 겹씩 쌓임      Dm | B♭ | Gm | E♭ | A
  마디 9       10.26     갑자기 비워짐: 낮은 현 + 피아노 한 음
  마디 10      빌드업    트레몰로 현·합창·팀파니 롤 크레셴도, 리버스 심벌 → 직전 16분 쉼
  마디 11      전환      F장조로 터짐 (그 역사를, 몸으로 기억하다)
  마디 12–14½  몽타주    2박마다 화음 전환(B♭ F C Dm C), 북·현 8분, 피아노 선율
  마디 14½–17  대사      피아노·패드만 아주 작게
  마디 17–19   엔딩      B♭ | C | F, 글자가 뜰 때마다 피아노 음
"""
import os
import urllib.request
import numpy as np

SR = 48000
BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT
SF2_URL = 'https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/main/GeneralUser-GS.sf2'


def T(bar, beat=0.0):
    return bar * BAR + beat * BEAT


def sf2_path():
    p = os.environ.get('SF2') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'GeneralUser-GS.sf2')
    if not os.path.exists(p):
        urllib.request.urlretrieve(SF2_URL, p)
    return p


TRIAD = {'m': (0, 3, 7), 'M': (0, 4, 7)}
CH = {'Dm': (38, 'm'), 'Bb': (34, 'M'), 'Gm': (31, 'm'), 'A': (33, 'M'), 'Eb': (39, 'M'),
      'F': (29, 'M'), 'C': (36, 'M')}


def tones(name, octave=2):
    """화음 구성음 (근음이 대략 octave 옥타브)"""
    r, q = CH[name]
    r += 12 * (octave - 2)
    return [r + i for i in TRIAD[q]]


class Part:
    """한 악기 묶음(스템). programs: {채널: (뱅크, 프리셋, 드럼여부)}"""

    def __init__(self, programs):
        self.programs, self.ev = programs, []

    def note(self, ch, key, t, dur, vel):
        vel = int(max(1, min(127, vel)))
        self.ev.append((t, 1, 'on', ch, int(key), vel))
        self.ev.append((t + dur, 0, 'off', ch, int(key), 0))

    def cc(self, ch, ctrl, val, t):
        self.ev.append((t, 0, 'cc', ch, ctrl, int(max(0, min(127, val)))))

    def ramp(self, ch, ctrl, v0, v1, t0, t1, steps=40):
        for i in range(steps + 1):
            self.cc(ch, ctrl, v0 + (v1 - v0) * i / steps, t0 + (t1 - t0) * i / steps)

    def render(self, sf2, n):
        import tinysoundfont
        syn = tinysoundfont.Synth(samplerate=SR, gain=-6)
        sid = syn.sfload(sf2, max_voices=256)
        for ch, (bank, preset, drums) in self.programs.items():
            syn.program_select(ch, sid, bank, preset, is_drums=drums)
            syn.control_change(ch, 7, 110)
            syn.control_change(ch, 11, 127)
        out = np.zeros((n, 2), np.float32)
        pos = 0
        for t, _, kind, ch, a, b in sorted(self.ev, key=lambda e: (e[0], e[1])):
            i = min(n, int(t * SR))
            if i > pos:
                out[pos:i] = np.frombuffer(syn.generate(i - pos), np.float32).reshape(-1, 2)
                pos = i
            if kind == 'on':
                syn.noteon(ch, a, b)
            elif kind == 'off':
                syn.noteoff(ch, a)
            else:
                syn.control_change(ch, a, b)
        if pos < n:
            out[pos:] = np.frombuffer(syn.generate(n - pos), np.float32).reshape(-1, 2)
        return out


# 채널 배치
PIANO, SLOW, FAST, CELLO, BASS, TREM = 0, 1, 2, 3, 4, 5
TIMP, TAIKO, REVCYM, KIT, CHOIR, PAD = 6, 7, 8, 9, 10, 11
# GM 오케스트라 키트 음 번호
KICK, SNARE, CRASH, TOM_L, TOM_M, TOM_H, SUSCYM, GONG = 36, 38, 49, 45, 47, 50, 55, 52
# 금관 · 색채 악기 (v1.4~)
HORN, TPT, TBN, TUBA = 12, 13, 14, 15
GLOCK, HARP = 1, 2


def compose(duration, cta_beats=(0.5, 1.0, 2.0, 3.0, 4.0)):
    piano = Part({PIANO: (0, 0, False)})
    strings = Part({SLOW: (0, 49, False), FAST: (0, 48, False), CELLO: (0, 42, False),
                    BASS: (0, 43, False), TREM: (0, 44, False)})
    perc = Part({TIMP: (0, 47, False), TAIKO: (0, 116, False), REVCYM: (0, 119, False), KIT: (128, 48, True)})
    choir = Part({CHOIR: (0, 52, False), PAD: (0, 89, False)})
    brass = Part({HORN: (0, 60, False), TPT: (0, 56, False), TBN: (0, 57, False), TUBA: (0, 58, False)})
    color = Part({GLOCK: (0, 9, False), HARP: (0, 46, False)})

    # ── 마디 0: 훅 ──
    piano.note(PIANO, 38, 0, BAR, 62); piano.note(PIANO, 50, 0, BAR, 56)
    for bt, k in ((1, 69), (2, 74), (3, 76)):                     # A4 D5 E5 → (다음 마디 F5)
        piano.note(PIANO, k, T(0, bt), BEAT * 1.6, 60)
    strings.note(CELLO, 38, 0, BAR, 72); strings.note(BASS, 26, 0, BAR, 60)
    perc.note(TIMP, 38, 0, 1.5, 78)

    # ── 마디 1–3: 배경 (1972 / 1975 / 10.04) ──
    pat8 = [0, 2, 1, 2, 3, 2, 1, 2]
    melody = {1: [(0, 77, 2), (2, 76, 1), (3, 74, 1)], 2: [(0, 74, 2), (2, 72, 1), (3, 70, 1)], 3: [(0, 69, 2.5), (2.5, 73, 1.5)]}
    for bar, name in ((1, 'Dm'), (2, 'Bb'), (3, 'A')):
        ch = tones(name, 3)
        arp = [ch[0], ch[1], ch[2], ch[0] + 12]
        for e in range(8):
            piano.note(PIANO, arp[pat8[e]] + 12, T(bar, e / 2), BEAT * .55, 56 + (8 if e % 2 == 0 else 0))
        for bt, k, d in melody[bar]:
            piano.note(PIANO, k, T(bar, bt), BEAT * d, 66)
        strings.note(CELLO, tones(name, 2)[0], T(bar), BAR, 74)
        strings.note(BASS, tones(name, 2)[0] - 12, T(bar), BAR, 66)
        if bar >= 2:
            for k in tones(name, 3):
                strings.note(SLOW, k + 12, T(bar), BAR, 52 + 8 * (bar - 2))
        perc.note(TIMP, tones(name, 2)[0] + 12 if name == 'A' else tones(name, 2)[0], T(bar), 1.2, 84)
    for i in range(8):                                              # 마디 3 끝: 팀파니 롤 → 5일 구간
        perc.note(TIMP, 45, T(3, 2 + i / 4), .2, 50 + i * 8)

    # ── 마디 4–8: 1979.10.16–20, 매일 한 겹씩 ──
    days = ['Dm', 'Bb', 'Gm', 'Eb', 'A']
    hi = {6: [(0, 79, 2), (2, 77, 1), (3, 74, 1)], 7: [(0, 75, 1.5), (1.5, 79, .5), (2, 82, 2)], 8: [(0, 81, 3), (3, 85, 1)]}
    for d, name in enumerate(days):
        bar = 4 + d
        lift = d * 7
        ch3 = tones(name, 3)
        for s in range(16):                                          # 16분 현 오스티나토
            k = [ch3[0], ch3[2], ch3[0] + 12, ch3[2]][s % 4]
            strings.note(FAST, k, T(bar, s / 4), BEAT * .22, 62 + lift + (10 if s % 4 == 0 else 0))
        for k in ch3 + [ch3[1] + 12]:
            strings.note(SLOW, k + 12, T(bar), BAR, 62 + lift)
        strings.note(CELLO, tones(name, 2)[0], T(bar), BAR, 80 + lift / 2)
        strings.note(BASS, tones(name, 2)[0] - 12, T(bar), BAR, 74 + lift / 2)
        for bt in range(4):                                          # 피아노 옥타브 박
            piano.note(PIANO, tones(name, 2)[0], T(bar, bt), BEAT * .9, 66 + lift)
            piano.note(PIANO, tones(name, 2)[0] + 12, T(bar, bt), BEAT * .9, 60 + lift)
        for bt, k, du in hi.get(bar, []):
            piano.note(PIANO, k, T(bar, bt), BEAT * du, 84)
            piano.note(PIANO, k - 12, T(bar, bt), BEAT * du, 70)
        taiko = [0, 2] if d < 2 else [0, 1, 2, 3, 3.5]
        for bt in taiko:
            perc.note(TAIKO, 48, T(bar, bt), .5, 92 + lift if bt == 0 else 74 + lift)
        perc.note(TIMP, tones(name, 2)[0] + (12 if tones(name, 2)[0] < 36 else 0), T(bar), 1.2, 90 + lift / 2)
        perc.note(KIT, KICK, T(bar), .5, 90)
        if d >= 2:
            perc.note(KIT, CRASH, T(bar), 2.0, 70 + lift)
        if d >= 3:
            for k in ch3:
                choir.note(CHOIR, k + 12, T(bar), BAR, 70 + lift)
    for i, k in enumerate([TOM_H, TOM_H, TOM_M, TOM_M, TOM_L, TOM_L, TOM_L, TOM_L]):  # 마디 8 끝 필인
        perc.note(KIT, k, T(8, 2 + i / 4), .3, 80 + i * 5)

    # ── 마디 9: 10.26 — 비워짐 ──
    for k in tones('Bb', 3):
        strings.note(SLOW, k, T(9), BAR, 48)
    strings.note(CELLO, 34, T(9), BAR, 62); strings.note(BASS, 22, T(9), BAR, 58)
    piano.note(PIANO, 86, T(9), BEAT * 3, 70); piano.note(PIANO, 74, T(9), BEAT * 3, 56)
    piano.note(PIANO, 81, T(9, 2), BEAT * 2, 58)
    perc.note(TIMP, 34 + 12, T(9), 2.0, 70)

    # ── 마디 10: 빌드업 → 직전 16분 쉼 ──
    stop = T(11) - BEAT / 4
    for k in (45, 57, 64, 69, 73):
        strings.note(TREM, k, T(10), stop - T(10), 100)
    strings.ramp(TREM, 11, 25, 127, T(10), stop)
    for k in (57, 61, 64, 69):
        choir.note(CHOIR, k, T(10), stop - T(10), 100)
    choir.ramp(CHOIR, 11, 20, 120, T(10), stop)
    strings.note(CELLO, 33, T(10), stop - T(10), 90); strings.note(BASS, 21, T(10), stop - T(10), 90)
    for i in range(30):
        perc.note(TIMP, 33 + 12, T(10, i * 4 / 32 * 1.0) if i < 30 else stop, .12, 40 + i * 2.8)
    for i in range(8):
        perc.note(KIT, SNARE, T(10, 2 + i / 4 * .9), .1, 50 + i * 9)
    perc.note(REVCYM, 60, max(0, T(11) - 2.0), 2.0, 110)            # 길이는 render 단계에서 정렬
    for k in (33, 45):
        piano.note(PIANO, k, T(10), stop - T(10), 70)
    brass.note(TUBA, 33, T(10), stop - T(10), 110); brass.note(TBN, 45, T(10), stop - T(10), 110)
    brass.note(HORN, 57, T(10), stop - T(10), 110); brass.note(HORN, 64, T(10), stop - T(10), 110)
    for ch in (TUBA, TBN, HORN):
        brass.ramp(ch, 11, 20, 127, T(10), stop)

    # ── 마디 11: 전환 — F장조로 터짐 ──
    t11 = T(11)
    perc.note(KIT, CRASH, t11, 3.0, 120); perc.note(KIT, KICK, t11, .6, 120)
    perc.note(TAIKO, 45, t11, 1.0, 120); perc.note(TIMP, 41, t11, 2.0, 120)
    for k in (41, 48, 53, 57, 60, 65, 69):
        strings.note(SLOW, k, t11, BAR, 100)
    for k in (53, 57, 60, 65):
        choir.note(CHOIR, k + 12, t11, BAR, 95)
    choir.cc(CHOIR, 11, 120, t11)
    strings.note(CELLO, 41, t11, BAR, 100); strings.note(BASS, 29, t11, BAR, 100)
    piano.note(PIANO, 29, t11, BAR, 100); piano.note(PIANO, 41, t11, BAR, 95)
    for bt, k in ((1, 72), (2, 77), (3, 79)):                          # C5 F5 G5 → A5
        piano.note(PIANO, k, T(11, bt), BEAT * 1.2, 88); piano.note(PIANO, k - 12, T(11, bt), BEAT * 1.2, 70)
        brass.note(TPT, k, T(11, bt), BEAT * 1.05, 112)                 # 트럼펫 팡파르
    perc.note(KIT, GONG, t11, 4.0, 120)
    brass.note(TUBA, 29, t11, BAR, 115); brass.note(TBN, 41, t11, BAR, 112); brass.note(TBN, 48, t11, BAR, 108)
    for k in (57, 60, 65):
        brass.note(HORN, k, t11, BAR, 112)
    brass.note(TPT, 69, t11, BEAT * .95, 115)

    # ── 마디 12–14½: 몽타주 — 2박마다 화음 ──
    cuts = ['Bb', 'F', 'C', 'Dm', 'C']
    mel = [(81, 77), (84, 81), (79, 76), (77, 74), (76, 79)]
    for c, name in enumerate(cuts):
        t0 = T(12) + c * 2 * BEAT
        ch3 = tones(name, 3)
        for k in ch3 + [ch3[0] + 12]:
            strings.note(SLOW, k + 12, t0, 2 * BEAT, 92)
            choir.note(CHOIR, k + 12, t0, 2 * BEAT, 78)
        for e in range(4):                                            # 8분 현·베이스
            tt = t0 + e * BEAT / 2
            strings.note(FAST, [ch3[0], ch3[2], ch3[0] + 12, ch3[2]][e] + 12, tt, BEAT * .4, 92)
            strings.note(CELLO, tones(name, 2)[0], tt, BEAT * .4, 92)
            strings.note(BASS, tones(name, 2)[0] - 12, tt, BEAT * .4, 86)
        for i, k in enumerate(mel[c]):
            piano.note(PIANO, k, t0 + i * BEAT, BEAT * .95, 96)
            piano.note(PIANO, k - 12, t0 + i * BEAT, BEAT * .95, 80)
            brass.note(HORN, k - 12, t0 + i * BEAT, BEAT * .95, 108)      # 호른이 선율을 함께
        brass.note(TUBA, tones(name, 2)[0] - (12 if tones(name, 2)[0] > 35 else 0), t0, 2 * BEAT * .95, 100)
        brass.note(TBN, tones(name, 2)[0] + 12, t0, 2 * BEAT * .95, 96)
        for bt in (0, 1):
            perc.note(KIT, KICK, t0 + bt * BEAT, .4, 110)
            perc.note(TAIKO, 48, t0 + bt * BEAT, .5, 100 if bt == 0 else 84)
            perc.note(TAIKO, 52, t0 + bt * BEAT + BEAT / 2, .3, 70)
        perc.note(KIT, SNARE, t0 + BEAT, .2, 96)
        perc.note(KIT, CRASH, t0, 1.2, 100 if c == 0 else 76)
        perc.note(TIMP, tones(name, 2)[0] + 12 if tones(name, 2)[0] < 36 else tones(name, 2)[0], t0, .8, 96)

    # ── 마디 14½–17: 대사 아래 아주 작게 ──
    tv = T(14, 2)
    for i, k in enumerate((53, 57, 60, 65, 69, 72, 77)):                # 하프: F장조로 천천히 오름
        color.note(HARP, k, tv + i * BEAT / 3, 3.0, 62 + i * 3)
    for t0, du, name in ((tv, BAR, 'F'), (tv + BAR, BAR, 'Bb'), (tv + 2 * BAR, BAR / 2, 'C')):
        for k in tones(name, 3):
            piano.note(PIANO, k + 12, t0, du, 40)
            choir.note(PAD, k, t0, du, 50)
        piano.note(PIANO, tones(name, 2)[0], t0, du, 44)
        strings.note(CELLO, tones(name, 2)[0], t0, du, 40)

    # ── 마디 17–19: 엔딩 B♭ | C | F ──
    for bar, name in ((17, 'Bb'), (18, 'C'), (19, 'F')):
        last = name == 'F'
        du = duration - T(bar) if last else BAR
        for k in tones(name, 3) + [tones(name, 3)[0] + 12]:
            strings.note(SLOW, k + 12, T(bar), du, 70 + (bar - 17) * 10)
            choir.note(CHOIR, k + 12, T(bar), du, 60 + (bar - 17) * 10)
        strings.note(CELLO, tones(name, 2)[0], T(bar), du, 80)
        strings.note(BASS, tones(name, 2)[0] - 12, T(bar), du, 72)
        piano.note(PIANO, tones(name, 2)[0], T(bar), du, 70)
        for e in range(8 if not last else 4):                          # 위로 오르는 8분 아르페지오
            k = (tones(name, 4) + [tones(name, 4)[0] + 12])[e % 4] + (12 if e >= 4 else 0)
            piano.note(PIANO, k, T(bar, e / 2), BEAT * .9, 58 + e * 2)
    for bar, name in ((17, 'Bb'), (18, 'C'), (19, 'F')):
        du = duration - T(bar) if name == 'F' else BAR
        for k in tones(name, 3):
            brass.note(HORN, k + 12 if k < 55 else k, T(bar), du, 70 + (bar - 17) * 12)
        if name == 'F':
            brass.note(TUBA, 29, T(bar), du, 85); brass.note(TBN, 41, T(bar), du, 80)
    perc.note(KIT, SUSCYM, T(19) - 1.2, 2.5, 70)
    for k in (65, 69, 72, 77, 79, 81):                                  # 마지막 F add9
        piano.note(PIANO, k, T(19), duration - T(19), 72)
    t_end = T(17)
    for i, (bt, k) in enumerate(zip(cta_beats, (72, 77, 81, 84, 89))):  # 엔딩 글자마다 한 음
        piano.note(PIANO, k, t_end + bt * BEAT, BEAT * 2, 74 + i * 3)
        color.note(GLOCK, k + 12 if k < 79 else k, t_end + bt * BEAT, 1.5, 70)
    return {'piano': piano, 'strings': strings, 'perc': perc, 'choir': choir, 'brass': brass, 'color': color}


def render_stems(duration):
    sf2 = sf2_path()
    n = int(duration * SR) + SR
    parts = compose(duration)
    # 리버스 심벌은 정점이 마디 11 첫 박에 오도록 실제 길이를 재서 다시 배치
    probe = Part({REVCYM: (0, 119, False)})
    probe.note(REVCYM, 60, 0, 4.0, 110)
    a = np.abs(probe.render(sf2, int(4.5 * SR))).max(axis=1)
    peak = float(np.argmax(a)) / SR
    perc = parts['perc']
    perc.ev = [e for e in perc.ev if e[3] != REVCYM]
    perc.note(REVCYM, 60, max(0.0, T(11) - peak), peak + .05, 110)
    return {k: p.render(sf2, n) for k, p in parts.items()}


if __name__ == '__main__':
    import sys, wave
    st = render_stems(50.0)
    mix = sum(st.values())
    mix = mix / np.abs(mix).max() * .9
    with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'score.wav', 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
