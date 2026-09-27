"""VOX 스타일 특별도슨트 숏츠 빌드.
  python3 -m vox.build                       # 새 seed로 25초 렌더 → output/
  python3 -m vox.build --seed 1987 --chaos .5
  python3 -m vox.build --stills 1.5,5,9 --seed 1987   # 정지 프레임만
음악 없음(무음 트랙). 컷·푸시인·등장은 config.BPM 박에 맞춰 떨어진다.
"""
import argparse, json, math, os, secrets, subprocess, sys, time
from multiprocessing import Pool
import numpy as np
import cv2
from PIL import Image
from . import config as C
from .engine import (ACCENT, CACHE, GREY, INK, PAPER, Sprite, affine, apply_edge, composite, duotone, ease_out_expo_overshoot,
                     finish, hue_mask, lum, pick_edge, rng, smooth, stepped, text_sprite, to_print, warp_sprite)
from .calli import calligraphy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = C.W, C.H, C.FPS
CX, CY = W / 2, H / 2
S = C.SAFE
F = lambda n: os.path.join(CACHE, n)


# ── 타이밍 ──────────────────────────────────────────
def timeline(bpm):
    beat = 60 / bpm
    t, out = C.FIRST_BEAT, []
    for sc in C.SCENES:
        dur = sc['beats'] * beat if sc['beats'] else C.DURATION - t
        out.append((sc, t, t + dur))
        t += dur
    return out, beat


# ── 소재 로드 ────────────────────────────────────────
class Assets:
    def __init__(self):
        self.paper = np.array(Image.open(F('paper.png')).convert('RGB'), np.float32) / 255
        self.xerox = np.array(Image.open(F('xerox.png')).convert('L').resize((W, H)), np.float32) / 255
        self.news = [np.array(Image.open(os.path.join(F('news'), n)).convert('RGBA'), np.float32) / 255 for n in sorted(os.listdir(F('news')))]
        self.cut = {}
        self.vid = {}
        for k, s in C.SOURCES.items():
            if s['kind'] == 'still':
                self.cut[k] = np.array(Image.open(F(f'cut_{k}.png')).convert('RGBA'), np.float32) / 255
            else:
                self.vid[k] = np.load(F(f'vid_{k}.npy'))


# ── 요소 ────────────────────────────────────────────
class El:
    """한 장의 오려 붙인 인쇄물. pos=화면 좌표(초기 카메라 기준), z=깊이(1=주제면, >1 배경, <1 전경)"""
    def __init__(self, name, sprite_fn, pos, z=1.0, scale=1.0, rot=0.0, enter=0.0, seed=0, chaos=.4,
                 shadow=True, opacity=1.0, stepped_in=True, band=None, is_hero=False):
        self.name, self.sprite_fn, self.pos, self.z = name, sprite_fn, np.array(pos, np.float32), z
        self.scale, self.rot, self.enter, self.shadow, self.opacity = scale, rot, enter, shadow, opacity
        self.stepped_in, self.band, self.is_hero = stepped_in, band, is_hero
        self.follow = 1.0  # 카메라를 따라가는 정도 (글자는 낮춤)
        r = rng(seed, 'enter', name)
        ang = r.uniform(0, 2 * math.pi)
        dist = 160 + 320 * chaos
        self.from_off = np.array([math.cos(ang) * dist, math.sin(ang) * dist], np.float32)
        self.from_rot = r.uniform(-1, 1) * (6 + 16 * chaos)
        self.from_scale = 1.1 + .15 * chaos


