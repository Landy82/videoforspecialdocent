# 산출물

| 버전 | 영상 | 커버 | 업로드 텍스트 |
|---|---|---|---|
| v2.2 (라벨 가림·얼굴 가림 수정) | [Higgsfield](https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f/a7814e2d-6584-4c77-8927-e9780effd0e3.mp4) | [Higgsfield](https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f/ca3b105a-4b86-4344-879d-8b0730b365a6.png) | memorial_docent_upload_v2.0.txt |
| v2.1 (VOX 콜라주, 음악 없음, 핏자국처럼 보이던 재채색 제거) | [Higgsfield](https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f/443d426e-bad3-455d-9ae0-78865b7f535c.mp4) | [Higgsfield](https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f/3ac11ae0-da4c-4149-b8ab-27531a53d704.png) | memorial_docent_upload_v2.0.txt |
| v2.0 (VOX 콜라주, 음악 없음) | [Higgsfield](https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f/b2173204-23b8-4694-bbdc-cd1c450855b7.mp4) | [Higgsfield](https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f/d3943ae0-ebc0-405a-9fe9-094b7e4b3df0.png) | memorial_docent_upload_v2.0.txt |
| v1.0 (Remotion, 합성 BGM) | [Higgsfield](https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f/7a692afd-05f9-4801-ac5c-8b631315dbbf.mp4) | memorial_docent_cover_v1.0.png | memorial_docent_upload_v1.0.txt |

영상이 이 폴더에 없는 이유: part36 원본과 Higgsfield 생성 재료가 Higgsfield 저장소에만 있어 렌더링을
Higgsfield 작업 공간에서 했고, 작업 저장소 환경에서는 Higgsfield 파일을 내려받을 수 없기 때문입니다.

- v2.2 재현: `python3 -m vox.build --seed 1987 --chaos .45 --bpm 112 --version v2.2` (자세한 방법은 vox/README.md)
- v1.0 재현: Remotion (`src/`), `npm run render`

## 부마민주항쟁 숏츠 v1.0 (docu/render.py, 실물 영상만)
- 52초 · 1080×1920 30fps · H.264 + AAC (배경음악 없음, 끝부분 배우 원음 "우리가 대한민국의 주인입니다." 한 줄)
- 1972 유신 → 1979.10.16~20 부산·마산 → 10.26 → 공연 몽타주 → 검은 화면 엔딩(민주화운동기념관 / 특별도슨트 / 매주 금토일 / 오후 3시)
- https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f/28229725-c05f-4113-9a6c-fc297168f825.mp4

## 부마민주항쟁 숏츠 v1.1
- 10.5–14초 장면 교체 (피켓 → 남성 무용수가 앞으로 내딛는 장면, draw 36초)
- 폰트 전면 교체: Hahmlet(제목) · IBM Plex Sans KR(본문) · Anton(숫자), 모두 OFL — docu/fonts
- 모션: 글자별 키네틱 등장/퇴장, 슬롯처럼 굴러오는 날짜 숫자, 거대한 외곽선 숫자 배경, 휩·줌 펀치 컷, 몽타주 RGB 분리·빛번짐, 엔딩 입자·빛 반사
- 사운드: docu/sound.py 코드 합성(샘플 없음) + 배우 원음 대사, 전체 -14 LUFS
- 엔딩 정보 글자 크기 축소
- https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f/8d1f1ee7-39f5-439b-99c3-3d772ae45e44.mp4

## 부마 × 특별도슨트 30초 모션 숏폼 v2.0 (motion/)
- 콘셉트 「선 하나가 몸이 되고, 몸이 역사가 된다」 · 120BPM · 60fps · 보라 #62579F 메인 · 루프
- https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f/1f5de74a-124e-4824-8c26-6eb5a82c0cfc.mp4

## 부마민주항쟁 숏츠 v1.2 — 음악에 맞춘 편집
- 음악: docu/score.py 로 직접 작곡(96BPM, D단조→F장조), 오픈 사운드폰트 GeneralUser GS(상업 이용 가능)의 피아노·현악·첼로·팀파니·타이코·합창으로 연주 + docu/sound.py 효과음·믹스, -13.3 LUFS
- 편집: 모든 컷을 마디(2.5초) 위로, 몽타주는 2박마다. 글자 등장·날짜 진행·줌 펄스가 박자에 맞춰 움직임. 10.26 뒤 한 마디 빌드업(박마다 선 하나) → 1/8박 정적 → 전환
- 폰트: 본명조(Noto Serif KR) 제목 + Pretendard 본문·가는 숫자 (docu/fonts2, OFL)
- 50초 · 1080×1920 30fps
- https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f/c1603d4f-e27c-4d74-bdd1-51baad8ab88d.mp4

## 부마민주항쟁 숏츠 v1.3 — 사실 수정
- 10.19 카드: 「마산으로 번진 시위」 → 「마산 시민 수천 명 / 반정부 시위」 (마산 확산은 10.18 — 민주화운동기념사업회 오픈아카이브 「민주화운동 일지」 BRR_1979_10_18_n004·n005, BRR_1979_10_19_n002 기준)
- 날짜 카드에 출처 표기: 민주화운동기념사업회 오픈아카이브 「민주화운동 일지」
- 나머지는 v1.2와 같음 (음악에 맞춘 편집, 작곡 음악, 본명조+Pretendard)
- https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f/f9b0e8da-da4c-42c6-9ccf-cf57c98512d1.mp4
