"""부마민주항쟁 × 특별도슨트 홍보 숏폼 v1.1 (실물 영상만 사용)
- 촬영 영상(1080×1920 변환본) 위에 키네틱 타이포·날짜 그래픽만 얹는다. AI 생성 이미지·영상 없음.
- 폰트(모두 OFL 오픈 라이선스, docu/fonts): Hahmlet(제목) · IBM Plex Sans KR(본문) · Anton(숫자)
- 사운드: docu/sound.py 가 코드로 직접 합성한 사운드트랙 + 마지막 배우 원음 대사 한 줄
  python3 docu/render.py <영상 폴더> <출력.mp4>
"""
import math, os, subprocess, sys
from functools import lru_cache
import numpy as np
import cv2
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
SAFE_L, SAFE_R, SAFE_T, SAFE_B = 60, 930, 250, 1520
ACCENT = (232, 73, 42)
PAPER = (237, 230, 216)
WHITE = (255, 255, 255)
FONT_DIR = os.environ.get('FONT_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts'))
F_HEAD = os.path.join(FONT_DIR, 'Hahmlet-800.ttf')
F_HEAD_M = os.path.join(FONT_DIR, 'Hahmlet-500.ttf')
F_SANS = os.path.join(FONT_DIR, 'IBMPlexSansKR-SemiBold.ttf')
F_SANS_M = os.path.join(FONT_DIR, 'IBMPlexSansKR-Medium.ttf')
F_SANS_B = os.path.join(FONT_DIR, 'IBMPlexSansKR-Bold.ttf')
F_NUM = os.path.join(FONT_DIR, 'Anton-Regular.ttf')

# ── 소스 (변환본 파일명, 원본 fps) ──────────────────────
SRC = {
    'yusin': ('px_5fdb044c.mp4', 60),     # 유신 현수막 앞 배우 (120fps 원본 → 60fps)
    'spot': ('px_2f255e51.mp4', 30),      # 스포트라이트 속 남성 배우
    'woman': ('px_bfd61af1.mp4', 30),     # 여성 독백 장면
    'draw': ('px_083bac20.mp4', 60),      # 남성 무용수 + 대형 일러스트
    'sign': ('px_cce6e17c.mp4', 60),      # 피켓 (240fps 원본 → 60fps)
    'final': ('px_84bf313a.mp4', 30),     # 마무리 내레이션
}

# ── 타임라인: (시작초, 끝초, 소스, 소스시작초, 속도, 카드) ──────────
# 카드 종류: hook / date / day / turn / montage / voice / cta
DAYS = ['16', '17', '18', '19', '20']
HOOK_D = (.25, 1.05)   # 훅 두 줄 타이핑 시작(초) — sound.py 타자음과 공유
CPS = 14               # 타이핑 속도(글자/초)
CTA_D = dict(label=.25, title=.6, rule=1.35, l3=1.5, l4=1.8, shine=2.3)  # 엔딩 등장 시각(초)
SHOTS = [
    (0.0, 3.0, 'yusin', 14.0, .5, dict(kind='hook', l1='1979년 10월,', l2='부산과 마산에서')),
    (3.0, 5.5, 'spot', 18.0, 1, dict(kind='date', date='1972. 10', text='유신헌법 선포')),
    (5.5, 8.0, 'yusin', 22.0, .5, dict(kind='date', date='1975. 05', text='긴급조치 9호', sub='집회와 시위 금지')),
    (8.0, 10.5, 'spot', 40.0, 1, dict(kind='date', date='1979. 10. 04', text='김영삼 의원', sub='국회의원직 제명')),
    (10.5, 14.0, 'draw', 36.0, .5, dict(kind='day', day=0, place='부산', text='부산대에서', sub='시위가 시작되다')),
    (14.0, 17.0, 'draw', 3.0, .5, dict(kind='day', day=1, place='부산', text='시민들이', sub='거리로')),
    (17.0, 20.0, 'yusin', 16.0, .5, dict(kind='day', day=2, place='부산', text='0시,', sub='비상계엄 선포')),
    (20.0, 23.0, 'woman', 45.0, 1, dict(kind='day', day=3, place='마산', text='마산으로', sub='번진 시위')),
    (23.0, 26.0, 'spot', 91.0, 1, dict(kind='day', day=4, place='마산·창원', text='정오,', sub='위수령 발동')),
    (26.0, 29.5, 'draw', 64.0, .5, dict(kind='date', date='1979. 10. 26', text='18년 유신체제의 끝')),
    (29.5, 32.0, 'sign', 38.0, .5, dict(kind='turn', l1='그 역사를,', l2='몸으로 기억하다')),
    (32.0, 33.5, 'woman', 68.0, 1, dict(kind='montage', word='춤으로')),
    (33.5, 35.0, 'spot', 60.0, 1, dict(kind='montage', word='만나는')),
    (35.0, 36.5, 'sign', 15.0, .5, dict(kind='montage', word='민주화운동의', size=124)),
    (36.5, 38.0, 'draw', 57.0, .5, dict(kind='montage', word='역사')),
    (38.0, 40.0, 'woman', 77.0, 1, dict(kind='montage', word='특별도슨트', accent=True)),
    (40.0, 45.5, 'final', 29.6, 1, dict(kind='voice', text='"우리가 대한민국의 주인입니다."')),
    (45.5, 52.0, 'final', 35.1, 1, dict(kind='cta')),
]
DURATION = SHOTS[-1][1]
VOICE = (40.0, 'final', 29.6, 5.4)  # (영상 시각, 소스, 소스 시작, 길이) — 원음 사용 구간


