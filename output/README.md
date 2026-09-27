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
