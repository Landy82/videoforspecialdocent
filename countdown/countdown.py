"""특별도슨트 '세 칸 카운트다운' 홍보 숏츠 (30초, 1080×1920 30fps) — 마지막 3회 공연
- 화면을 세 칸으로 나눠 서로 다른 배우를 동시에 보여 주고, 각 칸이 마지막 3회(11.27 금 · 28 토 · 29 일)가 된다.
  칸이 하나씩 열려 전체 화면이 되고, 끝에서 3 → 2 → 1로 줄어든다. 실제 공연 영상만 쓴다(AI 생성 없음).
- 음악 없음(무음 트랙). 96BPM 격자(1박 0.625초, 30초 = 48박)에 컷과 글자를 맞춰 두어 나중에 음악을 얹기 쉽다.
  python3 countdown/countdown.py <영상 폴더(px_*.mp4)> out.mp4
"""
import math
import os
import subprocess
import sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'docu'))
import render as D                     # docu/render.py: 글자·이징·영상 처리 도구

W, H, FPS = D.W, D.H, D.FPS
DURATION = 30.0
BEAT = .625                            # 96BPM
L, R, TOP = D.SAFE_L, D.SAFE_R, D.SAFE_T
CX = (L + R) / 2                       # 오른쪽 버튼을 피한 안전영역 가운데
ACC, ACC_T, WHITE = D.ACCENT, D.ACCENT_T, D.WHITE
FB, FS, FM = D.F_HEAD, D.F_SANS, D.F_SANS_M     # Pretendard Bold / SemiBold / Medium
SW = W // 3                            # 칸 너비 360


def T(b):
    return b * BEAT


# ── 구간 (박) ──
HOOK, OPEN, PANELS, COUNT, CTA = (0, 4), (4, 12), (12, 30), (30, 40), (40, 48)
PANEL_BEATS = 6

# ── 영상: (소스, 소스 시작초, 칸에서 보일 가로 중심 0~1) — 칸마다 다른 배우 ──
HOOK_SRC = ('spot', 40.0)
STRIPS_A = [('woman', 52.0, .50), ('spot', 100.0, .50), ('draw', 12.0, .56)]     # 열림·펼침 (같은 영상이 이어짐)
STRIPS_B = [('final', 8.0, .30), ('sign', 28.0, .50), ('draw', 57.0, .38)]      # 카운트다운
DATES = [('27', '금'), ('28', '토'), ('29', '일')]
COPY = [('춤과 연기로', '만나는 전시 해설'),
        ('수어까지 함께하는', '모두의 무대'),
        ('영상과 몸짓으로 만나는', '민주화운동의 순간들')]


# ── 영상 읽기: 여러 소스를 동시에 열어 두고, 앞으로 갈 때는 건너뛰기(grab)로 빠르게 ──
class Reader:
    def __init__(self, root):
        self.root, self.caps = root, {}

    def frame(self, key, idx):
        fn, fps = D.SRC[key]
        c = self.caps.get(key)
        if c is None:
            c = self.caps[key] = [cv2.VideoCapture(os.path.join(self.root, fn)), -1, None]
        cap, last, cache = c
        if idx == last and cache is not None:
            return cache
        if idx < last or idx - last > 45:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        else:
            for _ in range(idx - last - 1):
                cap.grab()
        ok, f = cap.read()
        if not ok:
            f = np.zeros((H, W, 3), np.uint8)
        elif f.shape[:2] != (H, W):
            f = cv2.resize(f, (W, H))
        c[1], c[2] = idx, f
        return f


_RD, _ROOT = None, None


def clip(key, st, lt, zoom=1.0):
    fps = D.SRC[key][1]
    f = _RD.frame(key, int(round((st + lt) * fps)))[..., ::-1]      # 속도 1 (60fps 변환본은 2장씩 건너뜀)
    return D.grade(np.ascontiguousarray(f), zoom)


def put(canvas, g, cx, x, w, dy=0, k=1.0):
    """g의 가로 중심 cx 둘레 w픽셀을 canvas의 x 위치에 붙인다 (dy만큼 세로로 밀어서)"""
    w = int(round(w))
    x = int(round(x))
    x0 = int(round(min(max(cx * W - w / 2, 0), W - w)))
    part = g[:, x0:x0 + w]
    dy = int(round(dy))
    s0, s1 = max(0, -dy), min(H, H - dy)
    if s1 <= s0 or w <= 0:
        return
    canvas[s0 + dy:s1 + dy, x:x + w] = part[s0:s1] * k


# ── 글자 도구 ──
def fit(txt, path, size, maxw):
    w = D.line_width(txt, path, size)
    return int(size * maxw / w) if w > maxw else size


