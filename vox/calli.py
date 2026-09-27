"""키네틱 캘리그래피 — 붓으로 한 획씩 써 내려가는 듯한 글자 등장.
글자마다 '쓰는 순서' 지도(위→아래, 왼쪽→오른쪽 + 붓 끝 노이즈)를 만들고 진행도에 따라 드러낸다.
먹 번짐(쓰는 순간 살짝 부풀었다 가라앉음) + 마른 붓결(Higgsfield 먹 질감) + 먹 방울.
그리는 동작이므로 12fps 계단 없이 풀 프레임으로 움직인다.
"""
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from .engine import CACHE, INK, PAPER, Sprite, rng

_cache = {}


def _glyph(ch, size):
    key = (ch, size)
    if key not in _cache:
        font = ImageFont.truetype(os.path.join(CACHE, 'brush.ttf'), size)
        bb = font.getbbox(ch)
        w, h = max(8, bb[2] - bb[0]), max(8, bb[3] - bb[1])
        pad = size // 6
        im = Image.new('L', (w + 2 * pad, h + 2 * pad), 0)
        ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), ch, font=font, fill=255)
        _cache[key] = np.array(im, np.float32) / 255
    return _cache[key]


_streak = None


def _streak_tex(h, w, r):
    global _streak
    if _streak is None:
        _streak = np.array(Image.open(os.path.join(CACHE, 'streak.png')).convert('L'), np.float32) / 255
    s = _streak
    y, x = r.integers(0, max(1, s.shape[0] - 10)), r.integers(0, max(1, s.shape[1] - 10))
    tile = np.roll(np.roll(s, -y, 0), -x, 1)
    tile = cv2.resize(tile, (w, h), interpolation=cv2.INTER_LINEAR)
    return tile


def calligraphy(text, size, progress, seed, key, chaos=0.4, color=None, sticker=True):
    """progress: 0~1 (전체 글자 쓰기 진행도). 줄바꿈은 '\n'."""
    color = INK if color is None else np.asarray(color, np.float32)
    lines = text.split('\n')
    chars = [c for c in text if c not in ' \n']
    n = max(1, len(chars))
    rows, ci = [], 0
    for li, line in enumerate(lines):
        tiles = []
        for ch in line:
            if ch == ' ':
                tiles.append(None); continue
            g = _glyph(ch, size)
            r = rng(seed, 'calli', key, ci)
            h, w = g.shape
            yy, xx = np.mgrid[:h, :w].astype(np.float32)
            order = .62 * yy / h + .38 * xx / w + (r.random((h // 12 + 2, w // 12 + 2)).astype(np.float32).repeat(12, 0).repeat(12, 1)[:h, :w] - .5) * .16
            order = cv2.GaussianBlur(order, (0, 0), 3)
            local = np.clip(progress * n - ci, 0, 1.0001)  # 이 글자 진행도
            front = local * 1.12 - .06
            reveal = np.clip((front - order) / .05 + .5, 0, 1) if local > 0 else np.zeros_like(order)
            bleed = np.clip(1 - abs(local - .7) / .3, 0, 1) if 0 < local < 1 else 0  # 쓰는 중 먹 번짐
            gl = g
            if bleed > 0:
                gl = np.clip(cv2.GaussianBlur(g, (0, 0), 1.5 + 2 * bleed) * (1 + .6 * bleed), 0, 1)
            streak = _streak_tex(h, w, r)
            dry = np.clip(.78 + .45 * streak - .25 * (order > .75), 0, 1)  # 획 끝은 마른 붓
            a = gl * reveal * dry
            # 기울기·크기 흔들림 (chaos)
            rot = r.uniform(-1, 1) * (1.5 + 5 * chaos)
            sc = 1 + r.uniform(-1, 1) * .06 * chaos
            M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, sc)
            a = cv2.warpAffine(a, M, (w, h))
            tiles.append((a, r.uniform(-1, 1) * size * .05 * chaos, local))
            ci += 1
        rows.append(tiles)
    # 배치
    gap = int(size * -.08)
    row_imgs = []
    for tiles in rows:
        ws = [t[0].shape[1] if t else int(size * .35) for t in tiles]
        hh = max([t[0].shape[0] for t in tiles if t] + [size])
        W = sum(ws) + gap * (len(tiles) - 1)
        A = np.zeros((hh + size // 5, max(W, 1)), np.float32)
        x = 0
        for t, w in zip(tiles, ws):
            if t:
                a, dy, _ = t
                y = int(max(0, min(A.shape[0] - a.shape[0], size * .08 + dy)))
                A[y:y + a.shape[0], x:x + a.shape[1]] = np.maximum(A[y:y + a.shape[0], x:x + a.shape[1]], a)
            x += w + gap
        row_imgs.append(A)
    Wm = max(a.shape[1] for a in row_imgs)
    lh = int(size * .9)
    A = np.zeros((lh * (len(row_imgs) - 1) + row_imgs[-1].shape[0], Wm), np.float32)
    for i, a in enumerate(row_imgs):
        x = (Wm - a.shape[1]) // 2 if len(row_imgs) > 1 else 0
        A[i * lh:i * lh + a.shape[0], x:x + a.shape[1]] = np.maximum(A[i * lh:i * lh + a.shape[0], x:x + a.shape[1]], a)
    # 먹 방울 (글자가 다 써질 때 튐)
    if progress > .15:
        rs = rng(seed, 'splat', key)
        splats = sorted(os.listdir(os.path.join(CACHE, 'splat')))
        for i in range(int(3 + 4 * chaos)):
            when = rs.uniform(.2, 1)
            if progress < when or not splats:
                continue
            s = np.array(Image.open(os.path.join(CACHE, 'splat', splats[rs.integers(len(splats))])), np.float32) / 255
            k = rs.uniform(.25, .9) * size / 160
            s = cv2.resize(s, (max(3, int(s.shape[1] * k)), max(3, int(s.shape[0] * k))))
            y, x = rs.integers(0, max(1, A.shape[0] - s.shape[0])), rs.integers(0, max(1, A.shape[1] - s.shape[1]))
            A[y:y + s.shape[0], x:x + s.shape[1]] = np.maximum(A[y:y + s.shape[0], x:x + s.shape[1]], s)
    pad = int(size * .12)
    A = np.pad(A, pad)
    rgb = np.ones(A.shape + (3,), np.float32) * color
    if sticker:  # 깨끗한 컷 + 얇은 종이 테두리 → 어두운 영상 위에서도 읽힘
        k = max(6, size // 24)
        border = cv2.dilate((A > .25).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))).astype(np.float32)
        border = cv2.GaussianBlur(border, (0, 0), 1.2)
        rgb = PAPER * (1 - A[..., None]) + rgb * A[..., None]
        A = np.maximum(A, border)
    return Sprite(rgb, A)