def lockup_sprite(descriptor, title, seed, chaos, title_size=132, desc_size=46, color=None, max_w=None):
    """얇은 설명 줄 + 굵은 제목 — 한 덩어리로 움직이는 타이틀 락업"""
    color = INK if color is None else color
    max_w = max_w or (S['right'] - S['left'] - 30)
    r = rng(seed, 'type', title)
    parts = []
    if descriptor:
        parts.append(text_sprite(descriptor, F('serif_400.ttf'), desc_size, color, jitter=chaos * .6, r=r))
    words, lines, cur = title.split(' '), [], ''
    from PIL import ImageFont
    font = ImageFont.truetype(F('serif_800.ttf'), title_size)
    for w_ in words:
        cand = (cur + ' ' + w_).strip()
        if font.getlength(cand) > max_w and cur:
            lines.append(cur); cur = w_
        else:
            cur = cand
    lines.append(cur)
    for ln in lines:
        parts.append(text_sprite(ln, F('serif_800.ttf'), title_size, color, jitter=chaos, r=r))
    Wl = max(p.size[0] for p in parts)
    gap = int(title_size * -.05)
    ys, y = [], 0
    for i, p in enumerate(parts):
        ys.append(y)
        y += p.size[1] + (int(desc_size * .3) if i == 0 and descriptor else gap)
    A = np.zeros((max(yy + p.size[1] for yy, p in zip(ys, parts)), Wl), np.float32)
    for yy, p in zip(ys, parts):
        A[yy:yy + p.size[1], :p.size[0]] = np.maximum(A[yy:yy + p.size[1], :p.size[0]], p.a)
    # 얇은 종이 테두리(깨끗한 컷) → 히어로 윗선과 겹쳐도 읽힘
    k = max(4, title_size // 16)
    A = np.pad(A, k + 2)
    border = cv2.GaussianBlur(cv2.dilate((A > .3).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))).astype(np.float32), (0, 0), 1)
    rgb = PAPER * (1 - A[..., None]) + np.asarray(color, np.float32) * A[..., None]
    return Sprite(rgb, np.maximum(A, border))


def card_sprite(w, h, color, r, chaos, torn):
    rgb = np.ones((h, w, 3), np.float32) * color
    a = np.ones((h, w), np.float32)
    if torn:
        _, a = apply_edge(rgb, a, 'rough', r, chaos, pad=0)
    return Sprite(rgb, a)


def treat(rgb, alpha, method, recolor_hue, rgb_u8=None):
    """히어로/보조 처리. method: None(보조, 흑백) | duotone | backing | selective"""
    if method == 'duotone':
        out, l = duotone(rgb)
        return out, np.clip((l - .35) / .5, 0, 1)
    out, l = to_print(rgb)
    if method == 'selective' and recolor_hue:
        m = hue_mask(rgb_u8 if rgb_u8 is not None else (rgb * 255).astype(np.uint8), recolor_hue)
        shade = (.55 + .45 * l)[..., None]
        out = out * (1 - m[..., None]) + ACCENT * shade * m[..., None]
        return out, m
    return out, None


def band_split(sp, n, seed, key, chaos):
    """사람 피사체: 가로 띠 3~6개로 잘라 각자 오프셋·회전·등장 시차 (인쇄가 어긋난 듯)"""
    h = sp.a.shape[0]
    r = rng(seed, 'bands', key)
    cuts = np.sort(r.uniform(.12, .88, n - 1)) if n > 1 else []
    ys = [0] + [int(c * h) for c in cuts] + [h]
    bands = []
    for i in range(n):
        y0, y1 = ys[i], ys[i + 1]
        if y1 - y0 < 4: continue
        acc = sp.acc[y0:y1] if sp.acc is not None else None
        bands.append(dict(sp=Sprite(sp.rgb[y0:y1], sp.a[y0:y1], acc), y0=y0, y1=y1,
                          dx=r.uniform(-1, 1) * (6 + 46 * chaos), rot=r.uniform(-1, 1) * (.3 + 2.2 * chaos),
                          delay=i * .12))
    return bands


