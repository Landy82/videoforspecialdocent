"""소재 준비 — UI 없이 배치로 돌릴 수 있는 스크립트.
  python3 -m vox.prep            (결과: .vox_cache/)
1) 사진: 로컬 배경 제거(rembg, u2net_human_seg) → 배경 없는 흑백 컷아웃(+원본 색, 재채색용)
2) 영상: public/clips 의 편집용 클립을 프레임 배열로 캐시
3) Higgsfield 생성 재료: 신문 조각 풀 추출 / 종이 / 먹 붓 질감 / 복사기 질감 (없으면 수식으로 대체)
4) 폰트: woff2 → ttf 변환
"""
import json, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image
from . import config as C

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, '.vox_cache')
GEN = os.path.join(ROOT, 'assets', 'generated')
os.makedirs(CACHE, exist_ok=True)
rng = np.random.default_rng(1960)


def p(*a):
    return os.path.join(CACHE, *a)


# ── 폰트 ───────────────────────────────────────────
def fonts():
    from fontTools.ttLib import TTFont
    nm = os.path.join(ROOT, 'node_modules', '@fontsource')
    todo = {
        'serif_800.ttf': f'{nm}/nanum-myeongjo/files/nanum-myeongjo-korean-800-normal.woff2',
        'serif_400.ttf': f'{nm}/nanum-myeongjo/files/nanum-myeongjo-korean-400-normal.woff2',
        'brush.ttf': f'{nm}/nanum-brush-script/files/nanum-brush-script-korean-400-normal.woff2',
    }
    for out, src in todo.items():
        if not os.path.exists(p(out)):
            f = TTFont(src); f.flavor = None; f.save(p(out))
    for w in ('Light', 'Medium', 'Bold'):
        src = os.path.join(ROOT, 'node_modules', 'pretendard', 'dist', 'public', 'static', f'Pretendard-{w}.otf')
        dst = p(f'sans_{w.lower()}.otf')
        if not os.path.exists(dst):
            with open(src, 'rb') as a, open(dst, 'wb') as b: b.write(a.read())


# ── 사진 컷아웃 ─────────────────────────────────────
def cutouts():
    from rembg import new_session, remove
    sess = None
    for key, s in C.SOURCES.items():
        if s['kind'] != 'still' or os.path.exists(p(f'cut_{key}.png')):
            continue
        sess = sess or new_session('u2net_human_seg' if s.get('person') else 'u2net')
        im = Image.open(os.path.join(ROOT, s['src'])).convert('RGB')
        rgba = np.array(remove(im, session=sess, post_process_mask=True))
        a = rgba[..., 3]
        ys, xs = np.where(a > 20)
        t, b, l, r = ys.min(), ys.max(), xs.min(), xs.max()
        crop = rgba[t:b + 1, l:r + 1]
        Image.fromarray(crop).save(p(f'cut_{key}.png'))  # 원본 색 유지(재채색·밝기 판정용), 흑백 변환은 합성 단계에서
        print('cutout', key, crop.shape)


# ── 영상 프레임 캐시 ─────────────────────────────────
def videos():
    idx = json.load(open(os.path.join(ROOT, 'public', 'clips', 'index.json')))
    for key, s in C.SOURCES.items():
        if s['kind'] != 'video' or os.path.exists(p(f'vid_{key}.npy')):
            continue
        clip = next((c for c in idx if c['shoot'] == s['shoot'] and s['part'] in c['parts']), None)
        if clip is None:
            clip = idx[0]; print(f'  (미리보기) {key} 원본 없음 → {clip["id"]} 대체')
        cap = cv2.VideoCapture(os.path.join(ROOT, 'public', clip['file']))
        start = (s['part'] - clip['parts'][0]) * 60 if s['part'] in clip['parts'] else 0
        frames, i = [], 0
        while True:
            ok, f = cap.read()
            if not ok: break
            if i >= start and len(frames) < 64:
                frames.append(cv2.resize(f[..., ::-1], (720, 1280), interpolation=cv2.INTER_AREA))
            i += 1
        np.save(p(f'vid_{key}.npy'), np.stack(frames))
        print('video', key, len(frames))


