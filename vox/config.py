"""VOX 스타일 콜라주 — 특별도슨트 숏츠 v2 설정 (여기만 고치면 됩니다)

· 음악은 넣지 않는다. Edits에서 곡을 입힐 때 BPM만 맞추면 모든 컷·푸시인이 박에 떨어진다.
· seed: 같은 seed + 같은 chaos = 항상 같은 영상. None이면 빌드할 때마다 새 seed를 뽑는다.
· chaos: 0 = 깔끔하게 정렬 / 1 = 겨우 붙어 있는 콜라주. 위치·회전·크기·크롭·가장자리·띠 어긋남·
  글자 흔들림·배경 조각·텍스처 오프셋을 한꺼번에 움직인다.
"""

SEED = None          # 예: 1987  (None = 새로 뽑기)
CHAOS = 0.45
BPM = 112            # 추천곡 BPM에 맞춰 바꾸세요 (행진 112 / 일어나 95 / 나는 나비 127 / 다시 만난 세계 108)
FIRST_BEAT = 0.0     # 첫 박이 떨어지는 시각(초). 곡의 첫 강박을 여기에 맞추면 됨
FPS = 30
W, H = 1080, 1920
DURATION = 25.0

# 팔레트 — 이 네 가지 외에는 쓰지 않는다
INK = (20, 19, 18)
PAPER = (237, 230, 216)      # 순백 금지, 따뜻한 종이색
GREY = (140, 138, 133)
ACCENT = (232, 73, 42)       # 레드오렌지 — 오직 히어로만

# 숏츠 UI 가림 영역 (핵심 문구는 이 안쪽에만)
SAFE = dict(left=60, right=W - 150, top=250, bottom=H - 400)

# ── 소재 ──────────────────────────────────────────
# video: public/clips 의 촬영ID/part. person=True면 가로 띠로 잘라 어긋나게 등장
# still: 로컬 배경 제거 → 흑백 컷아웃. recolor_hue: '선택적 재채색'이 가능한 부분의 원본 색상 범위(OpenCV H 0~180)
SOURCES = {
    'struggle': dict(kind='video', shoot='20260830_150557', part=36, person=True),
    'shirt': dict(kind='video', shoot='20260830_151741', part=27, person=True),
    'cloth': dict(kind='video', shoot='20260830_151129', part=8, person=True, recolor_hue=[(0, 10), (165, 180)]),
    'spotlight': dict(kind='still', src='public/stills/spotlight_man.jpg', person=True),
    'fist': dict(kind='still', src='public/stills/woman_fist_guitar.jpg', person=True),
    'sign': dict(kind='still', src='public/stills/woman_sign.jpg', person=True),
    'drawing': dict(kind='still', src='public/stills/man_drawing_down.jpg', person=True),
}

# ── 장면 (beats = 박 수). 마지막 CTA는 남은 시간을 모두 쓴다 ─────────
SCENES = [
    dict(id='title', beats=8, hero='spotlight', support=['drawing'],
         descriptor='민주화운동기념관 특별도슨트', title='몸으로 부딪힌 역사'),
    dict(id='move', beats=6, hero='struggle', calli='몸짓', label='01', en='MOVEMENT'),
    dict(id='narr', beats=6, hero='shirt', calli='대사', label='02', en='NARRATION'),
    dict(id='music', beats=6, hero='fist', calli='음악', label='03', en='MUSIC'),
    dict(id='media', beats=6, hero='cloth', calli='영상', label='04', en='VISUAL MEDIA'),
    dict(id='feel', beats=6, hero='sign', descriptor='아는 것을 넘어,', calli='함께 느끼는 역사'),
    dict(id='cta', beats=None, hero_word='무료',
         descriptor='민주화운동기념관 특별도슨트', title='매주 금·토·일 오후 3시',
         lines=['M1 B1 상설전시실 1·2', '2026. 6. 12 ~ 11. 29', '관람 문의 02-6440-8982']),
]
END_FADE = 0.6   # 마지막 N초 동안 빈 종이로 돌아가 첫 장면과 루프 연결

# Higgsfield(nano_banana_2) 생성 재료 — scripts/fetch-higgsfield.sh 가 assets/generated/ 로 받는다
GENERATED = dict(
    news=['news_a.png', 'news_b.png', 'news_c.png'],
    paper='paper2.png', ink='ink.png', xerox='xerox.png',
)
