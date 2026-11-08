"""특별도슨트 관객 후기 영상 (59초, 1080×1920 30fps) — 마지막 3회 공연 홍보
- 실제 공연 영상 위에 관객이 남긴 후기를 보라 키컬러(#62579F) 모션그래픽으로 보여준다. AI 생성 없음.
- 후기 문장은 원문 그대로(긴 글은 앞뒤를 덜고 … 로 표시), 관객 설명은 후기 본문에 쓰인 내용만 붙인다.
- 음악 없음(무음 트랙). 대신 59초를 24마디(≈97.6BPM) 격자로 나눠 컷·글자·말풍선이 일정한 박에 떨어지므로
  Edits 등에서 음악을 입혀도 리듬이 맞는다.
  python3 reviews/reviews_video.py <영상 폴더(px_*.mp4)> out.mp4
"""
import math
import os
import subprocess
import sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'docu'))
import render as D                     # docu/render.py: 글자·이징·영상 처리 도구

W, H, FPS = D.W, D.H, D.FPS
DURATION = 59.0
BAR = DURATION / 24                    # 24마디 격자 (≈97.6BPM)
BEAT = BAR / 4
L, R = D.SAFE_L, D.SAFE_R
ACC, ACC_T, WHITE = D.ACCENT, D.ACCENT_T, D.WHITE
QF, QF_B, QF_M = D.F_SANS, D.F_HEAD, D.F_SANS_M   # Pretendard SemiBold / Bold / Medium


def T(bar, beat=0.0):
    return bar * BAR + beat * BEAT


# ── 영상 컷 (마디 단위): (시작마디, 마디 수, 소스, 소스 시작초) — 60fps 변환본도 속도 1 ──
SHOTS = [
    (0, 2, 'final', 29.6), (2, 2, 'woman', 45.0), (4, 2, 'draw', 36.0), (6, 2, 'spot', 100.0),
    (8, 1, 'sign', 15.0), (9, 1, 'yusin', 22.0), (10, 2, 'woman', 68.0), (12, 2, 'spot', 18.0),
    (14, 1, 'woman', 80.0), (15, 2, 'draw', 76.0), (17, 2, 'final', 35.0), (19, 2, 'sign', 38.0),
    (21, 3, None, 0.0),
]

# ── 후기 카드 ──
BUBBLES = ['울컥하고 감동적이었어요.', '최근 본 공연 중 최고였슴', '두 번 봤는데 볼수록 더 감동', '눈물펑펑입니다.',
           '와 무료공연이 이 수준이라니', '쉽지 않은 내용임에도 아이들이 몰입해서 관람했습니다',
           '특별 도슨트라는 이름에 맞게 정말 특별했습니다!', '또 오고싶어요!!!']
CARDS = [
    (0, 2, dict(kind='title')),
    (2, 2, dict(kind='quote', text='책과 영상으로 접할 때보다 훨씬 와닿았습니다. … 마치 씻김굿을 보는 듯 했습니다.', attr='관람객 후기')),
    (4, 2, dict(kind='quote', text='강원도에서 왔는데, 오는 수고가 전혀 아깝지 않게 느껴졌던 멋진 공연이었습니다.', attr='강원도에서 온 관람객')),
    (6, 2, dict(kind='quote', text='마산에서 한걸음에 달려와 온몸짓으로 민주주의를 새롭게 보여 주셔서 감사합니다', attr='마산에서 온 관람객')),
    (8, 2, dict(kind='burst')),
    (10, 2, dict(kind='quote', text='수어로 관람자를 넓게 배려하는 섬세함조차 민주주의의 가치를 잘 실현하고 있는 공연이라 생각합니다.', attr='관람객 후기')),
    (12, 2, dict(kind='quote', size=54, text='The performers themselves expressed such genuine passion that it transcended a need for translation. Very moving.',
                 attr='해외 관람객 · 원문 영어', tr='배우들의 진심 어린 열정은 번역이 필요 없을 만큼 깊이 전해졌습니다. 정말 감동적이었어요.')),
    (14, 1, dict(kind='quote', text='일본에서 왔습니다. 이런 시설이 있는게 정말 부럽습니다.', attr='일본에서 온 관람객')),
    (15, 2, dict(kind='quote', text='광주에서 왔는데 이곳에서 5·18민주화운동을 잘 전달해주셔서 너무 감사합니다', attr='광주에서 온 관람객')),
    (17, 2, dict(kind='quote', text='오후 3시에 경험하게 해주신 이 기억은 아주 오래 제 가슴에 머무를 것입니다.', attr='관람객 후기')),
    (19, 2, dict(kind='climax', text='민주주의는 결승선이 없으니 우리 스스로 계속 보듬어주듯이 지켜나가야 하겠습니다.')),
    (21, 3, dict(kind='cta')),
]
CTA_BEATS = [0, 1, 4, 5, 6, 7]
RAIN = ['너무 감동적이었어요', '눈물이 났어요', '또 오고 싶어요', '몸으로 기억하는 역사', '최고였어요', '수어까지 감사해요',
        '아이와 함께 왔어요', '뭉클했어요', '꼭 다시 올게요', '민주주의 만세', '새로운 도슨트', '울컥했어요',
        '잊지 않겠습니다', '가슴이 뜨거워요', '추천합니다', '감사합니다']


