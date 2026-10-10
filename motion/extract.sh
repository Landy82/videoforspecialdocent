#!/usr/bin/env bash
# 변환본 영상(px_*.mp4) 폴더 → frames/<clip>/0001.jpg … (30fps, 1080×1920)
# usage: motion/extract.sh <영상 폴더> <frames 폴더>
set -e
SRCDIR=$1; OUT=$2; HERE=$(cd "$(dirname "$0")" && pwd)
node -e "
global.window={}; const {SRC,CLIPS}=require('$HERE/clips.js');
for (const [id,c] of Object.entries(CLIPS)) console.log(id, SRC[c.src], c.ss, c.sp, c.dur, Math.round(c.dur*30));
" | { while read id f ss sp dur n; do
  mkdir -p "$OUT/$id"
  ffmpeg -v error -y -ss "$ss" -i "$SRCDIR/$f" -t "$(python3 -c "print($dur*$sp+0.2)")" -an \
    -vf "setpts=(PTS-STARTPTS)/$sp,fps=30,scale=1080:1920" -frames:v "$n" -q:v 3 "$OUT/$id/%04d.jpg" &
done; wait; }
for d in "$OUT"/*/; do echo "$(basename "$d") $(ls "$d" | wc -l)"; done
