"""부마민주항쟁 × 특별도슨트 홍보 숏폼 (실물 영상만 사용)
- 촬영 영상(1080×1920 변환본) 위에 날짜 카드·진행 그래픽·자막만 얹는다. AI 생성 이미지·영상 없음.
- 음악 없음(무음) + 마지막 배우 원음 대사 한 줄. 음악은 Edits에서 입힌다.
  python3 docu/render.py <영상 폴더> <출력.mp4>
"""
import math, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
SAFE_L, SAFE_R, SAFE_T, SAFE_B = 60, 930, 250, 1520
ACCENT = (232, 73, 42)
PAPER = (237, 230, 216)
FONT_DIR = os.environ.get('FONT_DIR', 'fonts')
F_SERIF = os.path.join(FONT_DIR, 'serif_800.ttf')
F_SERIF_R = os.path.join(FONT_DIR, 'serif_400.ttf')
F_SANS = os.path.join(FONT_DIR, 'Pretendard-Bold.otf')
F_SANS_B = os.path.join(FONT_DIR, 'Pretendard-Black.otf')

# ── 소스 (변환본 파일명, 원본 fps) ──────────────────────
SRC = {
    'yusin': ('px_5fdb044c.mp4', 60),     # 유신 현수막 앞 배우 (120fps 원본 → 60fps)
    'spot': ('px_2f255e51.mp4', 30),      # 스포트라이트 속 남성 배우
    'woman': ('px_bfd61af1.mp4', 30),     # 여성 독백 장면
    'draw': ('px_083bac20.mp4', 60),      # 여성 무용수 + 대형 일러스트
    'sign': ('px_cce6e17c.mp4', 60),      # 피켓 (240fps 원본 → 60fps)
    'final': ('px_84bf313a.mp4', 30),     # 마무리 내레이션
}

# ── 타임라인: (시작초, 끝초, 소스, 소스시작초, 속도, 카드) ──────────
# 카드 종류: hook / date / day / turn / montage / voice / cta
DAYS = ['16', '17', '18', '19', '20']
SHOTS = [
    (0.0, 3.0, 'yusin', 14.0, .5, dict(kind='hook', l1='1979년 10월,', l2='부산과 마산에서')),
    (3.0, 5.5, 'spot', 18.0, 1, dict(kind='date', date='1972. 10', text='유신헌법 선포')),
    (5.5, 8.0, 'yusin', 22.0, .5, dict(kind='date', date='1975. 05', text='긴급조치 9호', sub='집회와 시위 금지')),
    (8.0, 10.5, 'spot', 40.0, 1, dict(kind='date', date='1979. 10. 04', text='김영삼 의원', sub='국회의원직 제명')),
    (10.5, 14.0, 'sign', 5.0, .5, dict(kind='day', day=0, place='부산', text='부산대에서', sub='시위가 시작되다')),
    (14.0, 17.0, 'draw', 3.0, .5, dict(kind='day', day=1, place='부산', text='시민들이', sub='거리로')),
    (17.0, 20.0, 'yusin', 16.0, .5, dict(kind='day', day=2, place='부산', text='0시,', sub='비상계엄 선포')),
    (20.0, 23.0, 'woman', 45.0, 1, dict(kind='day', day=3, place='마산', text='마산으로', sub='번진 시위')),
    (23.0, 26.0, 'spot', 91.0, 1, dict(kind='day', day=4, place='마산·창원', text='정오,', sub='위수령 발동')),
    (26.0, 29.5, 'draw', 64.0, .5, dict(kind='date', date='1979. 10. 26', text='18년 유신체제의 끝')),
    (29.5, 32.0, 'sign', 38.0, .5, dict(kind='turn', l1='그 역사를,', l2='몸으로 기억하다')),
    (32.0, 33.5, 'woman', 68.0, 1, dict(kind='montage')),
    (33.5, 35.0, 'spot', 60.0, 1, dict(kind='montage')),
    (35.0, 36.5, 'sign', 15.0, .5, dict(kind='montage')),
    (36.5, 38.0, 'draw', 57.0, .5, dict(kind='montage')),
    (38.0, 40.0, 'woman', 77.0, 1, dict(kind='montage')),
    (40.0, 45.5, 'final', 29.6, 1, dict(kind='voice', text='"우리가 대한민국의 주인입니다."')),
    (45.5, 52.0, 'final', 35.1, 1, dict(kind='cta')),
]
DURATION = SHOTS[-1][1]
VOICE = (40.0, 'final', 29.6, 5.4)  # (영상 시각, 소스, 소스 시작, 길이) — 원음 사용 구간


def font(path, size):
    return ImageFont.truetype(path, size)