# ── 장면 구성 ────────────────────────────────────────
class Scene:
    def __init__(self, sc, t0, t1, beat, A, seed, chaos, idx):
        self.sc, self.t0, self.t1, self.beat, self.A, self.seed, self.chaos, self.idx = sc, t0, t1, beat, A, seed, chaos, idx
        r = rng(seed, 'scene', sc['id'])
        self.r = r
        self.els = []
        self.leak = idx > 0 and r.random() < .55
        self.pull_back = r.random() < .4
        self.drift = np.array([r.uniform(-1, 1) * 9, r.uniform(-1, 1) * 7], np.float32)
        self.hero_pos = np.array([CX, CY], np.float32)
        self._scraps()
        getattr(self, 'build_' + ('title' if sc['id'] == 'title' else 'cta' if sc['id'] == 'cta' else 'feel' if sc['id'] == 'feel' else 'chapter'))()
        self.els.sort(key=lambda e: -e.z)  # 먼 것부터 그림

    # 배경: 신문 조각 (낮은 대비, seed 배치)
    def _scraps(self):
        r, ch = rng(self.seed, 'scraps', self.sc['id']), self.chaos
        pool = self.A.news
        n = int(6 + 6 * ch)
        for i in range(n):
            src = pool[r.integers(len(pool))]
            k = r.uniform(.5, 1.1)
            h, w = int(src.shape[0] * k), int(src.shape[1] * k)
            img = cv2.resize(src, (max(8, w), max(8, h)))
            rgb, a = img[..., :3], img[..., 3]
            prt, _ = to_print(rgb, contrast=.7, lift=.12)
            prt = prt * .45 + PAPER * .55  # 대비 낮춤 — 분위기일 뿐 읽히지 않게
            sp = Sprite(prt, a)
            pos = (r.uniform(-60, W + 60), r.uniform(80, H - 80))
            self.els.append(El(f'scrap{i}', lambda f, sp=sp: sp, pos, z=r.uniform(1.4, 1.9), rot=r.uniform(-1, 1) * (6 + 30 * ch),
                               enter=r.integers(0, 3) * .25, seed=self.seed, chaos=ch, opacity=r.uniform(.55, .9)))
        for i in range(0 if self.sc['id'] == 'cta' else 1 + int(2 * ch)):  # 전경 조각 (흐리게, 큰 시차)
            src = pool[r.integers(len(pool))]
            k = r.uniform(.9, 1.4)
            img = cv2.resize(src, (int(src.shape[1] * k), int(src.shape[0] * k)))
            prt, _ = to_print(img[..., :3], contrast=.8)
            sp = Sprite(prt * .7 + PAPER * .3, img[..., 3])
            side = r.choice([-1, 1])
            pos = (CX + side * r.uniform(480, 620), r.uniform(200, H - 200))
            self.els.append(El(f'fg{i}', lambda f, sp=sp: sp, pos, z=r.uniform(.62, .72), rot=r.uniform(-25, 25),
                               enter=r.integers(1, 5) * .25, seed=self.seed, chaos=ch, opacity=.95))

    def _accent_method(self, key):
        allowed = ['duotone', 'backing'] + (['selective'] if C.SOURCES[key].get('recolor_hue') else [])
        return allowed[rng(self.seed, 'accent', self.sc['id']).integers(len(allowed))]

    def _subject(self, key, pos, height, hero, enter, z=1.0, rot=0.0):
        """사진 컷아웃 또는 영상 프린트를 요소(띠 분할 포함)로 추가하고 화면 bbox를 돌려줌"""
        src = C.SOURCES[key]
        r = rng(self.seed, 'subject', self.sc['id'], key)
        ch = self.chaos
        method = self._accent_method(key) if hero else None
        edge = 'print' if src['kind'] == 'video' else pick_edge(r, ch, hero)
        rh = src.get('recolor_hue')

        if src['kind'] == 'still':
            cut = self.A.cut[key]
            rgb, a = cut[..., :3], cut[..., 3]
            out, acc = treat(rgb, a, method, rh)
            eo, ea = apply_edge(out, a, edge, r, ch)
            pad = (ea.shape[0] - a.shape[0]) // 2
            accp = np.pad(acc, pad) if acc is not None else None
            base = Sprite(eo, ea, accp)
            light = float((lum(out) * a).sum() / max(1, a.sum()))
            frames = None
        else:
            frames = self.A.vid[key]
            base = None
            light = 0.0
            a = np.ones(frames.shape[1:3], np.float32)
        sh, sw = (base.a.shape if base is not None else (frames.shape[1] + 2 * 24, frames.shape[2] + 2 * 24))
        scale = height / sh
        # 히어로 뒤 카드: 레드오렌지 배경지(backing) 또는 밝은 피사체용 회색 카드
        card = None
        if hero and method == 'backing':
            card = ('accent', ACCENT)
        elif light > .56:
            card = ('grey', GREY)
        if card:
            cw, chh = int(sw * (1.1 + .1 * ch)), int(sh * (.9 + .06 * ch))
            csp = card_sprite(cw, chh, card[1], r, ch, torn=r.random() < .5)
            if card[0] == 'accent':
                csp.acc = np.ones_like(csp.a)
            off = np.array([r.uniform(-1, 1) * 40, r.uniform(-1, 1) * 30 + 40], np.float32)
            self.els.append(El(f'{key}_card', lambda f, csp=csp: csp, pos + off, z=z + .02, scale=scale,
                               rot=rot + r.uniform(-1, 1) * (2 + 6 * ch), enter=enter, seed=self.seed, chaos=ch, is_hero=hero))

        def video_sprite(frame_local, key=key, method=method, rh=rh, r=r):
            fr = frames[int(frame_local * .63) % len(frames)]  # 2초 클립을 장면 길이에 맞춰 느리게
            rgb = fr.astype(np.float32) / 255
            out, acc = treat(rgb, None, method, rh, fr)
            eo, ea = apply_edge(out, np.ones(out.shape[:2], np.float32), 'print', r, ch)
            accp = np.pad(acc, 24) * (ea > 0) if acc is not None else None
            return Sprite(eo, ea, accp)

        n_bands = int(np.clip(3 + round(r.random() * (1 + 3 * ch)), 3, 6)) if src.get('person') else 1
        split_keys = rng(self.seed, 'bandsplit', self.sc['id'], key)
        cuts = np.sort(split_keys.uniform(.12, .88, n_bands - 1))
        ys = [0.0] + list(cuts) + [1.0]
        for bi in range(n_bands):
            y0f, y1f = ys[bi], ys[bi + 1]
            dx = split_keys.uniform(-1, 1) * (6 + 46 * ch) if n_bands > 1 else 0
            brot = split_keys.uniform(-1, 1) * (.3 + 2.2 * ch) if n_bands > 1 else 0

            def band_fn(f, y0f=y0f, y1f=y1f):
                sp = video_sprite(f) if frames is not None else base
                hh = sp.a.shape[0]
                y0, y1 = int(y0f * hh), int(y1f * hh)
                acc = sp.acc[y0:y1] if sp.acc is not None else None
                return Sprite(sp.rgb[y0:y1], sp.a[y0:y1], acc)
            # 띠 중심 위치 (전체 스프라이트 중심 기준)
            cy_off = ((y0f + y1f) / 2 - .5) * sh * scale
            bpos = pos + np.array([dx - math.sin(math.radians(rot)) * cy_off, math.cos(math.radians(rot)) * cy_off], np.float32)
            self.els.append(El(f'{key}_b{bi}', band_fn, bpos, z=z, scale=scale, rot=rot + brot,
                               enter=enter + bi * .25, seed=self.seed, chaos=ch, is_hero=hero))
        if hero:
            self.hero_pos = np.array(pos, np.float32)
        top = pos[1] - sh * scale / 2
        return dict(top=top, bottom=pos[1] + sh * scale / 2, left=pos[0] - sw * scale / 2, right=pos[0] + sw * scale / 2)

    def _type(self, name, sprite, pos, enter, z=.98, rot=0.0):
        el = El(name, lambda f, sp=sprite: sp, pos, z=z, rot=rot, enter=enter, seed=self.seed, chaos=self.chaos)
        el.follow = .3
        self.els.append(el)

    def _calli(self, text, size, pos, start_beat, dur_beats, color=None, z=.96, hero=False):
        key = self.sc['id'] + text
        b = self.beat * FPS
        rot = rng(self.seed, 'callirot', key).uniform(-1, 1) * (2 + 5 * self.chaos)

        def fn(f, text=text):
            p = np.clip(f / (dur_beats * b), 0, 1)
            sp = calligraphy(text, size, p, self.seed, key, self.chaos, color=color)
            if hero and color is not None:
                sp.acc = (np.abs(sp.rgb - ACCENT).sum(-1) < .2).astype(np.float32) * sp.a
            return sp
        el = El('calli_' + text, fn, pos, z=z, rot=rot, enter=start_beat, seed=self.seed, chaos=self.chaos, stepped_in=False, is_hero=hero)
        el.from_off *= 0; el.from_rot = 0; el.from_scale = 1.04  # 글씨는 제자리에서 써진다
        el.follow = .45
        self.els.append(el)

    # 1) 타이틀
    def build_title(self):
        sc, ch, r = self.sc, self.chaos, self.r
        for k in sc.get('support', []):
            self._subject(k, (CX - 250 + r.uniform(-1, 1) * 60 * ch, 980), 820, False, .5, z=1.25, rot=r.uniform(-1, 1) * (3 + 8 * ch))
        hb = self._subject(sc['hero'], (CX + 60 + r.uniform(-1, 1) * 50 * ch, 1030), 1040, True, 1.5)
        lk = lockup_sprite(sc['descriptor'], sc['title'], self.seed, ch)
        lh = lk.size[1]
        # 제목 아래쪽이 히어로의 머리(윗선)를 덮도록 → 두 레이어가 맞물림
        y = max(S['top'] + lh / 2, hb['top'] + lh * .5 - lh * .35 + 30)
        self._type('lockup', lk, (S['left'] + 40 + lk.size[0] / 2, y), 1.0)

    # 2~5) 영상 챕터 + 키네틱 캘리그래피
    def build_chapter(self):
        sc, ch, r = self.sc, self.chaos, self.r
        side = r.choice([-1, 1])
        src = C.SOURCES[sc['hero']]
        h = 1180 if src['kind'] == 'video' else 1120
        hb = self._subject(sc['hero'], (CX - 30 + side * 30 * ch, 1010), h, True, 1.5, rot=r.uniform(-1, 1) * (1 + 3 * ch))
        size = 330
        self._calli(sc['calli'], size, (CX - 40 + side * 60, max(S['top'] + 200, hb['top'] + 60)), .5, 1.5)
        lab = lockup_sprite(sc['en'], sc['label'], self.seed, ch, title_size=86, desc_size=30)
        self._type('label', lab, (S['left'] + 30 + lab.size[0] / 2, S['top'] + 10 + lab.size[1] / 2), 1.0)

    # 6) 아는 것을 넘어, 함께 느끼는 역사
    def build_feel(self):
        sc, ch, r = self.sc, self.chaos, self.r
        hb = self._subject(sc['hero'], (CX + 180, 1020), 1180, True, 1.5, rot=r.uniform(-1, 1) * (1 + 3 * ch))
        d = lockup_sprite(None, sc['descriptor'], self.seed, ch, title_size=64)
        self._type('desc', d, (S['left'] + 40 + d.size[0] / 2, S['top'] + 60), .5)
        self._calli('함께\n느끼는\n역사', 250, (CX - 110, 880), 1.0, 2.0)

    # 7) CTA
    def build_cta(self):
        sc, ch, r = self.sc, self.chaos, self.r
        self._subject('cloth', (CX + 250, 760), 620, False, .5, z=1.3, rot=r.uniform(3, 8))
        lk = lockup_sprite(sc['descriptor'], sc['title'], self.seed, ch, title_size=84, desc_size=44)
        self._type('lockup', lk, (S['left'] + 20 + lk.size[0] / 2, S['top'] + 30 + lk.size[1] / 2), 1.0)
        y = 1250
        for i, ln in enumerate(sc['lines']):
            sp = text_sprite(ln, F('serif_400.ttf') if i else F('serif_800.ttf'), 50, INK, jitter=ch * .5, r=rng(self.seed, 'cta', i))
            self._type(f'line{i}', sp, (S['left'] + 20 + sp.size[0] / 2, y + i * 78), 1.0 + i * .5)
        # 히어로: '무료' — 제목 단어 자체가 히어로라 레드오렌지를 가질 수 있다
        self._calli(sc['hero_word'], 470, (CX - 90, 880), 2.5, 1.0, color=ACCENT, hero=True, z=.94)
        self.hero_pos = np.array([CX - 90, 880], np.float32)

    # ── 카메라: 느린 연속 드리프트 + 박에 맞춘 결정적 푸시인 (히어로로) ──
    def camera(self, t):
        lt = t - self.t0
        lb = lt / self.beat
        d = .012 * lt
        if self.pull_back:
            d += .06 * (1 - ease_out_expo_overshoot(lb / 1.0, 0))
        n_beats = (self.t1 - self.t0) / self.beat
        pushes = [b for b in (3, 5, 7) if b < n_beats - .5] if self.sc['id'] != 'cta' else [2.5]
        pull = np.zeros(2, np.float32)
        for pb in pushes:
            e = ease_out_expo_overshoot((lb - pb) * self.beat * FPS / 9, .05) if lb >= pb else 0
            d += .045 * e
            pull += (self.hero_pos - np.array([CX, CY])) * .05 * e
        cam = self.drift * lt + pull
        if self.sc['id'] == 'cta':  # 21초 무렵부터는 읽기 좋게 거의 멈춤
            cam *= .4; d = min(d, .06)
        return cam, d


