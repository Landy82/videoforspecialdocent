"""실제 오케스트라 녹음 샘플(VSCO 2 Community Edition, CC0)로 score.py 악보를 연주하는 간단한 샘플러.

  VSCO=<VSCO-2-CE 폴더> python3 docu/orchestra.py out.wav
  · 음마다 가장 가까운 녹음 음을 골라 음높이만 살짝 옮기고(최대 몇 반음), 세기에 맞는 다이내믹 레이어와
    라운드로빈을 고른다. 지속음이 악보보다 짧으면 가운데 구간을 크로스페이드로 이어 붙인다.
  · score.py 의 (파트, 채널)을 실제 악기로 배치: 현은 음역에 따라 바이올린/비올라/첼로로 나눈다.
  · 필요한 폴더: VSCO_DIRS (git sparse-checkout 목록)
"""
import glob
import math
import os
import re
import sys
from math import gcd

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score as S

SR = S.SR
VSCO_URL = 'https://github.com/sgossner/VSCO-2-CE'
VSCO_DIRS = [
    'Keys/Upright Nr1/', 'Strings/Violin Section/susVib/', 'Strings/Violin Section/Spic/', 'Strings/Violin Section/Trem/',
    'Strings/Viola Section/susvib/', 'Strings/Viola Section/spic/', 'Strings/Viola Section/trem/',
    'Strings/Cello Section/susvib/', 'Strings/Cello Section/spic/', 'Strings/Cello Section/trem/',
    'Strings/Solo Contrabass/SusNV/', 'Strings/Harp/', 'Brass/F Horn/sus/', 'Brass/Trumpet/sus/',
    'Brass/Tenor Trombone/sus/', 'Brass/Tuba/sus/', 'Percussion/Glock/', 'Percussion/Timpani*', 'Percussion/BDrumNewhit*',
    'Percussion/Snare2-HitSN*', 'Percussion/Snare2-rollSN*', 'Percussion/cymbal-crash1*', 'Percussion/gongHit*', 'LICENSE',
]
NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
        'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
DYN = {'pp': 1, 'p': 2, 'mp': 3, 'mf': 4, 'f': 5, 'ff': 6, 'fff': 7}
_cache = {}


def vsco_root():
    root = os.environ.get('VSCO') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VSCO-2-CE')
    if not os.path.exists(os.path.join(root, 'Strings')):
        import subprocess
        subprocess.run(['git', 'clone', '-q', '--depth', '1', '--filter=blob:none', '--sparse', VSCO_URL, root], check=True)
        subprocess.run(['git', '-C', root, 'sparse-checkout', 'set', '--no-cone', *VSCO_DIRS], check=True)
    return root


