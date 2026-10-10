#!/usr/bin/env bash
# 전체 빌드: 영상 프레임 추출 → 박자별 확인 컷 → 60fps×3 서브프레임 렌더 → tmix 모션블러 → 사운드 합치기
# usage: motion/build.sh <변환본 영상 폴더> <작업 폴더> <out.mp4> [workers]
set -e
HERE=$(cd "$(dirname "$0")" && pwd); SRC=$1; WORK=$2; OUT=$3; WK=${4:-6}
mkdir -p "$WORK"
[ -d "$WORK/frames" ] || bash "$HERE/extract.sh" "$SRC" "$WORK/frames"
node "$HERE/render.mjs" audio "$WORK/music.wav"
node "$HERE/render.mjs" video "$WORK/frames" "$WORK" "$WK"
ffmpeg -v error -y -framerate 180 -i "$WORK/sub/%05d.jpg" \
  -vf "tmix=frames=3:weights='1 1 1',select='eq(mod(n\,3)\,2)',setpts=N/(60*TB)" -r 60 \
  -c:v libx264 -preset medium -crf 17 -pix_fmt yuv420p "$WORK/video.mp4"
ffmpeg -v error -y -i "$WORK/video.mp4" -i "$WORK/music.wav" \
  -filter_complex "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,aformat=sample_rates=48000:channel_layouts=stereo[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -t 30 -movflags +faststart "$OUT"
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate -of compact "$OUT"