def project(el, cam, d):
    cam, d = cam * el.follow, d * el.follow
    k = el.z / (el.z - d)
    p = np.array([CX, CY]) + (el.pos - np.array([CX, CY])) * k - cam / el.z * k
    return p, k


def render_frame(i):
    t = i / FPS
    sc = next((s for s in SCENES if s.t0 <= t < s.t1), SCENES[-1])
    canvas = ASSETS.paper.copy()
    accbuf = np.zeros((H, W), np.float32)
    if t < C.FIRST_BEAT:
        return (finish(canvas, accbuf, ASSETS.xerox, i, SEED, CHAOS) * 255).astype(np.uint8)
    cam, d = sc.camera(t)
    lf = (t - sc.t0) * FPS
    bf = sc.beat * FPS
    for el in sc.els:
        ef = lf - el.enter * bf
        if ef < 0:
            continue
        dur = .45 * FPS
        # 등장: 12fps 계단으로 '툭' 붙고, 안착 후에는 부드럽게
        if el.stepped_in and ef < dur:
            efd = stepped(ef)
            prev = max(0, efd - C.FPS / 12)
        else:
            efd, prev = ef, ef - 1
        p = ease_out_expo_overshoot(efd / dur)
        pp = ease_out_expo_overshoot(max(0, prev) / dur)
        off, poff = el.from_off * (1 - p), el.from_off * (1 - pp)
        sp = el.sprite_fn(lf - el.enter * bf) if callable(el.sprite_fn) else el.sprite_fn
        pos, k = project(el, cam, d)
        scale = el.scale * k * (el.from_scale + (1 - el.from_scale) * p)
        rot = el.rot + el.from_rot * (1 - p)
        M = affine(pos[0] + off[0], pos[1] + off[1], (sp.size[0] / 2, sp.size[1] / 2), scale, rot)
        motion = (off - poff) * .5 if ef < dur else (0, 0)
        defocus = (1 - el.z) * 14 if el.z < .8 else max(0, el.z - 1.2) * 2.5
        placed = warp_sprite(sp, M, (W, H), blur=defocus, motion=motion)
        if placed:
            fade = np.clip(ef / 2, 0, 1) if el.stepped_in else 1
            composite(canvas, accbuf, placed, shadow=el.shadow, opacity=el.opacity * fade)
    leak = 0.0
    if sc.leak:
        leak = float(np.clip(1 - lf / 10, 0, 1))
    out = finish(canvas, accbuf, ASSETS.xerox, i, SEED, CHAOS, leak=leak)
    tail = C.DURATION - C.END_FADE
    if t > tail:  # 빈 종이로 돌아가 루프 연결
        k = smooth((t - tail) / C.END_FADE)
        out = out * (1 - k) + ASSETS.paper * k
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


