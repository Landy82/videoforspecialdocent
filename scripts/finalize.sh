#!/usr/bin/env bash
# 렌더 결과를 유튜브 기준 음량(-14 LUFS, True Peak -1.5 dBTP)으로 2패스 정규화하고 정확히 25초로 맞춘다.
#   scripts/finalize.sh <입력.mp4> <출력.mp4>
set -euo pipefail
IN=$1; OUT=$2
FF=${FFMPEG:-ffmpeg}
DUR=${DURATION:-25}
M=$($FF -hide_banner -i "$IN" -t "$DUR" -vn -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | grep "\"$1\"" | sed -E 's/.*: "?([^"]*)"?,?/\1/'; }
$FF -v error -y -i "$IN" -t "$DUR" -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,aresample=48000" \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart "$OUT"
echo "측정(정규화 전): I=$(g input_i) LUFS, TP=$(g input_tp) dBTP"
$FF -hide_banner -i "$OUT" -vn -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | grep -E '"input_(i|tp)"' | tr -d ' \n'; echo " ← 정규화 후"
