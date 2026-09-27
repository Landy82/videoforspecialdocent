#!/usr/bin/env bash
# Higgsfield에 올린/생성한 파일을 프로젝트로 내려받는다 (Higgsfield 작업 공간 등 CloudFront 접근 가능한 곳에서 실행)
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p assets/video assets/generated
U=https://d2ol7oe51mr4n9.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f
G=https://d8j0ntlcm91z4.cloudfront.net/user_3BVmzaDnwYqNBNwBPW7xvH5fv2f
# 업로드한 공연 영상: "media_id 파일명"
while read -r id name; do
  [ -f "assets/video/$name" ] || curl -sSf -o "assets/video/$name" "$U/$id.mp4"
done <<'LIST'
c2d00ae4-dc05-41ae-b34f-ce0d3890d2e7 20260830_150557_part36.mp4
LIST
# 생성 텍스처 (gpt_image_2_5)
curl -sSf -o assets/generated/paper.png "$G/hf_20260927_170539_ebeb6e7f-98b9-4f80-92b2-c6c6123fb4fb.png"
curl -sSf -o assets/generated/stamp.png "$G/hf_20260927_170539_1ff12e2a-380b-46a4-8839-fca0a901f566.png"
# VOX v2 재료 (nano_banana_2)
while read -r id name; do
  curl -sSf -o "assets/generated/$name" "$G/hf_20260927_${id}.png"
done <<'LIST'
174320_6980d5a5-814c-4f57-8707-934d4dc605d4 news_a.png
174320_4fb6dde8-368d-48bf-b877-e67105e42e8e news_b.png
174320_1bad31ca-61f0-4783-8a1f-75dfc270d6df news_c.png
174320_b7762bf6-10ad-4919-b8de-a2c8d7b7b3f5 paper2.png
174320_4ebfdad4-1ff4-4a9e-a641-f2c469053848 ink.png
174321_7e1c42e5-f5fd-49bd-ba1e-d745b2218bc1 xerox.png
LIST
echo "fetched"