# ── 이징 ─────────────────────────────────────────
def clamp(t):
    return min(max(t, 0.0), 1.0)


def ease(t):
    return 1 - (1 - clamp(t)) ** 3


def ease_io(t):
    t = clamp(t)
    return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2


def back(t, s=1.9):
    t = clamp(t) - 1
    return 1 + t * t * ((s + 1) * t + s)


# ── 글자 단위 렌더 (캐시) ─────────────────────────────
@lru_cache(maxsize=None)
def font(path, size):
    return ImageFont.truetype(path, size)


@lru_cache(maxsize=None)
def glyph(ch, path, size, fill, shadow=True):
    """한 글자 RGBA (+부드러운 그림자). 반환: (이미지, 전진폭, 여백)"""
    f = font(path, size)
    asc, desc = f.getmetrics()
    w = f.getlength(ch)
    pad = int(size * .3)
    im = Image.new('RGBA', (int(w) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad, pad), ch, font=f, fill=fill)
    if shadow:
        a = im.getchannel('A').filter(ImageFilter.GaussianBlur(max(2, size * .08)))
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        sh.putalpha(a.point(lambda v: int(v * .8)))
        im = Image.alpha_composite(ImageChops.offset(sh, 0, max(1, int(size * .03))), im)
    return im, w, pad


def asc(path, size):
    return font(path, size).getmetrics()[0]


def with_alpha(im, a):
    if a >= 1:
        return im
    arr = np.array(im)
    arr[..., 3] = (arr[..., 3] * max(a, 0)).astype(np.uint8)
    return Image.fromarray(arr)


def line_width(txt, path, size, track=0):
    return sum(glyph(ch, path, size, WHITE)[1] for ch in txt) + track * (len(txt) - 1)