# ── 신문 조각 풀 ─────────────────────────────────────
def news_pool():
    out = p('news'); os.makedirs(out, exist_ok=True)
    if os.listdir(out):
        return
    n = 0
    for name in C.GENERATED['news']:
        f = os.path.join(GEN, name)
        if not os.path.exists(f):
            continue
        im = np.array(Image.open(f).convert('RGB'))
        g = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY)
        m = (g > 70).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        k, lab, st, _ = cv2.connectedComponentsWithStats(m)
        for i in range(1, k):
            x, y, w, h, area = st[i]
            if area < 12000: continue
            a = (lab[y:y + h, x:x + w] == i).astype(np.uint8) * 255
            a = cv2.GaussianBlur(a, (3, 3), 0)
            rgba = np.dstack([im[y:y + h, x:x + w], a])
            Image.fromarray(rgba).save(os.path.join(out, f'n{n:02d}.png')); n += 1
    if n == 0:  # 대체: 수식으로 만든 신문 조각
        for n in range(14):
            h, w = rng.integers(260, 620), rng.integers(260, 560)
            img = np.full((h, w), 205, np.uint8)
            for y in range(24, h - 20, 11):   # 읽히지 않는 활자 줄
                for x0 in range(18, w - 30, 150):
                    ln = rng.integers(60, 135)
                    img[y:y + 4, x0:x0 + ln] = rng.integers(95, 140)
            if rng.random() < .5:
                y0, x0 = rng.integers(20, h // 2), rng.integers(10, w // 3)
                img[y0:y0 + h // 3, x0:x0 + w // 2] = 150
            img = cv2.GaussianBlur(img, (3, 3), 0)
            a = np.full((h, w), 255, np.uint8)
            edge = (rng.random((h, w)) * 18).astype(int)
            yy, xx = np.mgrid[:h, :w]
            d = np.minimum.reduce([yy, xx, h - 1 - yy, w - 1 - xx])
            a[d < cv2.GaussianBlur(edge.astype(np.float32), (0, 0), 6) + 4] = 0
            Image.fromarray(np.dstack([img, img, img, a])).save(os.path.join(out, f'n{n:02d}.png'))
    print('news pool', len(os.listdir(out)))


def textures():
    def gen(name):
        f = os.path.join(GEN, name)
        return np.array(Image.open(f).convert('RGB')) if os.path.exists(f) else None
    # 종이 바탕
    if not os.path.exists(p('paper.png')):
        im = gen(C.GENERATED['paper'])
        if im is None:
            im = np.ones((H, W, 3)) * np.array(C.PAPER) + rng.normal(0, 3.5, (H, W, 1))
            im += cv2.GaussianBlur(rng.normal(0, 6, (H, W)), (0, 0), 40)[..., None]
        im = cv2.resize(np.clip(im, 0, 255).astype(np.uint8), (C.W, C.H), interpolation=cv2.INTER_AREA)
        # 팔레트 고정: 평균을 PAPER로 맞추고 명암 변화만 남긴다
        l = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY).astype(np.float32)
        l = (l - l.mean()) * 0.8
        out = np.clip(np.array(C.PAPER, np.float32)[None, None] + l[..., None], 0, 255).astype(np.uint8)
        Image.fromarray(out).save(p('paper.png'))
    # 먹 붓 질감 (결 방향 줄무늬) + 튄 먹 방울
    if not os.path.exists(p('streak.png')):
        im = gen(C.GENERATED['ink'])
        if im is not None:
            g = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY)
            ink = (g < 110).astype(np.uint8)
            k, lab, st, _ = cv2.connectedComponentsWithStats(ink)
            os.makedirs(p('splat'), exist_ok=True)
            ns = 0
            for i in range(1, k):
                x, y, w, h, area = st[i]
                if 30 < area < 6000:
                    a = (lab[y:y + h, x:x + w] == i).astype(np.uint8) * 255
                    Image.fromarray(a).save(p('splat', f's{ns:02d}.png')); ns += 1
            big = sorted(range(1, k), key=lambda i: -st[i][4])[0]
            x, y, w, h, _ = st[big]
            streak = 255 - g[y:y + h, x:x + w]
        else:
            n = rng.random((64, 900)).astype(np.float32)
            streak = cv2.resize(cv2.GaussianBlur(n, (0, 0), 1.2), (900, 900), interpolation=cv2.INTER_LINEAR)
            streak = (np.clip((streak - .35) * 3, 0, 1) * 255).astype(np.uint8)
            os.makedirs(p('splat'), exist_ok=True)
            for s in range(12):
                r = rng.integers(4, 16); a = np.zeros((r * 4, r * 4), np.uint8)
                cv2.circle(a, (r * 2, r * 2), r, 255, -1)
                Image.fromarray(a).save(p('splat', f's{s:02d}.png'))
        Image.fromarray(streak).save(p('streak.png'))
    # 복사기 열화 질감
    if not os.path.exists(p('xerox.png')):
        im = gen(C.GENERATED['xerox'])
        if im is None:
            g = 255 - np.clip(np.abs(rng.normal(0, 18, (H, W))), 0, 255)
            g -= (rng.random((1, W)) < .01) * 40
            im = np.clip(g, 0, 255).astype(np.uint8)
        else:
            im = cv2.cvtColor(cv2.resize(im, (C.W, C.H)), cv2.COLOR_RGB2GRAY)
        Image.fromarray(im.astype(np.uint8)).save(p('xerox.png'))


H, W = C.H, C.W

if __name__ == '__main__':
    fonts(); textures(); news_pool(); videos()
    if '--no-cutout' not in sys.argv:
        cutouts()
    print('prep done →', CACHE)