# ── 글자 도구 ──
def wrap(txt, path, size, maxw):
    lines, cur = [], ''
    for w in txt.split(' '):
        t = (cur + ' ' + w).strip()
        if not cur or D.line_width(t, path, size) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def words(c, lines, path, size, x0, y0, lt, start, step, out, fill=WHITE, align='left', lh=1.45):
    """단어마다 보이지 않는 선 아래에서 솟아오름. 반환: (다음 줄 y, 마지막 단어 등장 시각)"""
    wi, y = 0, y0
    for ln in lines:
        ws = ln.split(' ')
        lw = D.line_width(ln, path, size)
        x = x0 - lw / 2 if align == 'center' else x0
        for w in ws:
            D.kinetic(c, w, path, size, x, y, lt, start + wi * step, fill=fill, stagger=.012, dur=.4, out=out)
            x += D.line_width(w + ' ', path, size)
            wi += 1
        y += int(size * lh)
    return y, start + (wi - 1) * step


def quote_block(c, card, lt, dur):
    size = card.get('size', 62)
    lines = wrap(card['text'], QF, size, 800)
    tr = wrap(card['tr'], QF_M, 36, 800) if card.get('tr') else []
    out = dur - .35
    block = len(lines) * size * 1.45 + 64 + len(tr) * 52
    y0 = 1460 - block
    D.kinetic(c, '“', QF_B, 260, L + 4, y0 - 215, lt, 0, fill=ACC_T, style='pop', dur=.35, out=out, shadow=False)
    ye, tl = words(c, lines, QF, size, L + 40, y0, lt, .18, BEAT / 4, out)
    h = (ye - y0 - size * .4) * D.ease((lt - .1) / .6) * (1 - D.ease((lt - out) / .3))
    D.bar(c, L + 8, y0 + 12, 6, h, ACC_T)
    D.kinetic(c, '— ' + card['attr'], QF_M, 32, L + 40, ye + 8, lt, tl + .3, fill=(205, 200, 232), stagger=.01, out=out)
    if tr:
        words(c, tr, QF_M, 36, L + 40, ye + 64, lt, tl + .45, BEAT / 8, out, fill=(225, 225, 232), lh=1.4)