def kinetic(c, txt, path, size, x, y, t, delay=0., fill=WHITE, stagger=.04, dur=.5, style='mask',
            out=None, align='left', track=0, shadow=True):
    """글자별 키네틱 등장.
    mask: 보이지 않는 선 아래에서 솟아오름 / pop: 튀어나오며 확대(오버슈트) / drop: 위에서 떨어짐 / fade: 타자기
    out(초)을 주면 그 시각부터 글자가 차례로 위로 빠지며 사라진다. 반환: 줄 너비"""
    total = line_width(txt, path, size, track)
    if align == 'center':
        x -= total / 2
    cx = x
    for i, ch in enumerate(txt):
        g, w, pad = glyph(ch, path, size, fill, shadow)
        p = (t - delay - i * stagger) / dur
        if p > 0 and ch != ' ':
            a, dy, sc = min(1, p * 2.2), 0.0, 1.0
            if style == 'mask':
                dy = (1 - ease(p)) * size * 1.05
            elif style == 'pop':
                sc = max(.05, back(p, 2.4))
            elif style == 'drop':
                dy = -(1 - back(p)) * size * .9
            elif style == 'fade':
                a = clamp(p)
            if out is not None:
                q = ease((t - out - i * stagger * .6) / .3)
                a *= 1 - q
                dy -= q * size * .7
            im = g
            if sc != 1:
                im = g.resize((max(1, int(g.width * sc)), max(1, int(g.height * sc))), Image.BILINEAR)
            px, py = cx - pad + (g.width - im.width) / 2, y - pad + dy + (g.height - im.height) / 2
            if style == 'mask' and dy > 0:  # 기준선 아래는 잘라서 '솟아오르는' 느낌
                im = im.crop((0, 0, im.width, max(0, int(g.height - dy))))
            if a > 0 and im.height > 0:
                c.alpha_composite(with_alpha(im, a), (int(px), int(py)))
        cx += w + track
    return total


def roll(c, txt, path, size, x, y, t, delay=0., fill=WHITE, stagger=.06, dur=.7, steps=7, out=None):
    """숫자가 슬롯처럼 굴러와 멈춤 (Anton). 숫자 외 문자는 페이드. 반환: 너비"""
    f = font(path, size)
    asc, desc = f.getmetrics()
    lh = asc + desc
    cx = x
    for i, ch in enumerate(txt):
        g, w, pad = glyph(ch, path, size, fill, False)
        p = (t - delay - i * stagger) / dur
        a = clamp(p * 3)
        if out is not None:
            a *= 1 - ease((t - out - i * .02) / .25)
        if p > 0 and ch != ' ' and a > 0:
            if ch.isdigit():
                s = (1 - ease(p)) * steps
                k0 = int(math.floor(s))
                win = Image.new('RGBA', g.size, (0, 0, 0, 0))
                for kq in (k0, k0 + 1):
                    gd = glyph(str((int(ch) + kq) % 10), path, size, fill, False)[0]
                    off = int((kq - s) * lh)
                    if -g.height < off < g.height:
                        tmp = Image.new('RGBA', g.size, (0, 0, 0, 0))
                        tmp.paste(gd, (int((g.width - gd.width) / 2), off))
                        win = Image.alpha_composite(win, tmp)
                # 굴러가는 동안 위아래를 부드럽게 잘라냄
                arr = np.array(win)
                yy = np.arange(arr.shape[0])
                edge = np.clip(np.minimum(yy - pad + 6, pad + lh + 6 - yy) / 14, 0, 1)
                arr[..., 3] = (arr[..., 3] * edge[:, None] * a).astype(np.uint8)
                c.alpha_composite(Image.fromarray(arr), (int(cx - pad), int(y - pad)))
            else:
                c.alpha_composite(with_alpha(g, a), (int(cx - pad), int(y - pad)))
        cx += w
    return cx - x


@lru_cache(maxsize=None)
def outline_text(txt, size, alpha):
    """배경용 거대한 외곽선 숫자 (Anton)"""
    f = font(F_NUM, size)
    bb = f.getbbox(txt, stroke_width=3)
    im = Image.new('RGBA', (bb[2] - bb[0] + 20, bb[3] - bb[1] + 20), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10 - bb[0], 10 - bb[1]), txt, font=f, fill=(0, 0, 0, 0),
                            stroke_width=3, stroke_fill=(255, 255, 255, alpha))
    return im


def bar(c, x, y, w, h, col, a=1.0):
    if w > 0 and h > 0 and a > 0:
        ImageDraw.Draw(c).rectangle([int(x), int(y), int(x + w), int(y + h)], fill=col + (int(255 * a),))


# ── 그래픽 블록 ─────────────────────────────────────
def giant(c, txt, size, lt, dur, y, alpha=60):
    """화면 뒤를 천천히 흘러가는 거대한 외곽선 숫자"""
    im = outline_text(txt, size, alpha)
    p = lt / dur
    a = ease(lt / .4) * (1 - ease((lt - dur + .3) / .3))
    x = W - im.width + 120 - 200 * p
    c.alpha_composite(with_alpha(im, a), (int(x), int(y)))


