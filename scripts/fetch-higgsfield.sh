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
echo "fetched"
