# 산출물

| 파일 | 위치 |
|---|---|
| memorial_docent_shorts_v1.0.mp4 | Higgsfield 작업 공간에서 렌더링 → Higgsfield 미디어: https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f/7a692afd-05f9-4801-ac5c-8b631315dbbf.mp4 |
| memorial_docent_cover_v1.0.png | 이 폴더 (Higgsfield 미디어에도 업로드됨) |
| memorial_docent_upload_v1.0.txt | 이 폴더 |

영상이 이 폴더에 없는 이유: part36 원본이 Higgsfield에만 있어 렌더링을 Higgsfield 작업 공간에서 했고,
작업 저장소 환경에서는 Higgsfield 저장소 파일을 내려받을 수 없기 때문입니다.

## 다시 만들기
```
bash scripts/fetch-higgsfield.sh   # Higgsfield 영상·텍스처 받기
npm ci && npm run clips && npm run fx
npm run render && npm run finalize output/memorial_docent_shorts_v1.1.mp4
```
문구·타이밍·BPM·색상·클립 구간은 `src/config.ts` 한 곳에서 수정합니다.