def day_bar(c, cur, place, t):
    """10.16 → 10.20 진행 그래픽: 선이 다음 날짜로 달려가고 현재 날짜가 굴러와 멈춘다"""
    x0, ly, step = SAFE_L + 30, SAFE_T + 200, 170
    kinetic(c, '1979. 10.', F_SANS, 32, x0 - 8, SAFE_T + 6, 99, fill=(225, 225, 225))
    d = ImageDraw.Draw(c)
    d.line([(x0, ly), (x0 + step * 4, ly)], fill=(255, 255, 255, 90), width=3)
    prog = ease_io(t / .55)
    xe = x0 + step * (cur - 1 + prog) if cur > 0 else x0
    d.line([(x0, ly), (xe, ly)], fill=ACCENT + (255,), width=7)
    for i, dd in enumerate(DAYS):
        cx = x0 + step * i
        if i == cur:
            r = 15 * max(back((t - .4) / .45, 2.6), 0)
            ring = ease((t - .4) / .8)
            if t > .4:
                rr = 15 + 40 * ring
                d.ellipse([cx - rr, ly - rr, cx + rr, ly + rr], outline=ACCENT + (int(255 * (1 - ring)),), width=4)
            col, sz = ACCENT, 76
        else:
            r, col, sz = 8, (WHITE if i < cur else (140, 140, 140)), 48
        if r > 0:
            d.ellipse([cx - r, ly - r, cx + r, ly + r], fill=col + (255,))
        tw = line_width(dd, F_NUM, sz)
        if i == cur:
            roll(c, dd, F_NUM, sz, cx - tw / 2, ly - 22 - sz * 1.45, t, .35, fill=ACCENT, steps=5, dur=.55)
        else:
            kinetic(c, dd, F_NUM, sz, cx - tw / 2, ly - 18 - sz * 1.45, 99, fill=col, shadow=False)
    # 장소 태그: 레드오렌지 블록이 쓸고 지나가며 종이색 태그를 남김
    tag_w = line_width(place, F_SANS_B, 42) + 40
    ty = ly + 44
    wp = ease((t - .15) / .3)
    wo = ease((t - .45) / .3)
    if t > .45:
        bar(c, x0 - 10, ty, tag_w * wo, 66, PAPER)
        kinetic(c, place, F_SANS_B, 42, x0 + 10, ty + 2, t, .5, fill=(20, 19, 18), stagger=.03, dur=.25, style='fade', shadow=False)
    bar(c, x0 - 10 + tag_w * wo, ty, tag_w * (wp - wo), 66, ACCENT)


@lru_cache(maxsize=None)
def line_alpha(txt, path, size):
    """줄 전체 글자 마스크 (빛 반사 효과용)"""
    tw = int(line_width(txt, path, size)) + 2 * int(size * .3)
    g0 = glyph(txt[0], path, size, WHITE, False)[0]
    im = Image.new('RGBA', (tw, g0.height), (0, 0, 0, 0))
    x = 0
    for ch in txt:
        g, w, pad = glyph(ch, path, size, WHITE, False)
        im.alpha_composite(g, (int(x), 0))
        x += w
    return np.array(im)[..., 3].astype(np.float32) / 255


_PART = np.random.default_rng(1016).random((80, 5))