def text_img(txt, path, size, fill=(255, 255, 255), stroke=3):
    f = font(path, size)
    bb = f.getbbox(txt, stroke_width=stroke)
    im = Image.new('RGBA', (bb[2] - bb[0] + 8, bb[3] - bb[1] + 12), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - bb[0], 6 - bb[1]), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 160))
    return im


def ease(t):
    t = min(max(t, 0), 1)
    return 1 - (1 - t) ** 3


def paste(canvas, im, x, y, alpha=1.0, dy=0):
    if alpha <= 0:
        return
    if alpha < 1:
        a = np.array(im)
        a[..., 3] = (a[..., 3] * alpha).astype(np.uint8)
        im = Image.fromarray(a)
    canvas.alpha_composite(im, (int(x), int(y + dy)))


def reveal(canvas, im, x, y, t, delay=0.0):
    """아래에서 살짝 올라오며 나타나기"""
    p = ease((t - delay) / 0.35)
    paste(canvas, im, x, y, p, dy=(1 - p) * 40)


def typed(txt, t, delay, cps=14):
    n = int(max(0, t - delay) * cps)
    return txt[:n]


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


def scrim(g, top=.55, bottom=.75):
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    k = np.clip((.35 - y) / .35, 0, 1) * top + np.clip((y - .5) / .5, 0, 1) * bottom
    return g * (1 - k)


def day_bar(canvas, cur, place, t):
    """10.16 → 10.20 날짜 진행 그래픽 (현재 날짜만 레드오렌지)"""
    x0, y0, step = SAFE_L + 20, SAFE_T + 30, 160
    lab = text_img('1979. 10.', F_SANS, 34, fill=(220, 220, 220))
    paste(canvas, lab, x0, y0 - 52)
    d = ImageDraw.Draw(canvas)
    d.line([(x0 + 30, y0 + 52), (x0 + 30 + step * 4, y0 + 52)], fill=(255, 255, 255, 110), width=4)
    prog = ease(t / .5)
    xe = x0 + 30 + step * (cur - 1 + prog) if cur > 0 else x0 + 30
    d.line([(x0 + 30, y0 + 52), (xe, y0 + 52)], fill=ACCENT + (255,), width=6)
    for i, dd in enumerate(DAYS):
        on = i == cur
        col = ACCENT if on else ((255, 255, 255) if i < cur else (150, 150, 150))
        cx = x0 + 30 + step * i
        r = 13 if on else 8
        d.ellipse([cx - r, y0 + 52 - r, cx + r, y0 + 52 + r], fill=col + (255,))
        im = text_img(dd, F_SANS_B, 56 if on else 40, fill=col)
        paste(canvas, im, cx - im.width / 2, y0 - (8 if on else 0))
    tag = text_img(place, F_SANS_B, 44, fill=(20, 19, 18))
    pad = Image.new('RGBA', (tag.width + 36, tag.height + 14), PAPER + (255,))
    pad.alpha_composite(tag, (18, 7))
    reveal(canvas, pad, x0, y0 + 100, t, .1)