def spans(c, parts, path, size, x, y, lt, start, align='left', stagger=.03, style='mask', out=None, dur=.45):
    """여러 색 조각을 한 줄로 이어 쓴다. parts=[(글자, 색)]"""
    total = sum(D.line_width(t, path, size) for t, _ in parts)
    if align == 'center':
        x -= total / 2
    n = 0
    for t, col in parts:
        D.kinetic(c, t, path, size, x, y, lt, start + n * stagger, fill=col, stagger=stagger, style=style, out=out, dur=dur)
        x += D.line_width(t, path, size)
        n += len(t)


def chip(c, txt, x, y, lt, start, size=32, out=None):
    w = D.line_width(txt, FS, size, 3) + 40
    a = 1 - D.ease((lt - out) / .3) if out is not None else 1.0
    if a > 0:
        D.bar(c, x, y, w * D.ease((lt - start) / .3), size + 26, ACC, a)
    D.kinetic(c, txt, FS, size, x + 20, y + 10, lt, start + .08, shadow=False, track=3, stagger=.012, out=out)


def date_label(c, k, x_slot, lt, start, y=1250, out=None):
    num, day = DATES[k]
    wn = D.line_width(num, FB, 120)
    blk = wn + 14 + D.line_width(day, FS, 56)
    x = min(x_slot + 36, R - blk)
    D.kinetic(c, num, FB, 120, x, y, lt, start, stagger=.05, out=out)
    D.kinetic(c, day, FS, 56, x + wn + 14, y + 52, lt, start + .1, fill=ACC_T, out=out)
    D.kinetic(c, '오후 3시', FM, 32, x + 4, y + 150, lt, start + .18, fill=(220, 218, 232), stagger=.015, out=out)


# ── 1. 훅: 영상이 비치는 거대한 '3' ──
@lru_cache(maxsize=1)
def three_mask():
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    f = ImageFont.truetype(FB, 1180)
    d.text((W / 2, 760), '3', font=f, fill=255, anchor='mm')
    a = np.asarray(m, np.float32)[..., None] / 255
    edge = np.clip(cv2.dilate(a[..., 0], np.ones((9, 9), np.uint8)) - a[..., 0], 0, 1)[..., None]
    return a, edge


def hook_frame(t):
    lt = t - T(HOOK[0])
    a, edge = three_mask()
    s = 1.1 - .1 * D.ease(lt / .6)
    M = cv2.getRotationMatrix2D((W / 2, 760), 0, s)
    a = cv2.warpAffine(a[..., 0], M, (W, H))[..., None]
    edge = cv2.warpAffine(edge[..., 0], M, (W, H))[..., None]
    g = clip(*HOOK_SRC, lt, 1.0 + .04 * lt)
    fade = D.ease(lt / .35)
    tint = g * .85 + D._ACC * .25
    base = D._GLOW * D._ACC * .25
    return np.clip(base * (1 - a) + tint * a * fade + edge * np.array(ACC_T, np.float32) / 255 * .8 * fade, 0, 1)


def hook_text(c, lt, dur):
    out = dur - .3
    D.kinetic(c, '민주화운동기념관 특별도슨트', FM, 40, CX, 1330, lt, T(1), fill=(225, 223, 238), align='center', stagger=.015, out=out, track=2)
    size = fit('마지막 3번의 공연', FB, 104, 860)
    spans(c, [('마지막 ', WHITE), ('3번', ACC_T), ('의 공연', WHITE)], FB, size, CX, 1395, lt, T(2), align='center', out=out)


# ── 2~3. 세 칸이 열리고, 하나씩 전체 화면으로 펼쳐짐 ──
def strips_open(t):
    """구간 2: 칸이 위·아래에서 번갈아 미끄러져 들어온다"""
    lt = t - T(OPEN[0])
    cv = np.zeros((H, W, 3), np.float32)
    for k, (key, st, cx) in enumerate(STRIPS_A):
        p = D.ease_io((lt - k * BEAT) / .5)
        if p <= 0:
            continue
        g = clip(key, st, t - T(OPEN[0]))
        put(cv, g, cx, k * SW, SW, dy=(1 - p) * H * (-1 if k % 2 == 0 else 1))
    return cv


def panel_frame(t):
    """구간 3: 칸 k가 자기 자리에서 전체 화면으로 넓어진다 (앞 칸 화면 위로)"""
    lt = t - T(PANELS[0])
    k = min(2, int(lt / T(PANEL_BEATS)))
    plt = lt - k * T(PANEL_BEATS)
    e = D.ease_io(plt / .55)
    if e >= 1:
        cv = np.zeros((H, W, 3), np.float32)
    elif k == 0:
        cv = strips_open(t)                     # 첫 칸은 세 칸 화면 위에서 펼쳐짐
    else:
        key, st, _ = STRIPS_A[k - 1]
        cv = clip(key, st, t - T(OPEN[0]), 1.0 + .03 * T(PANEL_BEATS))   # 앞 칸이 다 펼쳐진 화면
    key, st, cx = STRIPS_A[k]
    g = clip(key, st, t - T(OPEN[0]), 1.0 + .03 * plt)
    w = SW + (W - SW) * e
    x = k * SW * (1 - e)
    put(cv, g, cx + (.5 - cx) * e, x, w)
    return cv, k, plt, e