def overlay(card, t, shot_t0, shot_t1):
    lt, dur = t - shot_t0, shot_t1 - shot_t0
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    k = card['kind']
    if k == 'hook':
        giant(c, '1979', 520, lt, dur, 330, 70)
        lw = line_width('부마민주항쟁', F_SANS_B, 36) + 36
        bar(c, SAFE_L + 20, SAFE_T + 20, lw * ease(lt / .3), 60, ACCENT)
        kinetic(c, '부마민주항쟁', F_SANS_B, 36, SAFE_L + 38, SAFE_T + 26, lt, .2, stagger=.03, dur=.3, shadow=False)
        for li, (txt, y) in enumerate(((card['l1'], 1080), (card['l2'], 1225))):
            d0 = HOOK_D[li]
            kinetic(c, txt, F_HEAD, 112, SAFE_L + 20, y, lt, d0, stagger=1 / CPS, dur=.12, style='pop', out=dur - .35)
            n = min(len(txt), int(max(0, lt - d0) * CPS))
            active = lt > d0 and (li == 1 or lt < HOOK_D[1]) and lt < dur - .35
            if active and (n < len(txt) or int(lt * 4) % 2 == 0):  # 깜빡이는 커서
                bar(c, SAFE_L + 28 + line_width(txt[:n], F_HEAD, 112), y + 18, 9, 118, ACCENT)
    elif k == 'date':
        out = dur - .3
        giant(c, card['date'][:4], 470, lt, dur, 300, 55)
        y0 = 1060
        nw = line_width(card['date'], F_NUM, 96) + 44
        wb, wo = ease(lt / .28), ease((lt - out) / .25)
        bar(c, SAFE_L + 20 + nw * wo, y0, nw * (wb - wo), 128, ACCENT)
        roll(c, card['date'], F_NUM, 96, SAFE_L + 42, y0 + 4, lt, .12, out=out)
        kinetic(c, card['text'], F_HEAD, 98, SAFE_L + 20, y0 + 160, lt, .3, out=out)
        if card.get('sub'):
            kinetic(c, card['sub'], F_SANS_M, 50, SAFE_L + 24, y0 + 300, lt, .5, fill=(230, 230, 230), stagger=.025, out=out)
    elif k == 'day':
        out = dur - .3
        giant(c, DAYS[card['day']], 760, lt, dur, 470, 50)
        day_bar(c, card['day'], card['place'], lt)
        kinetic(c, card['text'], F_HEAD, 104, SAFE_L + 20, 1160, lt, .25, out=out)
        kinetic(c, card['sub'], F_HEAD, 104, SAFE_L + 20, 1295, lt, .45, out=out)
    elif k == 'turn':
        kinetic(c, card['l1'], F_HEAD_M, 92, SAFE_L + 20, 1110, lt, .15, stagger=.05)
        w2 = kinetic(c, card['l2'], F_HEAD, 120, SAFE_L + 20, 1235, lt, .6, fill=PAPER, stagger=.06, style='pop')
        bar(c, SAFE_L + 22, 1235 + asc(F_HEAD, 120) + 34, w2 * ease_io((lt - 1.3) / .5), 8, ACCENT)
    elif k == 'montage':
        kinetic(c, '민주화운동기념관 특별도슨트', F_SANS, 34, SAFE_L + 20, SAFE_T + 24, 99, fill=PAPER)
        sz = card.get('size', 156)
        acc = card.get('accent')
        cx = (SAFE_L + SAFE_R) / 2
        ww = kinetic(c, card['word'], F_HEAD, sz, cx, 1180, lt, .02, fill=ACCENT if acc else WHITE, stagger=.045,
                     dur=.35, style='pop', align='center', out=None if acc else dur - .18)
        u = ease_io((lt - .25) / .35) * (1 if acc else 1 - ease((lt - dur + .2) / .2))
        bar(c, cx - ww / 2 * u, 1180 + asc(F_HEAD, sz) + 36, ww * u, 6, PAPER if acc else ACCENT)
    elif k == 'voice':
        kinetic(c, card['text'], F_HEAD_M, 58, (SAFE_L + SAFE_R) / 2, 1330, lt, .2, stagger=.03, dur=.4, align='center',
                out=dur - .4)
    elif k == 'cta':
        cx = (SAFE_L + SAFE_R) / 2
        # 먼지 입자: 천천히 떠오르며 반짝임
        d = ImageDraw.Draw(c)
        fade_in = ease(lt / 1.0)
        for px, py, sp, sz, ph in _PART:
            y = (py * H - lt * (20 + 50 * sp)) % H
            a = (.25 + .35 * (.5 + .5 * math.sin(lt * (1 + 2 * sp) + ph * 6.28))) * fade_in
            r = 1 + 2.5 * sz
            d.ellipse([px * W - r, y - r, px * W + r, y + r], fill=(255, 255, 255, int(255 * a * .6)))
        kinetic(c, '민주화운동기념관', F_SANS, 44, cx, 690, lt, CTA_D['label'], stagger=.035, align='center', track=8)
        tw = kinetic(c, '특별도슨트', F_HEAD, 128, cx, 775, lt, CTA_D['title'], stagger=.07, dur=.55, align='center')
        # 빛 반사: 대각선 레드오렌지 빛이 제목을 훑고 지나감
        sp = (lt - CTA_D['shine']) / .8
        if 0 < sp < 1:
            m = line_alpha('특별도슨트', F_HEAD, 128)
            pad = int(128 * .3)
            yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]]
            pos = -150 + (m.shape[1] + 300) * ease_io(sp)
            band = np.exp(-((xx + yy * .35 - pos) ** 2) / (2 * 45 ** 2))
            arr = np.zeros(m.shape + (4,), np.uint8)
            arr[..., :3] = ACCENT
            arr[..., 3] = (m * band * 255).astype(np.uint8)
            c.alpha_composite(Image.fromarray(arr), (int(cx - tw / 2 - pad), int(775 - pad)))
        u = ease_io((lt - CTA_D['rule']) / .45)
        bar(c, cx - 70 * u, 990, 140 * u, 5, ACCENT)
        kinetic(c, '매주 금토일', F_SANS_B, 60, cx, 1040, lt, CTA_D['l3'], stagger=.045, align='center')
        kinetic(c, '오후 3시', F_SANS_B, 60, cx, 1130, lt, CTA_D['l4'], stagger=.045, align='center')
    return c


