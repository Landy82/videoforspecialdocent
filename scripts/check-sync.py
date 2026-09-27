"""완성본 자체 점검: 화면 급변(컷) 위치가 박(0.5초 격자)에 맞는지, 음악 박 위치와 일치하는지 확인.
  python3 scripts/check-sync.py <영상.mp4> [bpm]   (FFMPEG 환경변수로 ffmpeg 경로 지정 가능)"""
import os, subprocess, sys, numpy as np
f = sys.argv[1]; bpm = float(sys.argv[2]) if len(sys.argv) > 2 else 120
ff = os.environ.get('FFMPEG', 'ffmpeg'); fps = 30; beat = 60 / bpm
raw = subprocess.run([ff, '-v', 'error', '-i', f, '-vf', 'scale=54:96,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
v = np.frombuffer(raw, np.uint8).reshape(-1, 96, 54).astype(float)
d = np.abs(np.diff(v, axis=0)).mean(axis=(1, 2))
cuts = [i + 1 for i in range(len(d)) if d[i] > 18 and d[i] > 2.5 * np.median(d[max(0, i - 8):i + 8])]
off = [((c / fps) / beat - round((c / fps) / beat)) * beat * fps for c in cuts]
print(f'프레임 {len(v)}개, 컷 {len(cuts)}개')
for c, o in zip(cuts, off):
    print(f'  {c/fps:6.2f}s  (박 격자와 {o:+.0f}프레임)')
bad = [c for c, o in zip(cuts, off) if abs(o) > 1]
print('박에서 1프레임 넘게 벗어난 컷:', [round(c / fps, 2) for c in bad] or '없음')