def overlay(card, t, shot_t0):
    lt = t - shot_t0
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    k = card['kind']
    if k == 'hook':
        paste(c, text_img('부마민주항쟁', F_SANS, 36, fill=ACCENT), SAFE_L + 20, SAFE_T + 20, ease(lt / .4))
        l1 = typed(card['l1'], lt, .2)
        if l1:
            paste(c, text_img(l1, F_SERIF, 112), SAFE_L + 20, 1080)
        l2 = typed(card['l2'], lt, 1.0)
        if l2:
            paste(c, text_img(l2, F_SERIF, 112), SAFE_L + 20, 1230)
    elif k == 'date':
        reveal(c, text_img(card['date'], F_SANS_B, 76, fill=ACCENT), SAFE_L + 20, 1110, lt)
        reveal(c, text_img(card['text'], F_SERIF, 100), SAFE_L + 20, 1210, lt, .12)
        if card.get('sub'):
            reveal(c, text_img(card['sub'], F_SERIF_R, 58, fill=(225, 225, 225)), SAFE_L + 24, 1340, lt, .24)
    elif k == 'day':
        day_bar(c, card['day'], card['place'], lt)
        reveal(c, text_img(card['text'], F_SERIF, 104), SAFE_L + 20, 1170, lt, .1)
        reveal(c, text_img(card['sub'], F_SERIF, 104), SAFE_L + 20, 1300, lt, .22)
    elif k == 'turn':
        reveal(c, text_img(card['l1'], F_SERIF, 116), SAFE_L + 20, 1120, lt)
        reveal(c, text_img(card['l2'], F_SERIF, 116, fill=PAPER), SAFE_L + 20, 1270, lt, .5)
    elif k == 'montage':
        paste(c, text_img('민주화운동기념관 특별도슨트', F_SANS, 40, fill=PAPER), SAFE_L + 20, SAFE_T + 20)
        paste(c, text_img('춤으로 만나는 민주화운동의 역사', F_SERIF, 66), SAFE_L + 20, 1350)
    elif k == 'voice':
        sub = text_img(card['text'], F_SERIF, 64)
        paste(c, sub, (W - 150 - sub.width) / 2 + 45, 1330, ease(lt / .3))
    elif k == 'cta':
        # 검은 화면 + 흰 글씨 4줄: 한 줄씩 마스크 리빌(아래→위) + 자간이 좁혀지며 안착, 마지막에 밑줄이 그어짐
        lines = [('민주화운동기념관', F_SANS, 64), ('특별도슨트', F_SERIF, 168), ('매주 금토일', F_SANS_B, 96), ('오후 3시', F_SANS_B, 96)]
        y = 640
        for i, (ln, fp, sz) in enumerate(lines):
            p = ease((lt - .15 - i * .45) / .5)
            if p > 0:
                track = int((1 - p) * sz * .35)  # 자간: 넓게 → 제자리
                f = font(fp, sz)
                widths = [f.getlength(ch) for ch in ln]
                tw = int(sum(widths) + track * (len(ln) - 1)) + 20
                im = Image.new('RGBA', (tw, int(sz * 1.35)), (0, 0, 0, 0))
                d = ImageDraw.Draw(im)
                x = 4
                for ch, wch in zip(ln, widths):
                    d.text((x, int(sz * .05)), ch, font=f, fill=(255, 255, 255))
                    x += wch + track
                # 마스크 리빌: 아래에서부터 드러남
                a = np.array(im)
                cut = int(a.shape[0] * (1 - p))
                a[:cut, :, 3] = 0
                im = Image.fromarray(a)
                cx = (SAFE_L + SAFE_R) / 2
                paste(c, im, cx - im.width / 2, y + (1 - p) * 30)
            y += int(sz * 1.35) + (30 if i == 1 else 10)
        u = ease((lt - 2.2) / .5)
        if u > 0:
            d = ImageDraw.Draw(c)
            cx = (SAFE_L + SAFE_R) / 2
            half = 230 * u
            d.line([(cx - half, y + 20), (cx + half, y + 20)], fill=ACCENT + (255,), width=8)
    return c


_RD, _ROOT = None, None
_GRAIN = [np.random.default_rng(1979 + k).normal(0, .025, (H // 2, W // 2, 1)).astype(np.float32) for k in range(4)]
_FLASH = {int(round(sh[0] * FPS)) for sh in SHOTS if sh[5]['kind'] == 'turn'}


def render_frame(i):
    global _RD
    if _RD is None:
        _RD = Reader(_ROOT)
    t = i / FPS
    s = next(sh for sh in SHOTS if sh[0] <= t < sh[1]) if t < DURATION else SHOTS[-1]
    t0, t1, key, st, speed, card = s
    k = i - int(round(t0 * FPS))
    src_fps = SRC[key][1]
    idx = int(round(st * src_fps + k * speed * src_fps / FPS))
    f = _RD.frame(key, idx)[..., ::-1]
    g = grade(f, 1.0 + .07 * (t - t0) / (t1 - t0))
    if card['kind'] == 'cta':
        g = np.zeros_like(g)
    g = scrim(g, top=.5, bottom=.8 if card['kind'] != 'montage' else .55)
    if card['kind'] != 'cta':
        g = np.clip(g + cv2.resize(_GRAIN[i % 4], (W, H))[..., None], 0, 1)
    if i in _FLASH:
        g = np.ones_like(g)  # 1프레임 화이트 플래시 (전환)
    base = Image.fromarray((g * 255).astype(np.uint8)).convert('RGBA')
    base.alpha_composite(overlay(card, t, t0))
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
    # 오디오: 무음 + 마지막 배우 원음 한 줄 (-16 LUFS)
    vt, vkey, vst, vlen = VOICE
    vsrc = os.path.join(root, SRC[vkey][0])
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-ss', str(vst), '-t', str(vlen), '-i', vsrc,
                    '-filter_complex', f'[1:a]afade=t=in:d=0.15,afade=t=out:st={vlen - 0.4}:d=0.4,loudnorm=I=-16:TP=-1.5,aformat=sample_rates=48000:channel_layouts=stereo,adelay={int(vt * 1000)}:all=1,apad[a]',
                    '-map', '0:v', '-map', '[a]', '-t', str(DURATION), '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000',
                    '-movflags', '+faststart', out], check=True)
    os.remove(tmp)
    print('done', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
