"""VOX 스타일 아날로그 콜라주 엔진 — 인쇄물을 오려 손으로 배치하고 촬영한 느낌.
모든 무작위 값은 (seed, 요소 이름)에서 결정적으로 나온다 → 같은 seed·chaos면 같은 프레임.
"""
import hashlib, math, os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from . import config as C

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.vox_cache')
INK = np.array(C.INK, np.float32) / 255
PAPER = np.array(C.PAPER, np.float32) / 255
GREY = np.array(C.GREY, np.float32) / 255
ACCENT = np.array(C.ACCENT, np.float32) / 255
STEP = C.FPS / 12  # 스톱모션 등장은 12fps 계단


def rng(seed, *keys):
    h = hashlib.sha256(('|'.join(map(str, (seed,) + keys))).encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], 'little'))


# ── 이징 ───────────────────────────────────────────
def ease_out_expo_overshoot(t, overshoot=0.08):
    """ease-out expo + 작은 오버슈트 후 안착"""
    t = np.clip(t, 0, 1)
    base = 1 - 2 ** (-10 * t)
    return base + overshoot * np.sin(np.pi * t) * (1 - t) * 2.2


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def stepped(t_frames):
    """등장 순간에만 12fps 계단 (프레임 번호를 12fps 격자로 내림)"""
    return math.floor(t_frames / STEP) * STEP


# ── 이미지 처리 ─────────────────────────────────────
def lum(rgb):
    return rgb[..., 0] * .299 + rgb[..., 1] * .587 + rgb[..., 2] * .114


def to_print(rgb, contrast=1.25, lift=0.0):
    """흑백 변환 후 잉크~종이 범위로 매핑 (순백·순흑 없음)"""
    l = lum(rgb)
    l = np.clip((l - .5) * contrast + .5 + lift, 0, 1)
    return INK + (PAPER - INK) * l[..., None], l


def duotone(rgb):
    l = np.clip((lum(rgb) - .5) * 1.3 + .5, 0, 1)
    return INK + (ACCENT - INK) * l[..., None], l  # 그림자=잉크, 밝은 곳=레드오렌지


def hue_mask(rgb_u8, ranges):
    hsv = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2HSV)
    m = np.zeros(hsv.shape[:2], np.float32)
    for lo, hi in ranges:
        m = np.maximum(m, ((hsv[..., 0] >= lo) & (hsv[..., 0] <= hi) & (hsv[..., 1] > 90) & (hsv[..., 2] > 40)).astype(np.float32))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    return cv2.GaussianBlur(m, (0, 0), 2)