# ── 4. 카운트다운 3 → 2 → 1 ──
def count_frame(t):
    lt = t - T(COUNT[0])
    cv = np.zeros((H, W, 3), np.float32)
    end = 1 - D.ease((lt - T(8)) / T(2))                 # 마지막 2박: 어둠으로
    for k, (key, st, cx) in enumerate(STRIPS_B):
        p = D.ease_io((lt - k * .08) / .35)
        if p <= 0:
            continue
        g = clip(key, st, lt)
        on = 2 + 2 * k                                    # 이 칸의 숫자가 뜨는 박
        lit = 1.0 if lt < T(on + 2) or k == 2 else .38   # 다음 숫자가 뜨면 어두워짐
        pulse = 1 + .18 * math.exp(-max(0, lt - T(on)) * 6) * (lt >= T(on))
        put(cv, g, cx, k * SW, SW, dy=(1 - p) * H * (-1 if k % 2 == 0 else 1), k=lit * pulse * end)
    return cv


def count_text(c, lt, dur):
    for k in range(3):
        on = T(2 + 2 * k)
        sc = k * SW + SW / 2
        D.kinetic(c, str(3 - k), FB, 300, sc, 600, lt, on, fill=ACC_T, align='center', style='pop', dur=.35, out=T(8))
        num, day = DATES[k]
        lab = f'{num} {day}'
        x = min(sc, R - D.line_width(lab, FS, 52) / 2 - 6)
        D.kinetic(c, lab, FS, 52, x, 1000, lt, on + .1, align='center', stagger=.03, out=T(8))
    txt = '11.29 일 · 마지막 공연'                         # '1'이 뜬 다음 박: 가운데 보라 띠
    w = D.line_width(txt, FB, 52) + 56
    u = D.ease_io((lt - T(7)) / .3) * (1 - D.ease((lt - T(8)) / .3))
    if u > 0:
        D.bar(c, CX - w / 2 * u, 1160, w * u, 84, ACC)
    D.kinetic(c, txt, FB, 52, CX, 1173, lt, T(7) + .1, align='center', stagger=.02, out=T(8), shadow=False)


# ── 5. 초대 ──
_PART = np.random.default_rng(1127).random((70, 5))


def cta(c, lt):
    d = ImageDraw.Draw(c)
    for px, py, sp, sz, ph in _PART:
        y = (py * H - lt * (18 + 45 * sp)) % H
        a = (.2 + .3 * (.5 + .5 * math.sin(lt * (1 + 2 * sp) + ph * 6.28))) * D.ease(lt / .8)
        r = 1 + 2.4 * sz
        d.ellipse([px * W - r, y - r, px * W + r, y + r], fill=(200, 192, 245, int(255 * a * .55)))
    b = [x * BEAT for x in range(8)]
    D.kinetic(c, '민주화운동기념관 특별도슨트', FM, 40, CX, 590, lt, b[0], align='center', stagger=.015, track=2)
    size = fit('마지막 3번의 공연', FB, 108, 860)
    D.kinetic(c, '마지막 3번의 공연', FB, size, CX, 660, lt, b[1], fill=ACC_T, align='center', style='pop', stagger=.04, dur=.4)
    u = D.ease_io((lt - b[2]) / .45)
    D.bar(c, CX - 70 * u, 820, 140 * u, 5, ACC_T)
    D.kinetic(c, '11.27 금 · 28 토 · 29 일', FB, 64, CX, 860, lt, b[3], align='center', stagger=.025)
    D.kinetic(c, '오후 3시 · 무료', FM, 48, CX, 955, lt, b[4], align='center', stagger=.025)
    D.kinetic(c, 'M1 B1 상설전시실', FM, 36, CX, 1035, lt, b[5], fill=(200, 196, 218), align='center', stagger=.02)
    D.kinetic(c, '문의 02-6440-8982', FM, 32, CX, 1090, lt, b[6], fill=(170, 166, 190), align='center', stagger=.02)


# ── 프레임 ──
def section(t):
    for name, (a, b) in (('hook', HOOK), ('open', OPEN), ('panels', PANELS), ('count', COUNT), ('cta', CTA)):
        if T(a) <= t < T(b):
            return name
    return 'cta'


def dividers(cv, a):
    if a > 0:
        for x in (SW, 2 * SW):
            cv[:, x - 3:x + 3] *= 1 - a