# ── 영상 처리 ──────────────────────────────────────
class Reader:
    def __init__(self, root):
        self.root, self.caps = root, {}

    def frame(self, key, idx):
        fn, fps = SRC[key]
        cap = self.caps.get(key)
        if cap is None:
            cap = self.caps[key] = [cv2.VideoCapture(os.path.join(self.root, fn)), -1]
        if idx != cap[1] + 1:
            cap[0].set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, f = cap[0].read()
        cap[1] = idx
        if not ok:
            f = np.zeros((H, W, 3), np.uint8)
        return f


def grade(f, zoom):
    if zoom != 1:
        h, w = f.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h * .45), 0, zoom)
        f = cv2.warpAffine(f, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    g = f.astype(np.float32) / 255
    lum = g.mean(axis=2, keepdims=True)
    g = lum + (g - lum) * .55                 # 채도 낮춤
    g = np.clip((g - .5) * 1.12 + .48, 0, 1)  # 대비
    return g


_Y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
_X = np.linspace(-1, 1, W, dtype=np.float32)[None, :, None]


def scrim(g, top=.55, bottom=.75):
    k = np.clip((.35 - _Y) / .35, 0, 1) * top + np.clip((_Y - .5) / .5, 0, 1) * bottom
    return g * (1 - k)


_EDGE = np.clip((_X ** 2 + ((_Y - .5) * 2) ** 2 - .55) / 1.2, 0, 1)   # 가장자리 빛번짐
_GLOW = np.exp(-(_X ** 2 + ((_Y - .45) * 3.2) ** 2) * 2.2)             # 엔딩 제목 뒤 은은한 빛
_ACC = np.array(ACCENT, np.float32)[None, None, :] / 255
_GRAIN = [np.random.default_rng(1979 + k).normal(0, .025, (H // 2, W // 2, 1)).astype(np.float32) for k in range(4)]
_FLASH = {int(round(sh[0] * FPS)) for sh in SHOTS if sh[5]['kind'] == 'turn'}
_RD, _ROOT = None, None


def render_frame(i):
    global _RD
    if _RD is None:
        _RD = Reader(_ROOT)
    t = i / FPS
    si = next(n for n, sh in enumerate(SHOTS) if sh[0] <= t < sh[1]) if t < DURATION else len(SHOTS) - 1
    t0, t1, key, st, speed, card = SHOTS[si]
    kind = card['kind']
    k = i - int(round(t0 * FPS))                 # 컷 이후 프레임
    kk = int(round(t1 * FPS)) - 1 - i            # 다음 컷까지 남은 프레임
    src_fps = SRC[key][1]
    idx = int(round(st * src_fps + k * speed * src_fps / FPS))
    f = _RD.frame(key, idx)[..., ::-1]
    # 컷 전환: 줌 펀치 + 방향 모션블러 (휩)
    punch = (1 - k / 5) ** 2 if k < 5 and kind not in ('cta', 'turn', 'hook', 'voice') else 0
    nxt = SHOTS[si + 1][5]['kind'] if si + 1 < len(SHOTS) else 'cta'
    whip_out = ((3 - kk) / 3) ** 2 if kk < 3 and nxt not in ('cta', 'voice', 'turn') else 0
    kb = int(80 * max(punch, whip_out))
    if kb > 1:
        f = cv2.blur(np.ascontiguousarray(f), (kb, 1) if si % 2 == 0 else (1, kb))
    g = grade(f, 1.0 + .07 * (t - t0) / (t1 - t0) + .12 * punch)
    if kind == 'montage' and k < 3:              # 몽타주 컷: RGB 분리
        s = (3 - k) * 8
        g = np.stack([np.roll(g[..., 0], s, 1), g[..., 1], np.roll(g[..., 2], -s, 1)], -1)
    if kind == 'cta':
        lt = t - t0
        breath = .14 + .04 * math.sin(lt * 2.2)
        g = np.broadcast_to(_GLOW * _ACC * (breath * ease((lt - .4) / 1.2)), (H, W, 3)).astype(np.float32)
    else:
        g = scrim(g, top=.5, bottom=.8 if kind != 'montage' else .55)
        g = np.clip(g + cv2.resize(_GRAIN[i % 4], (W, H))[..., None], 0, 1)
    if kind in ('montage', 'day') and k < 6:     # 컷마다 가장자리에 붉은 빛번짐
        g = np.clip(g + _EDGE * _ACC * ((1 - k / 6) * (.5 if kind == 'montage' else .3)), 0, 1)
    if kind == 'voice' and k < 8:                # 몽타주 → 대사: 어둠에서 열림
        g = g * (k / 8)
    if i in _FLASH:
        g = np.ones_like(g)                      # 1프레임 화이트 플래시
    elif i - 1 in _FLASH:
        g = np.clip(g + .55, 0, 1)
    base = Image.fromarray((g * 255).astype(np.uint8)).convert('RGBA')
    base.alpha_composite(overlay(card, t, t0, t1))
    return np.array(base.convert('RGB')).tobytes()


def main(root, out, workers=os.cpu_count()):
    global _ROOT
    _ROOT = root
    tmp = out + '.video.mp4'
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    n = int(DURATION * FPS)
    from multiprocessing import Pool
    CH = 20  # 연속 구간 단위로 나눠 순차 읽기 유지
    step = workers * CH  # 한 번에 이만큼만 메모리에 둔다 (imap은 결과가 쌓여 OOM)
    with Pool(workers) as pool:
        for b in range(0, n, step):
            for fr in pool.map(render_frame, range(b, min(n, b + step)), chunksize=CH):
                p.stdin.write(fr)
            print('frame', min(n, b + step), '/', n, flush=True)
    p.stdin.close(); p.wait()
    # 오디오: 합성 사운드트랙 + 마지막 배우 원음 한 줄 → 전체 -14 LUFS
    import sound
    music = out + '.music.wav'
    sound.build(music)
    vt, vkey, vst, vlen = VOICE
    vsrc = os.path.join(root, SRC[vkey][0])
    ms = int(vt * 1000)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-ss', str(vst), '-t', str(vlen), '-i', vsrc, '-i', music,
                    '-filter_complex',
                    f'[1:a]afade=t=in:d=0.15,afade=t=out:st={vlen - 0.4}:d=0.4,loudnorm=I=-16:TP=-1.5,'
                    f'aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}:all=1,apad[v];'
                    f'[2:a]aformat=sample_rates=48000:channel_layouts=stereo[m];'
                    f'[m][v]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,aformat=sample_rates=48000[a]',
                    '-map', '0:v', '-map', '[a]', '-t', str(DURATION), '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                    '-movflags', '+faststart', out], check=True)
    os.remove(tmp)
    os.remove(music)
    print('done', out)


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main(sys.argv[1], sys.argv[2])
