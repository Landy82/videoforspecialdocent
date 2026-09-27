# VOX 스타일 콜라주 빌더 (특별도슨트 숏츠 v2)

인쇄물을 오려 손으로 배치해 촬영한 듯한 아날로그 콜라주. 음악 없음 — Edits에서 곡을 입힌다.

```
pip install -r vox/requirements.txt
bash scripts/fetch-higgsfield.sh      # Higgsfield 영상·나노바나나2 재료
npm ci && npm run clips               # 8K 원본 → 편집용 클립(연속 part 자동 연결)
python3 -m vox.prep                   # 로컬 배경 제거(rembg) · 신문 조각 풀 · 질감 · 폰트
python3 -m vox.build                  # 새 seed로 렌더 → output/
python3 -m vox.build --seed 1987 --chaos .45 --bpm 112 --version v2.1
python3 -m vox.build --seed 1987 --stills 3.9,12.6   # 정지 프레임만 (out/vox_<seed>/)
```

- `vox/config.py`: 문구·장면·BPM·첫 박·seed·chaos·팔레트 한 곳에서 수정
- 같은 seed + 같은 chaos = 항상 같은 프레임. 렌더 결과 옆 `.json`에 seed가 기록된다.
- 팔레트는 잉크·종이·회색·레드오렌지 4색만. 레드오렌지는 장면마다 히어로 하나에만
  (듀오톤 / 레드오렌지 배경지 / 선택적 재채색 중 seed가 하나를 고름).
