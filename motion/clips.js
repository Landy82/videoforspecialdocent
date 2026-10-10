// 실물 공연 영상 구간 (AI 생성 없음). t0/dur: 영상 타임라인에서 쓰는 구간(초), ss: 원본 시작초, sp: 속도
// fx/fy: 1080×1920 기준 피사체 중심 — 창(window)이 이 점을 따라간다, wz: 창 속 영상 기본 배율
window.SRC = {
  yusin: 'px_5fdb044c.mp4', spot: 'px_2f255e51.mp4', woman: 'px_bfd61af1.mp4',
  draw: 'px_083bac20.mp4', sign: 'px_cce6e17c.mp4', final: 'px_84bf313a.mp4',
};
window.CLIPS = {
  hook:    { src: 'yusin', ss: 14.0,  sp: .5, t0: 0.0,  dur: 2.6, fx: 330, fy: 1150, wz: .75 },
  press:   { src: 'spot',  ss: 12.0,  sp: 1,  t0: 2.0,  dur: 2.2, fx: 600, fy: 900, wz: .7 },
  lunge:   { src: 'draw',  ss: 36.0,  sp: .5, t0: 3.9,  dur: 4.3, fx: 660, fy: 880, wz: .6 },
  masan:   { src: 'woman', ss: 45.0,  sp: 1,  t0: 10.4, dur: 3.2, fx: 620, fy: 950 },
  p1:      { src: 'sign',  ss: 15.0,  sp: .5, t0: 13.4, dur: 3.6, fx: 540, fy: 900 },
  p2:      { src: 'spot',  ss: 100.0, sp: 1,  t0: 13.4, dur: 3.0, fx: 540, fy: 1050 },
  p3:      { src: 'woman', ss: 68.0,  sp: 1,  t0: 13.4, dur: 3.0, fx: 540, fy: 1000 },
  p4:      { src: 'draw',  ss: 42.0,  sp: .5, t0: 13.4, dur: 3.0, fx: 600, fy: 1000 },
  history: { src: 'spot',  ss: 104.0, sp: 1,  t0: 16.3, dur: 1.6, fx: 540, fy: 1000 },
  mom:     { src: 'woman', ss: 66.0,  sp: 1,  t0: 17.9, dur: 2.3, fx: 520, fy: 950 },
  m1:      { src: 'woman', ss: 77.0,  sp: 1,  t0: 19.9, dur: 4.4, fx: 480, fy: 1000 },
  m2:      { src: 'sign',  ss: 38.0,  sp: .5, t0: 19.9, dur: 4.4, fx: 540, fy: 900 },
  m3:      { src: 'draw',  ss: 12.0,  sp: .5, t0: 19.9, dur: 4.4, fx: 560, fy: 1100 },
  m4:      { src: 'spot',  ss: 24.0,  sp: 1,  t0: 19.9, dur: 4.4, fx: 560, fy: 1000 },
  m5:      { src: 'yusin', ss: 20.0,  sp: .5, t0: 19.9, dur: 4.4, fx: 400, fy: 1100 },
  final:   { src: 'final', ss: 29.6,  sp: 1,  t0: 23.9, dur: 2.4, fx: 540, fy: 900 },
};
if (typeof module !== 'undefined') module.exports = { SRC: window.SRC, CLIPS: window.CLIPS };