def render_frame(i):
    global _RD
    if _RD is None:
        _RD = Reader(_ROOT)
    t = i / FPS
    sec = section(t)
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if sec == 'hook':
        g = hook_frame(t)
        hook_text(c, t - T(HOOK[0]), T(HOOK[1] - HOOK[0]))
    elif sec == 'open':
        lt = t - T(OPEN[0])
        g = strips_open(t)
        dividers(g, 1.0)
        g = D.scrim(g, top=.6, bottom=.7)
        out = T(OPEN[1] - OPEN[0]) - .3
        chip(c, '특별도슨트 마지막 3회', L + 20, TOP, lt, .2, out=out)
        size = fit('11월의 마지막 주말', FB, 76, 860)
        D.kinetic(c, '11월의 마지막 주말', FB, size, L + 20, TOP + 90, lt, .45, stagger=.03, out=out)
        for k in range(3):
            date_label(c, k, k * SW, lt, k * BEAT + .35)
    elif sec == 'panels':
        g, k, plt, e = panel_frame(t)
        if k == 0:
            dividers(g, 1 - e)
        g = D.scrim(g, top=.55, bottom=.82)
        out = T(PANEL_BEATS) - .3 if k < 2 else T(PANEL_BEATS) - .25
        num, day = DATES[k]
        chip(c, f'11.{num} {day} · 오후 3시', L + 20, TOP, plt, .35, out=out)
        a1, a2 = COPY[k]
        s2 = fit(a2, FB, 96, 860)
        D.kinetic(c, a1, FS, 64, L + 20, 1170, plt, .45, stagger=.025, out=out)
        D.kinetic(c, a2, FB, s2, L + 20, 1265, plt, .45 + BEAT / 2, fill=ACC_T, stagger=.03, out=out)
        if k == 0 and plt < .6:                 # 펼쳐지기 시작하면 세 칸의 날짜 표시가 위로 빠지며 사라짐
            for j in range(3):
                date_label(c, j, j * SW, 99 + plt, 0, out=99)
    elif sec == 'count':
        lt = t - T(COUNT[0])
        g = count_frame(t)
        dividers(g, 1.0)
        g = D.scrim(g, top=.35, bottom=.55) * .8
        count_text(c, lt, T(COUNT[1] - COUNT[0]))
    else:
        lt = t - T(CTA[0])
        g = np.broadcast_to(D._GLOW * D._ACC * ((.16 + .04 * math.sin(lt * 2.2)) * D.ease((lt - .2) / .8)), (H, W, 3)).astype(np.float32)
        g = g * (1 - D.ease((t - (DURATION - .5)) / .5))
        cta(c, lt)
    if sec != 'cta':
        g = np.clip(g + cv2.resize(D._GRAIN[i % 4], (W, H))[..., None], 0, 1)
    base = Image.fromarray((np.clip(g, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
    if sec == 'cta' and t > DURATION - .5:
        c = D.with_alpha(c, 1 - D.ease((t - (DURATION - .5)) / .5))
    base.alpha_composite(c)
    return np.array(base.convert('RGB')).tobytes()


def main(root, out, workers=int(os.environ.get('WORKERS', max(1, (os.cpu_count() or 2) - 2)))):
    global _ROOT
    _ROOT = root
    tmp = out + '.video.mp4'
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-maxrate', '10M', '-bufsize', '20M', '-g', '60',
                          '-profile:v', 'high', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    n = int(DURATION * FPS)
    from multiprocessing import Pool
    CH = 20
    step = workers * CH
    with Pool(workers, maxtasksperchild=4) as pool:
        for b in range(0, n, step):
            for fr in pool.map(render_frame, range(b, min(n, b + step)), chunksize=CH):
                p.stdin.write(fr)
            print('frame', min(n, b + step), '/', n, flush=True)
    p.stdin.close(); p.wait()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
                    '-map', '0:v', '-map', '1:a', '-t', str(DURATION), '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k',
                    '-movflags', '+faststart', out], check=True)
    os.remove(tmp)
    print('done', out)


def stills(root, out, times):
    """디자인 시안: 지정 시각 프레임을 한 장에 모은다"""
    global _ROOT
    _ROOT = root
    fs = [Image.frombytes('RGB', (W, H), render_frame(int(round(t * FPS)))).resize((360, 640)) for t in times]
    sheet = Image.new('RGB', (360 * len(fs), 640))
    for k, f in enumerate(fs):
        sheet.paste(f, (360 * k, 0))
    sheet.save(out, quality=82)


if __name__ == '__main__':
    if sys.argv[1] == '--stills':
        stills(sys.argv[2], sys.argv[3], [float(x) for x in sys.argv[4:]])
    else:
        main(sys.argv[1], sys.argv[2])