@lru_cache(maxsize=None)
def bubble_img(txt, side):
    size, padx, pady = 42, 30, 20
    lines = wrap(txt, QF, size, 620)
    tw = max(D.line_width(l, QF, size) for l in lines)
    h = int(len(lines) * size * 1.35 + pady * 2)
    w = int(tw + padx * 2)
    im = Image.new('RGBA', (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bg, fg = (ACC + (238,), WHITE) if side == 0 else ((246, 245, 250, 240), (30, 28, 42))
    d.rounded_rectangle([0, 0, w, h], radius=34, fill=bg)
    y = pady - 4
    for l in lines:
        D.kinetic(im, l, QF, size, padx, y, 99, fill=fg, shadow=False)
        y += int(size * 1.35)
    return im


def burst(c, lt, dur):
    D.bar(c, L + 20, D.SAFE_T + 20, (D.line_width('관람객 후기', QF, 30, 4) + 40) * D.ease(lt / .3), 56, ACC)
    D.kinetic(c, '관람객 후기', QF, 30, L + 40, D.SAFE_T + 28, lt, .1, shadow=False, track=4)
    times = [k * BEAT for k in range(len(BUBBLES))]
    gap, bottom = 22, 1450
    out = dur - .3
    fade_all = 1 - D.ease((lt - out) / .3)
    for k, (txt, tk) in enumerate(zip(BUBBLES, times)):
        if lt < tk:
            continue
        im = bubble_img(txt, k % 2)
        # 뒤에 뜬 말풍선만큼 위로 밀려 올라감
        off = sum((bubble_img(BUBBLES[j], j % 2).height + gap) * D.ease((lt - times[j]) / .35)
                  for j in range(k + 1, len(BUBBLES)) if lt >= times[j])
        y = bottom - im.height - off
        a = D.clamp((y - 420) / 180) * fade_all * D.clamp((lt - tk) / .12)
        sc = max(.05, D.back((lt - tk) / .3, 2.2))
        if a <= 0:
            continue
        sim = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR) if sc != 1 else im
        x = L + 10 if k % 2 == 0 else R - im.width             # 보라 말풍선은 왼쪽, 흰 말풍선은 오른쪽
        cx = x if k % 2 == 0 else x + im.width - sim.width
        cy = y + (im.height - sim.height) / 2
        c.alpha_composite(D.with_alpha(sim, a), (int(cx), int(cy)))


def title(c, lt, dur):
    out = dur - .35
    c.alpha_composite(title_bg(lt, dur))
    D.bar(c, L + 20, D.SAFE_T + 20, (D.line_width('관람객 후기', QF, 30, 4) + 40) * D.ease(lt / .3), 56, ACC)
    D.kinetic(c, '관람객 후기', QF, 30, L + 40, D.SAFE_T + 28, lt, .1, shadow=False, track=4)
    words(c, ['관객이 남긴'], QF_B, 128, L + 20, 1050, lt, .25, BEAT / 2, out)
    words(c, ['말들'], QF_B, 128, L + 20, 1215, lt, .25 + BEAT, BEAT / 2, out, fill=ACC_T)
    D.kinetic(c, '민주화운동기념관 특별도슨트', QF_M, 40, L + 24, 1420, lt, .25 + 2 * BEAT, fill=(225, 225, 235), stagger=.02, out=out, track=2)


def title_bg(lt, dur):
    """배경: 수많은 후기 조각이 세 줄로 천천히 떠오름 (투명도를 한 번에 주려고 별도 레이어)"""
    out = dur - .35
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for i, s in enumerate(RAIN):
        col = i % 3
        y = 1700 - ((lt * (40 + 12 * col) + i * 230) % 1500)
        x = 70 + col * 320 + (i * 37) % 60
        D.kinetic(c, s, D.F_NUM, 36, x, y, 99, fill=(235, 232, 250), shadow=False)
    a = .2 * D.ease(lt / .6) * (1 - D.ease((lt - out) / .3))
    return D.with_alpha(c, a)


def climax(c, card, lt, dur):
    out = dur - .3
    lines = wrap(card['text'], QF_B, 76, 820)
    y0 = 1000 - len(lines) * 76 * 1.4 / 2
    ye, tl = words(c, lines, QF_B, 76, (L + R) / 2, y0, lt, .1, BEAT / 2, out, align='center', lh=1.4)
    u = D.ease_io((lt - tl - .3) / .5) * (1 - D.ease((lt - out) / .25))
    D.bar(c, (L + R) / 2 - 160 * u, ye + 20, 320 * u, 6, ACC_T)


_PART = np.random.default_rng(1129).random((70, 5))


def cta(c, lt, dur):
    cx = (L + R) / 2
    d = ImageDraw.Draw(c)
    for px, py, sp, sz, ph in _PART:
        y = (py * H - lt * (18 + 45 * sp)) % H
        a = (.2 + .3 * (.5 + .5 * math.sin(lt * (1 + 2 * sp) + ph * 6.28))) * D.ease(lt / 1.0)
        r = 1 + 2.4 * sz
        d.ellipse([px * W - r, y - r, px * W + r, y + r], fill=(200, 192, 245, int(255 * a * .55)))
    b = [x * BEAT for x in CTA_BEATS]
    D.kinetic(c, '이제 마지막', QF, 60, cx, 640, lt, b[0], align='center', stagger=.03)
    D.kinetic(c, '3번의 공연', QF_B, 168, cx, 730, lt, b[1], fill=ACC_T, align='center', style='pop', stagger=.05, dur=.4)
    u = D.ease_io((lt - 2.5 * BEAT) / .45)
    D.bar(c, cx - 70 * u, 975, 140 * u, 5, ACC_T)
    D.kinetic(c, '민주화운동기념관 특별도슨트', QF_M, 42, cx, 1010, lt, b[2], align='center', stagger=.02, track=2)
    D.kinetic(c, '금·토·일 오후 3시', QF_B, 68, cx, 1080, lt, b[3], align='center', stagger=.03)
    D.kinetic(c, '11월 29일까지 · 무료', QF_M, 44, cx, 1182, lt, b[4], align='center', stagger=.02)
    D.kinetic(c, 'M1 B1 상설전시실', QF_M, 32, cx, 1252, lt, b[5], fill=(190, 186, 210), align='center', stagger=.02)


def overlay(t):
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for b0, nb, card in CARDS:
        t0, t1 = T(b0), T(b0 + nb)
        if t0 <= t < t1 or (card['kind'] == 'cta' and t >= t0):
            lt, dur = t - t0, t1 - t0
            k = card['kind']
            if k == 'title':
                title(c, lt, dur)
            elif k == 'quote':
                quote_block(c, card, lt, dur)
            elif k == 'burst':
                burst(c, lt, dur)
            elif k == 'climax':
                climax(c, card, lt, dur)
            elif k == 'cta':
                cta(c, lt, dur)
    return c


# ── 영상 ──
_RD, _ROOT = None, None
_GLOW = D._GLOW
_ACC = D._ACC


def pulse(t, kind):
    amp = {'burst': .016, 'climax': .014}.get(kind, 0)
    if not amp:
        return 0.0
    nb = math.floor(t / BEAT + 1e-6)
    since = t - nb * BEAT
    return amp * (1.5 if nb % 4 == 0 else 1) * (1 - math.exp(-since * 30)) * math.exp(-since * 5)


def card_kind(t):
    for b0, nb, card in CARDS:
        if T(b0) <= t < T(b0 + nb):
            return card['kind']
    return 'cta'


def render_frame(i):
    global _RD
    if _RD is None:
        _RD = D.Reader(_ROOT)
    t = i / FPS
    si = next((n for n, s in enumerate(SHOTS) if T(s[0]) <= t < T(s[0] + s[1])), len(SHOTS) - 1)
    b0, nb, key, st = SHOTS[si]
    t0, t1 = T(b0), T(b0 + nb)
    kind = card_kind(t)
    k = i - int(round(t0 * FPS))
    if key is None:
        lt = t - t0
        g = np.broadcast_to(_GLOW * _ACC * ((.16 + .04 * math.sin(lt * 2.2)) * D.ease((lt - .3) / 1.0)), (H, W, 3)).astype(np.float32)
        g = g * (1 - D.ease((t - (DURATION - .6)) / .6))
    else:
        src_fps = D.SRC[key][1]
        idx = int(round(st * src_fps + k * src_fps / FPS))       # 속도 1: 60fps 변환본은 2장씩 건너뜀(반복 프레임 제거)
        f = _RD.frame(key, idx)[..., ::-1]
        punch = (1 - k / 5) ** 2 if k < 5 and si > 0 else 0
        if punch > .04:
            kb = int(60 * punch)
            f = cv2.blur(np.ascontiguousarray(f), (kb, 1) if si % 2 == 0 else (1, kb))
        prog = (t - t0) / (t1 - t0)
        g = D.grade(f, 1.0 + .06 * prog + .1 * punch + pulse(t, kind))
        g = D.scrim(g, top=.5, bottom={'burst': .6, 'climax': .85}.get(kind, .82))
        if kind == 'climax':
            g = g * .8
        g = np.clip(g + cv2.resize(D._GRAIN[i % 4], (W, H))[..., None], 0, 1)
        if i < 9:
            g = g * (i / 9)                                       # 첫 0.3초: 어둠에서 열림
    base = Image.fromarray((g * 255).astype(np.uint8)).convert('RGBA')
    base.alpha_composite(overlay(t))
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
    # 음악 없음: 앱 호환을 위해 무음 오디오 트랙만 붙인다
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
                    '-map', '0:v', '-map', '1:a', '-t', str(DURATION), '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k',
                    '-movflags', '+faststart', out], check=True)
    os.remove(tmp)
    print('done', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
