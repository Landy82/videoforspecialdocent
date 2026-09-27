"""Higgsfield로 생성한 텍스처를 영상용으로 가공한다.
  assets/generated/paper.png  → public/fx/paper.jpg        (기록 문서 종이 배경)
  assets/generated/stamp.png  → public/fx/stamp_rect.png   (사각 도장 테두리, 잉크=불투명)
                               public/fx/stamp_circle.png (원형 도장 테두리)
  + public/fx/grain_0..5.png (필름 그레인, 수식으로 생성)
원본 텍스처가 없으면 비슷한 모양을 수식으로 만들어 대신 쓴다(로컬 미리보기용).
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, 'assets', 'generated')
FX = os.path.join(ROOT, 'public', 'fx')
os.makedirs(FX, exist_ok=True)
rng = np.random.default_rng(419)


def placeholder_paper():
    a = np.ones((1344, 752, 3)) * np.array([236, 222, 196]) + rng.normal(0, 4, (1344, 752, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype('uint8'))


def placeholder_stamp():
    im = Image.new('L', (752, 1344), 255)
    d = ImageDraw.Draw(im)
    d.rectangle([40, 90, 712, 450], outline=0, width=34)
    d.ellipse([110, 650, 640, 1180], outline=0, width=34)
    a = np.array(im, float) + rng.normal(0, 60, (1344, 752))
    return Image.fromarray(np.clip(a, 0, 255).astype('uint8')).filter(ImageFilter.MedianFilter(3)).convert('RGB')


def load(name, fallback):
    p = os.path.join(GEN, name)
    if os.path.exists(p):
        return Image.open(p).convert('RGB'), True
    return fallback(), False


paper, real_p = load('paper.png', placeholder_paper)
paper.resize((1080, 1920), Image.LANCZOS).save(os.path.join(FX, 'paper.jpg'), quality=90)

stamp, real_s = load('stamp.png', placeholder_stamp)
g = np.array(stamp.convert('L'), float)
ink = np.clip((200 - g) / 150, 0, 1)  # 어두울수록 잉크
# 잉크가 있는 가로줄 덩어리로 도형을 나눔 (위 = 사각, 아래 = 원형)
rows = (ink > 0.5).mean(1) > 0.01
blobs, start = [], None
for y, on in enumerate(list(rows) + [False]):
    if on and start is None: start = y
    if not on and start is not None:
        if y - start > 20: blobs.append((start, y))
        start = None
blobs = sorted(blobs, key=lambda b: b[1] - b[0], reverse=True)[:2]
blobs.sort()
for name, (y0, y1) in zip(('stamp_rect', 'stamp_circle'), blobs):
    part = ink[y0:y1]
    cols = np.where((part > 0.5).mean(0) > 0.01)[0]
    crop = part[:, cols[0]:cols[-1] + 1]
    rgba = np.zeros(crop.shape + (4,), 'uint8')
    rgba[..., :3] = 255
    rgba[..., 3] = (np.where(crop > 0.25, crop, 0) * 255).astype('uint8')
    Image.fromarray(rgba).save(os.path.join(FX, f'{name}.png'))

for i in range(6):
    n = rng.normal(128, 40, (480, 270)).clip(0, 255).astype('uint8')
    Image.fromarray(n).resize((1080, 1920), Image.NEAREST).save(os.path.join(FX, f'grain_{i}.png'))

print(f'paper: {"Higgsfield" if real_p else "대체"} / stamp: {"Higgsfield" if real_s else "대체"} → public/fx')