def noise_edge(h, w, r, scale, amp):
    n = r.random((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    return cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC) * amp


def apply_edge(rgb, a, kind, r, chaos, pad=24):
    """가장자리 처리: sticker(깨끗한 컷+얇은 종이 테두리) / rough(손으로 다듬은) / torn(찢긴 섬유) / print(직사각 인쇄+여백)"""
    h, w = a.shape
    rgb = np.pad(rgb, ((pad, pad), (pad, pad), (0, 0)), constant_values=0)
    a = np.pad(a, pad, constant_values=0)
    H, W = a.shape
    if kind == 'print':
        m = int(14 + 10 * chaos)
        card = np.zeros((H, W), np.float32)
        card[pad - m:pad + h + m, pad - m:pad + w + m] = 1
        out = np.where(card[..., None] > 0, PAPER * (1 - a[..., None]) + rgb * a[..., None], 0)
        return out.astype(np.float32), card
    if kind == 'sticker':
        k = int(7 + 4 * chaos)
        border = cv2.dilate((a > .5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))).astype(np.float32)
        border = cv2.GaussianBlur(border, (0, 0), 1.0)
        out = PAPER * (1 - a[..., None]) + rgb * a[..., None]
        return (out * (border[..., None] > 0)).astype(np.float32), np.maximum(border, a)
    if kind == 'rough':
        d = cv2.distanceTransform((a > .5).astype(np.uint8), cv2.DIST_L2, 5)
        cut = d > noise_edge(H, W, r, 9, 3 + 5 * chaos)
        aa = cv2.GaussianBlur(cut.astype(np.float32), (0, 0), .8) * (a > .05)
        return rgb.astype(np.float32), aa
    # torn: 종이 섬유가 보이는 찢긴 가장자리 (바깥쪽 흰 섬유 테두리)
    k = int(10 + 8 * chaos)
    grow = cv2.dilate((a > .5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
    d = cv2.distanceTransform(grow, cv2.DIST_L2, 5)
    rim = (d > noise_edge(H, W, r, 5, k * .9) + noise_edge(H, W, r, 2, 2.5)).astype(np.float32)
    fiber = np.clip(noise_edge(H, W, r, 1, 1) * 1.2, 0, 1)
    rim = cv2.GaussianBlur(rim, (0, 0), .7)
    base = PAPER * (0.92 + 0.08 * fiber[..., None])
    out = base * (1 - a[..., None]) + rgb * a[..., None]
    return out.astype(np.float32), np.maximum(rim, a * rim)


def pick_edge(r, chaos, hero=False):
    if hero:
        return 'sticker' if r.random() < .6 else 'print'
    kinds = ['sticker', 'print', 'rough', 'torn']
    w = np.array([.36, .30, .20 + .05 * chaos, .14 + .1 * chaos])
    return kinds[r.choice(4, p=w / w.sum())]


# ── 스프라이트 (RGBA float32 + accent 가중치) ───────────
class Sprite:
    def __init__(self, rgb, a, acc=None):
        self.rgb, self.a = rgb.astype(np.float32), a.astype(np.float32)
        self.acc = acc.astype(np.float32) if acc is not None else None

    @property
    def size(self):
        return self.a.shape[1], self.a.shape[0]


def text_sprite(text, font_path, size, color, jitter=0.0, r=None, tracking=0, stroke=0, stroke_color=None):
    """단어별 기준선·회전 흔들림(chaos)이 들어간 한 줄 텍스트"""
    font = ImageFont.truetype(font_path, size)
    words = text.split(' ')
    tiles = []
    for wd in words:
        bb = font.getbbox(wd, stroke_width=stroke)
        tw, th = bb[2] - bb[0] + 8, bb[3] - bb[1] + 8
        im = Image.new('L', (tw + 2 * stroke, th + 2 * stroke), 0)
        d = ImageDraw.Draw(im)
        d.text((4 - bb[0] + stroke, 4 - bb[1] + stroke), wd, font=font, fill=255)
        a = np.array(im, np.float32) / 255
        rot = (r.uniform(-1, 1) * 2.2 * jitter) if r is not None else 0
        dy = (r.uniform(-1, 1) * size * .06 * jitter) if r is not None else 0
        if rot:
            pd = int(size * .12)
            a = np.pad(a, pd)
            M = cv2.getRotationMatrix2D((a.shape[1] / 2, a.shape[0] / 2), rot, 1)
            a = cv2.warpAffine(a, M, (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR)
        tiles.append((a, dy))
    space = int(size * .28) + tracking
    Wt = sum(t[0].shape[1] for t in tiles) + space * (len(tiles) - 1)
    Ht = max(t[0].shape[0] for t in tiles) + int(size * .2)
    A = np.zeros((Ht, Wt), np.float32)
    x = 0
    for a, dy in tiles:
        y = int(size * .1 + dy)
        y = max(0, min(Ht - a.shape[0], y))
        A[y:y + a.shape[0], x:x + a.shape[1]] = np.maximum(A[y:y + a.shape[0], x:x + a.shape[1]], a)
        x += a.shape[1] + space
    rgb = np.ones(A.shape + (3,), np.float32) * np.array(color, np.float32)
    return Sprite(rgb, A)


# ── 합성 ───────────────────────────────────────────
def warp_sprite(sp, M, canvas_wh, blur=0.0, motion=(0, 0)):
    """스프라이트를 affine M(2x3)으로 화면에 올릴 bbox 영역만 계산"""
    w, h = sp.size
    pts = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], np.float32) @ M.T
    pad = int(blur * 3 + abs(motion[0]) + abs(motion[1]) + 4)
    x0, y0 = np.floor(pts.min(0) - pad).astype(int)
    x1, y1 = np.ceil(pts.max(0) + pad).astype(int)
    W, H = canvas_wh
    x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1c <= x0c or y1c <= y0c:
        return None
    M2 = M.copy(); M2[:, 2] -= [x0c, y0c]
    size = (x1c - x0c, y1c - y0c)
    chans = [sp.a[..., None] * sp.rgb, sp.a[..., None]]
    if sp.acc is not None:
        chans.append((sp.a * sp.acc)[..., None])
    src = np.concatenate(chans, axis=2)
    out = cv2.warpAffine(src, M2, size, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    if out.ndim == 2:
        out = out[..., None]
    if blur > 0.4:  # 초점 흐림 (깊이)
        out = cv2.GaussianBlur(out, (0, 0), blur)
    mlen = math.hypot(*motion)
    if mlen > 2:  # 방향 흐림 (속도) — 초점 흐림과 별도
        k = int(min(mlen, 60)) | 1
        ker = np.zeros((k, k), np.float32)
        c = k // 2
        ang = math.atan2(motion[1], motion[0])
        for i in range(k):
            t = i - c
            ker[int(round(c + t * math.sin(ang))), int(round(c + t * math.cos(ang)))] = 1
        out = cv2.filter2D(out, -1, ker / ker.sum())
        if out.ndim == 2:
            out = out[..., None]
    return (x0c, y0c, x1c, y1c), out


def composite(canvas, accbuf, placed, shadow=True, opacity=1.0, shadow_dir=(22, 34)):
    box, out = placed
    x0, y0, x1, y1 = box
    prem, a = out[..., :3], out[..., 3:4] * opacity
    prem = prem * opacity
    if shadow:  # 길고 부드러운 접촉 그림자 → 종이 위에 놓인 느낌
        sa = cv2.GaussianBlur(a[..., 0], (0, 0), 16)
        dx, dy = shadow_dir
        sh = np.zeros_like(sa)
        hh, ww = sa.shape
        sh[max(0, dy):, max(0, dx):] = sa[:hh - max(0, dy), :ww - max(0, dx)]
        k = (sh * .38)[..., None]
        region = canvas[y0:y1, x0:x1]
        canvas[y0:y1, x0:x1] = region * (1 - k) + INK * k
    region = canvas[y0:y1, x0:x1]
    canvas[y0:y1, x0:x1] = region * (1 - a) + prem
    if out.shape[2] > 4:
        ab = accbuf[y0:y1, x0:x1]
        accbuf[y0:y1, x0:x1] = ab * (1 - a[..., 0]) + out[..., 4] * opacity
    else:
        accbuf[y0:y1, x0:x1] *= (1 - a[..., 0])


def affine(cx, cy, anchor, scale, rot_deg):
    ax, ay = anchor
    c, s = math.cos(math.radians(rot_deg)) * scale, math.sin(math.radians(rot_deg)) * scale
    return np.array([[c, -s, cx - (c * ax - s * ay)], [s, c, cy - (s * ax + c * ay)]], np.float32)


# ── 마감 (하프톤·복사기·색수차·비네트·라이트릭) ──────────
_HT = {}


def halftone_field(W, H, cell=7, ang=45):
    key = (W, H, cell)
    if key not in _HT:
        yy, xx = np.mgrid[:H, :W].astype(np.float32)
        c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        u, v = (xx * c + yy * s) / cell, (-xx * s + yy * c) / cell
        du, dv = u - np.floor(u) - .5, v - np.floor(v) - .5
        _HT[key] = np.sqrt(du * du + dv * dv) / .7071  # 0(중심)~1(모서리)
    return _HT[key]


def finish(canvas, accbuf, xerox, t_frame, seed, chaos, leak=0.0):
    H, W = canvas.shape[:2]
    L = lum(canvas)
    clean = 1 - np.clip(accbuf * 1.5, 0, 1)  # 히어로의 레드오렌지 영역은 열화를 약하게
    # 하프톤: 그림자·중간톤에만 (하이라이트는 깨끗하게)
    gate = 1 - smooth((L - .45) / .35)
    dark = cv2.GaussianBlur(1 - L, (0, 0), 1.5)
    dots = (halftone_field(W, H) < np.sqrt(np.clip(dark, 0, 1)) * 1.05).astype(np.float32)
    ht = 1 - (1 - dots) * .5
    k = (.28 + .14 * chaos) * gate * clean
    canvas *= (1 - k[..., None]) + (ht * k)[..., None]
    # 복사기 열화: multiply + overlay, 매 프레임 조금씩 다른 오프셋 (seed 결정)
    r = rng(seed, 'xerox', int(t_frame // 3))
    ox, oy = r.integers(0, 60), r.integers(0, 60)
    xr = np.roll(np.roll(xerox, oy, 0), ox, 1)
    xk = (.35 + .25 * chaos) * clean
    canvas *= 1 - (1 - xr[..., None]) * xk[..., None]
    ov = xr[..., None]
    over = np.where(canvas < .5, 2 * canvas * ov, 1 - 2 * (1 - canvas) * (1 - ov))
    canvas[:] = canvas * (1 - .12 * clean[..., None]) + over * (.12 * clean[..., None])
    # 가장자리 색수차 (절제)
    yy, xx = np.mgrid[:H, :W].astype(np.float32)
    cx, cy = W / 2, H / 2
    for ch, sc in ((0, 1.0025), (2, 0.9975)):
        mx = (cx + (xx - cx) / sc).astype(np.float32)
        my = (cy + (yy - cy) / sc).astype(np.float32)
        canvas[..., ch] = cv2.remap(canvas[..., ch], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # 비네트
    rr = ((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2
    canvas *= (1 - .22 * np.clip(rr - .25, 0, 1.5))[..., None]
    # 변색된 라이트릭 (전환 때만)
    if leak > 0:
        rl = rng(seed, 'leak', int(t_frame // 20))
        lx, ly = rl.uniform(0, W), rl.uniform(0, H * .6)
        g = np.exp(-(((xx - lx) / (W * .55)) ** 2 + ((yy - ly) / (H * .35)) ** 2))
        col = np.array([1.0, .78, .45], np.float32)
        canvas[:] = 1 - (1 - canvas) * (1 - (g * leak * .55)[..., None] * col)
    return np.clip(canvas, 0, 1)