def load(path):
    if path in _cache:
        return _cache[path]
    sr, x = wavfile.read(path)
    if x.dtype == np.int16:
        x = x.astype(np.float32) / 32768
    elif x.dtype == np.int32:
        x = x.astype(np.float32) / 2147483648
    elif x.dtype == np.uint8:
        x = (x.astype(np.float32) - 128) / 128
    else:
        x = x.astype(np.float32)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    x = x[:, :2]
    if sr != SR:
        g = gcd(sr, SR)
        x = resample_poly(x, SR // g, sr // g, axis=0).astype(np.float32)
    a = np.abs(x).max(1)
    i = int(np.argmax(a > a.max() * .004))          # 앞쪽 무음 제거
    x = x[max(0, i - 32):]
    _cache[path] = x
    return x


def extend(x, need):
    """지속음이 짧으면 가운데 구간을 크로스페이드로 반복"""
    L = len(x)
    a, b = int(L * .35), int(L * .85)
    seg = x[a:b]
    xf = max(64, min(int(.25 * SR), len(seg) // 3))
    out = x[:b].copy()
    fade = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
    while len(out) < need:
        tail = out[-xf:] * (1 - fade) + seg[:xf] * fade
        out = np.concatenate([out[:-xf], tail, seg[xf:]])
    return out


class Inst:
    def __init__(self, root, sub, pat='.', excl=None, pitched=True, sustain=True, release=.35, gain=1.0, pan=0.0,
                 keyfn=None, shift=True):
        files = [f for f in glob.glob(os.path.join(root, sub, '*.wav'))
                 if re.search(pat, os.path.basename(f)) and not (excl and re.search(excl, os.path.basename(f)))]
        if not files:
            raise FileNotFoundError(f'{sub} {pat}')
        self.z = {}
        for f in files:
            b = os.path.basename(f)
            m = re.search(r'_([A-G][#b]?)(-?\d)(?=[_.])', b)
            key = keyfn(b) if keyfn else ((int(m.group(2)) + 1) * 12 + NOTE[m.group(1)] if (m and pitched) else 0)
            v = re.search(r'_v(\d+)', b)
            d = re.search(r'_(pp|p|mp|mf|f|ff|fff)(?=[_.])', b)
            vel = int(v.group(1)) if v else (DYN[d.group(1)] if d else 1)
            self.z.setdefault(key, {}).setdefault(vel, []).append(f)
        self.keys = np.array(sorted(self.z))
        self.pitched, self.sustain, self.release, self.gain, self.pan, self.shift = pitched, sustain, release, gain, pan, shift
        self.rr = 0

    def render(self, key, vel, dur):
        k = int(self.keys[np.argmin(np.abs(self.keys - key))]) if self.pitched else int(self.keys[0])
        layers = sorted(self.z[k])
        li = min(len(layers) - 1, int(vel / 128 * len(layers)))
        paths = sorted(self.z[k][layers[li]])
        self.rr += 1
        x = load(paths[self.rr % len(paths)])
        if self.pitched and self.shift and key != k:                  # 음높이 옮기기
            r = 2 ** ((key - k) / 12)
            n = int(len(x) / r)
            t = np.arange(n) * r
            x = np.stack([np.interp(t, np.arange(len(x)), x[:, c]) for c in (0, 1)], 1).astype(np.float32)
        if self.sustain:
            need = int((dur + self.release) * SR)
            if len(x) < need:
                x = extend(x, need)
            x = x[:need].copy()
            rs = int(dur * SR)
            if rs < len(x):
                x[rs:] *= (np.linspace(1, 0, len(x) - rs, dtype=np.float32) ** 2)[:, None]
        else:                                                          # 타악·피아노·하프: 자연 감쇠, 단 너무 길면 자름
            x = x[:int(min(len(x) / SR, max(dur + self.release, .2) if self.release else 8.0) * SR)].copy()
            if self.release:
                fl = min(len(x), int(.25 * SR))
                x[-fl:] *= np.linspace(1, 0, fl, dtype=np.float32)[:, None]
        a = (self.pan + 1) * math.pi / 4
        g = self.gain * (.4 + .6 * vel / 127)
        x[:, 0] *= g * math.cos(a) * 1.414
        x[:, 1] *= g * math.sin(a) * 1.414
        return x


def build_insts(root):
    I = {}
    def add(name, *a, **k):
        I[name] = Inst(root, *a, **k)
    add('piano', 'Keys/Upright Nr1', r'^UR1_', sustain=False, release=.5, gain=1.0)
    add('vln_sus', 'Strings/Violin Section/susVib', gain=.8, pan=-.35)
    add('vln_spic', 'Strings/Violin Section/Spic', sustain=False, release=0, gain=.85, pan=-.35)
    add('vln_trem', 'Strings/Violin Section/Trem', gain=.8, pan=-.35)
    add('vla_sus', 'Strings/Viola Section/susvib', gain=.8, pan=.1)
    add('vla_spic', 'Strings/Viola Section/spic', sustain=False, release=0, gain=.85, pan=.1)
    add('vla_trem', 'Strings/Viola Section/trem', gain=.8, pan=.1)
    add('vc_sus', 'Strings/Cello Section/susvib', gain=.85, pan=.3)
    add('vc_spic', 'Strings/Cello Section/spic', sustain=False, release=0, gain=.9, pan=.3)
    add('vc_trem', 'Strings/Cello Section/trem', gain=.85, pan=.3)
    add('cb_sus', 'Strings/Solo Contrabass/SusNV', gain=1.0, pan=.4)
    add('harp', 'Strings/Harp', sustain=False, release=0, gain=.9, pan=-.3)
    add('horn', 'Brass/F Horn/sus', gain=.75, pan=-.2)
    add('tpt', 'Brass/Trumpet/sus', gain=.6, pan=.05)
    add('tbn', 'Brass/Tenor Trombone/sus', gain=.65, pan=.25)
    add('tuba', 'Brass/Tuba/sus', r'_Mid', gain=.75, pan=.35)
    add('glock', 'Percussion/Glock', sustain=False, release=0, gain=.45, pan=.3)
    # 팀파니 북 5개(1=가장 낮음으로 가정): 악보 음에 가장 가까운 북을 고르고 음높이는 옮기지 않는다
    add('timp', 'Percussion/Timpani', r'_Hit_', sustain=False, release=0, gain=1.0, pan=-.05, shift=False,
        keyfn=lambda b: 31 + 4 * int(re.search(r'Timpani(\d)', b).group(1)))
    add('bdrum', 'Percussion', r'^BDrumNewhit', pitched=False, sustain=False, release=0, gain=1.0)
    add('snare', 'Percussion', r'^Snare2-HitSN', pitched=False, sustain=False, release=0, gain=.6, pan=.1)
    add('crash', 'Percussion', r'^cymbal-crash1_', pitched=False, sustain=False, release=0, gain=.6, pan=.15)
    add('gong', 'Percussion', r'^gongHit_', pitched=False, sustain=False, release=0, gain=.8, pan=-.1)
    return I


def route(part, ch, key):
    """score.py 의 (파트, 채널, 음) → VSCO 악기"""
    if part == 'piano':
        return 'piano'
    if part == 'strings':
        if ch == S.SLOW:
            return 'vln_sus' if key >= 67 else ('vla_sus' if key >= 55 else 'vc_sus')
        if ch == S.FAST:
            return 'vln_spic' if key >= 60 else ('vla_spic' if key >= 50 else 'vc_spic')
        if ch == S.TREM:
            return 'vln_trem' if key >= 64 else ('vla_trem' if key >= 55 else 'vc_trem')
        return {S.CELLO: 'vc_sus', S.BASS: 'cb_sus'}[ch]
    if part == 'perc':
        if ch == S.TIMP:
            return 'timp'
        if ch == S.TAIKO:
            return 'bdrum'
        if ch == S.REVCYM:
            return 'revcrash'
        return {S.KICK: 'bdrum', S.SNARE: 'snare', S.CRASH: 'crash', S.SUSCYM: 'crash', S.GONG: 'gong'}.get(key, 'timp')
    if part == 'choir':
        if ch == S.CHOIR:
            return 'tpt' if key >= 77 else 'horn'
        return 'vln_sus' if key >= 60 else 'vla_sus'
    if part == 'brass':
        return {S.HORN: 'horn', S.TPT: 'tpt', S.TBN: 'tbn', S.TUBA: 'tuba'}[ch]
    if part == 'color':
        return {S.GLOCK: 'glock', S.HARP: 'harp'}[ch]
    raise KeyError((part, ch))


def render_stems(duration):
    root = vsco_root()
    I = build_insts(root)
    parts = S.compose(duration)
    n = int(duration * SR) + SR
    stems = {}
    timp_roll_spans = []
    for pname, part in parts.items():
        out = np.zeros((n, 2), np.float32)
        # 채널별 표현(CC11) 곡선
        expr = {}
        for t, _, kind, ch, a, b in part.ev:
            if kind == 'cc' and a == 11:
                expr.setdefault(ch, []).append((t, b / 127))
        for ch in expr:
            expr[ch].sort()
        ons = {}
        for t, _, kind, ch, key, vel in sorted(part.ev, key=lambda e: (e[0], e[1])):
            if kind == 'on':
                ons.setdefault((ch, key), []).append((t, vel))
            elif kind == 'off' and ons.get((ch, key)):
                t0, vel = ons[(ch, key)].pop(0)
                dur = max(.05, t - t0)
                name = route(pname, ch, key)
                if name == 'revcrash':
                    x = load(sorted(I['crash'].z[0][max(I['crash'].z[0])])[0])[::-1].copy() * .7
                    x = x[-int(min(len(x) / SR, dur) * SR):]
                elif pname == 'perc' and ch == S.TIMP and dur < .15 and vel < 120:
                    timp_roll_spans.append(t0)
                    x = I['timp'].render(key, vel, dur) * .55          # 롤의 낱타는 작게
                else:
                    x = I[name].render(key, vel, dur)
                i = int(t0 * SR)
                if i >= n:
                    continue
                x = x[:n - i]
                if ch in expr:
                    ts, vs = zip(*expr[ch])
                    tt = t0 + np.arange(len(x)) / SR
                    x = x * (np.interp(tt, ts, vs) ** 1.5)[:, None].astype(np.float32)
                out[i:i + len(x)] += x
        stems[pname] = out
    return stems


if __name__ == '__main__':
    import wave
    st = render_stems(50.0)
    mix = sum(st.values())
    mix = mix / np.abs(mix).max() * .9
    with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'orch.wav', 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
