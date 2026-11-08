"""특별도슨트 관객 후기 영상 (59초, 1080×1920 30fps) — 마지막 3회 공연 홍보
- 실제 공연 영상 위에 관객이 남긴 후기를 보라 키컬러(#62579F) 모션그래픽으로 보여준다. AI 생성 없음.
- 후기 문장은 원문 그대로(긴 글은 앞뒤를 덜고 … 로 표시), 관객 설명은 후기 본문에 쓰인 내용만 붙인다.
- v1.1: 카드 한 장 4박(≈2.5초), 글자 등장 2배 빠르게, 말풍선 2묶음(반 박마다 하나, 32개)과
  큰 글씨가 박마다 쌓이는 장면(8개)을 더해 후기 약 50개. 공연 영상도 박 단위로 더 자주 바꿔 여러 배우가 나온다.
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


def T(beat):
    return beat * BEAT


# ── 영상 컷 (박 단위): (시작 박, 박 수, 소스, 소스 시작초) — 60fps 변환본도 속도 1 ──
SHOTS = [
    (0, 4, 'final', 4.0), (4, 4, 'woman', 52.0), (8, 4, 'draw', 12.0), (12, 4, 'sign', 24.0),
    (16, 4, 'spot', 40.0), (20, 4, 'draw', 57.0), (24, 4, 'final', 30.0), (28, 5, 'woman', 84.0),
    (33, 3, 'spot', 66.0), (36, 4, 'draw', 40.0),
    (40, 2, 'yusin', 14.0), (42, 2, 'woman', 64.0), (44, 2, 'draw', 98.0), (46, 2, 'sign', 40.0),
    (48, 4, 'final', 52.0), (52, 4, 'spot', 100.0), (56, 4, 'woman', 44.0), (60, 4, 'draw', 84.0),
    (64, 4, 'spot', 133.0), (68, 4, 'sign', 44.0), (72, 6, 'woman', 91.0), (78, 4, 'draw', 70.0),
    (82, 14, None, 0.0),
]

# ── 후기 카드 ──
BUBBLES_A = ['울컥하고 감동적이었어요.', '최근 본 공연 중 최고였슴', '두번 봤는데 볼수록 더 감동', '너무너무 재밌었다!!',
             '퍼포먼스가 강렬하고 상징적이었습니다', '바로 앞에서 볼수있어서 참여하는 느낌이 있었어요', '수어까지 제공해줘서 감사해요',
             '쉽지 않은 내용임에도 아이들이 몰입해서 관람했습니다', '역동적이었고, 절제되었으며 아름다웠습니다.', '재밌고 몰입감이 높아요',
             '놀랍고 신선했다. 출연자들에게 감사하다.', '연극은 예상하지못했는데 너무 재밌게봤어요', '몸으로 이야기하는 도슨트 너무 좋았습니다',
             '너무 신선하고 특별한 도슨트네요.', '출연진의 몸짓이 매우 인상적이었습니다.', '기대 이상으로 너무 멋진 프로그램이었습니다.']
BUBBLES_B = ['이렇게 몰입하면서 역사를 본 것이 처음입니다', '두분의 무용수가 하시는데 너무 꽉찬 무대였고, 감동이었습니다.',
             '춤에서 자유를 갈망하는게 느껴져서 뜻 깊었습니다', '표정연기를 잘 하셔서 내가 그곳에 실제로 있는 것처럼 느껴졌다.',
             '음악과 춤으로 역사를 보는 것이 너무 재밌고 더 감동 받았어요.', '아이와 다시 꼭 방문하겠습니다!', '보는 중간중간 눈물을 참느라 힘들었네요!!',
             '미디어 영상과 무용수 분들의 조화가 너무 좋았습니다.', '이미 완벽해서 개선 안해도 될거같아요', '발성이 너무좋아요',
             '무용과 민주화역사의 결합이 좋았습니다', '연기자분들 너무 대단하고 감사합니다', '열정적인 공연 감동적입니다.',
             '매우만족별점9999999999개', '새로운 문화에 눈을 뜬 느낌. 놀라웠음.', '계속 자리를 지켜주세요']
WALL = ['눈물펑펑입니다.', '코끝이 찡해졌어요', '감동이다. 먹먹하다.', '몸으로 기억하는 역사', '연극은 정말 멋지네요', '최고!',
        '또 오고싶어요!!!', '민주주의 만세!']
CARDS = [
    (0, 4, dict(kind='title')),
    (4, 4, dict(kind='quote', text='책과 영상으로 접할 때보다 훨씬 와닿았습니다. … 마치 씻김굿을 보는 듯 했습니다.', attr='관람객 후기')),
    (8, 4, dict(kind='quote', text='강원도에서 왔는데, 오는 수고가 전혀 아깝지 않게 느껴졌던 멋진 공연이었습니다.', attr='강원도에서 온 관람객')),
    (12, 4, dict(kind='quote', text='마산에서 한걸음에 달려와 온몸짓으로 민주주의를 새롭게 보여 주셔서 감사합니다', attr='마산에서 온 관람객')),
    (16, 8, dict(kind='burst', items=BUBBLES_A)),
    (24, 4, dict(kind='quote', text='수어로 관람자를 넓게 배려하는 섬세함조차 민주주의의 가치를 잘 실현하고 있는 공연이라 생각합니다.', attr='관람객 후기')),
    (28, 5, dict(kind='quote', size=54, text='The performers themselves expressed such genuine passion that it transcended a need for translation. Very moving.',
                 attr='해외 관람객 · 원문 영어', tr='배우들의 진심 어린 열정은 번역이 필요 없을 만큼 깊이 전해졌습니다. 정말 감동적이었어요.')),
    (33, 3, dict(kind='quote', text='일본에서 왔습니다. 이런 시설이 있는게 정말 부럽습니다.', attr='일본에서 온 관람객')),
    (36, 4, dict(kind='quote', text='광주에서 왔는데 이곳에서 5·18민주화운동을 잘 전달해주셔서 너무 감사합니다', attr='광주에서 온 관람객')),
    (40, 8, dict(kind='wall', items=WALL)),
    (48, 4, dict(kind='quote', text='부산에서 전시회를 보러 왔어요. … 공연으로 보니 또 새롭고 마음에 더 다가오는거 같아요.', attr='부산에서 온 관람객')),
    (52, 4, dict(kind='quote', text='오후 3시에 경험하게 해주신 이 기억은 아주 오래 제 가슴에 머무를 것입니다.', attr='관람객 후기')),
    (56, 8, dict(kind='burst', items=BUBBLES_B)),
    (64, 4, dict(kind='quote', text='무용수 분들의 형형한 눈빛이 기억에 남습니다.', attr='관람객 후기')),
    (68, 4, dict(kind='quote', text='특별도슨트라는 말이 딱 적합하다. 특별하고 눈을 뗄 수 없었습니다.', attr='관람객 후기')),
    (72, 6, dict(kind='climax', text='민주주의는 결승선이 없으니 우리 스스로 계속 보듬어주듯이 지켜나가야 하겠습니다.')),
    (78, 4, dict(kind='quote', text='와 무료공연이 이 수준이라니 계속해서 공연해주세요', attr='관람객 후기')),
    (82, 14, dict(kind='cta')),
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
    out = dur - .3
    block = len(lines) * size * 1.45 + 64 + len(tr) * 52
    y0 = 1460 - block
    D.kinetic(c, '“', QF_B, 260, L + 4, y0 - 215, lt, 0, fill=ACC_T, style='pop', dur=.3, out=out, shadow=False)
    ye, tl = words(c, lines, QF, size, L + 40, y0, lt, .08, BEAT / 8, out)        # 32분음표마다 한 단어
    h = (ye - y0 - size * .4) * D.ease((lt - .05) / .4) * (1 - D.ease((lt - out) / .3))
    D.bar(c, L + 8, y0 + 12, 6, h, ACC_T)
    D.kinetic(c, '— ' + card['attr'], QF_M, 32, L + 40, ye + 8, lt, tl + .15, fill=(205, 200, 232), stagger=.008, out=out)
    if tr:
        words(c, tr, QF_M, 36, L + 40, ye + 64, lt, tl + .2, BEAT / 16, out, fill=(225, 225, 232), lh=1.4)


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


def label(c, lt):
    D.bar(c, L + 20, D.SAFE_T + 20, (D.line_width('관람객 후기', QF, 30, 4) + 40) * D.ease(lt / .3), 56, ACC)
    D.kinetic(c, '관람객 후기', QF, 30, L + 40, D.SAFE_T + 28, lt, .1, shadow=False, track=4)


def burst(c, card, lt, dur):
    BUBBLES = card['items']
    label(c, lt)
    times = [k * BEAT / 2 for k in range(len(BUBBLES))]                 # 8분음표마다 하나
    gap, bottom = 22, 1450
    out = dur - .3
    fade_all = 1 - D.ease((lt - out) / .3)
    for k, (txt, tk) in enumerate(zip(BUBBLES, times)):
        if lt < tk:
            continue
        im = bubble_img(txt, k % 2)
        # 뒤에 뜬 말풍선만큼 위로 밀려 올라감
        off = sum((bubble_img(BUBBLES[j], j % 2).height + gap) * D.ease((lt - times[j]) / .25)
                  for j in range(k + 1, len(BUBBLES)) if lt >= times[j])
        y = bottom - im.height - off
        a = D.clamp((y - 420) / 180) * fade_all * D.clamp((lt - tk) / .12)
        sc = max(.05, D.back((lt - tk) / .25, 2.2))
        if a <= 0:
            continue
        sim = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR) if sc != 1 else im
        x = L + 10 if k % 2 == 0 else R - im.width             # 보라 말풍선은 왼쪽, 흰 말풍선은 오른쪽
        cx = x if k % 2 == 0 else x + im.width - sim.width
        cy = y + (im.height - sim.height) / 2
        c.alpha_composite(D.with_alpha(sim, a), (int(cx), int(cy)))


WALL_SIZE = [100, 84, 92, 80, 96, 120, 92, 100]


def wall(c, card, lt, dur):
    """짧은 후기가 박마다 하나씩 큰 글씨로 쌓인다. 새 글이 뜨면 앞의 글은 한 톤 어두워진다."""
    items = card['items']
    label(c, lt)
    out = dur - .3
    now = min(len(items) - 1, int(lt / BEAT))
    ys = np.linspace(D.SAFE_T + 150, 1380, len(items))
    for k, txt in enumerate(items):
        tk = k * BEAT
        if lt < tk:
            continue
        size = WALL_SIZE[k % len(WALL_SIZE)]
        w = D.line_width(txt, QF_B, size)
        if w > 860:
            size = int(size * 860 / w)
            w = D.line_width(txt, QF_B, size)
        base = ACC_T if k % 2 else WHITE
        fill = base if k == now else tuple(int(v * .62 + 40) for v in base)
        x = L + 20 if k % 2 == 0 else R - 20 - w
        D.kinetic(c, txt, QF_B, size, x, ys[k] - size / 2, lt, tk, fill=fill, style='pop', stagger=.018, dur=.28, out=out)


def title(c, lt, dur):
    out = dur - .3
    c.alpha_composite(title_bg(lt, dur))
    label(c, lt)
    words(c, ['관객이 남긴'], QF_B, 128, L + 20, 1050, lt, .12, BEAT / 4, out)
    words(c, ['말들'], QF_B, 128, L + 20, 1215, lt, .12 + BEAT / 2, BEAT / 4, out, fill=ACC_T)
    D.kinetic(c, '민주화운동기념관 특별도슨트', QF_M, 40, L + 24, 1420, lt, .12 + BEAT, fill=(225, 225, 235), stagger=.015, out=out, track=2)


def title_bg(lt, dur):
    """배경: 수많은 후기 조각이 세 줄로 천천히 떠오름 (투명도를 한 번에 주려고 별도 레이어)"""
    out = dur - .3
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for i, s in enumerate(RAIN):
        col = i % 3
        y = 1700 - ((lt * (40 + 12 * col) + i * 230) % 1500)
        x = 70 + col * 320 + (i * 37) % 60
        D.kinetic(c, s, D.F_NUM, 36, x, y, 99, fill=(235, 232, 250), shadow=False)
    a = .2 * D.ease(lt / .4) * (1 - D.ease((lt - out) / .3))
    return D.with_alpha(c, a)


def climax(c, card, lt, dur):
    out = dur - .3
    lines = wrap(card['text'], QF_B, 76, 820)
    y0 = 1000 - len(lines) * 76 * 1.4 / 2
    ye, tl = words(c, lines, QF_B, 76, (L + R) / 2, y0, lt, .08, BEAT / 4, out, align='center', lh=1.4)
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
                burst(c, card, lt, dur)
            elif k == 'wall':
                wall(c, card, lt, dur)
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
    amp = {'burst': .016, 'wall': .02, 'climax': .014}.get(kind, 0)
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
        g = D.scrim(g, top=.5, bottom={'burst': .6, 'climax': .85, 'wall': .7}.get(kind, .82))
        if kind in ('climax', 'wall'):
            g = g * (.8 if kind == 'climax' else .62)
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