SCENES, ASSETS, SEED, CHAOS = None, None, None, None


def setup(seed, chaos, bpm):
    global SCENES, ASSETS, SEED, CHAOS
    SEED, CHAOS = seed, chaos
    ASSETS = Assets()
    tl, beat = timeline(bpm)
    SCENES = [Scene(sc, t0, t1, beat, ASSETS, seed, chaos, i) for i, (sc, t0, t1) in enumerate(tl)]
    return tl, beat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=C.SEED)
    ap.add_argument('--chaos', type=float, default=C.CHAOS)
    ap.add_argument('--bpm', type=float, default=C.BPM)
    ap.add_argument('--out', default=None)
    ap.add_argument('--stills', default=None)
    ap.add_argument('--workers', type=int, default=os.cpu_count())
    ap.add_argument('--version', default='v2.0')
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else secrets.randbelow(10 ** 6)
    tl, beat = setup(seed, a.chaos, a.bpm)
    print(f'seed={seed} chaos={a.chaos} bpm={a.bpm} (1박 {beat:.3f}s)')
    for sc, t0, t1 in tl:
        print(f'  {sc["id"]:6s} {t0:6.2f}s ~ {t1:6.2f}s')
    os.makedirs(os.path.join(ROOT, 'output'), exist_ok=True)
    if a.stills:
        od = os.path.join(ROOT, 'out', f'vox_{seed}'); os.makedirs(od, exist_ok=True)
        for s in a.stills.split(','):
            fr = render_frame(int(float(s) * FPS))
            Image.fromarray(fr).save(os.path.join(od, f't{float(s):05.2f}.png'))
        print('stills →', od); return
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    out = a.out or os.path.join(ROOT, 'output', f'memorial_docent_shorts_{a.version}.mp4')
    n = int(C.DURATION * FPS)
    cmd = [ff, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', str(C.DURATION),
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-color_range', 'tv',
           '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart', out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(a.workers) as pool:
        for j, fr in enumerate(pool.imap(render_frame, range(n), chunksize=4)):
            proc.stdin.write(fr.tobytes())
            if j % 75 == 0:
                print(f'  frame {j}/{n}  {time.time() - t0:.0f}s', flush=True)
    proc.stdin.close(); proc.wait()
    meta = dict(seed=seed, chaos=a.chaos, bpm=a.bpm, first_beat=C.FIRST_BEAT,
                cuts=[round(t0, 3) for _, t0, _ in tl], file=os.path.basename(out))
    json.dump(meta, open(out.replace('.mp4', '.json'), 'w'), ensure_ascii=False, indent=1)
    print('done', out, f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
