// ─────────────────────────────────────────────────────────────
//  민주화운동기념관 특별도슨트 숏츠 — 설정 파일 (여기만 고치면 됩니다)
//  · 시간 단위는 '마디(bar)'와 '박(beat)'. 120BPM이면 1박 = 0.5초, 1마디 = 2초.
//  · 음악을 바꾸면 bpm 값만 바꾸세요. 모든 컷과 문구가 자동으로 따라갑니다.
// ─────────────────────────────────────────────────────────────

export const config = {
	version: 'v1.0',
	fps: 30,
	width: 1080,
	height: 1920,
	durationSec: 25,
	bpm: 120,

	audio: {
		bgm: 'audio/bgm.wav', // public/ 기준 경로
		bgmVolume: 1,
		// 정적 구간: 이 마디의 첫 박부터 stopBeats 박 동안 음악이 멈추고 공연 원음이 들림
		silenceBar: 8,
		silenceBeats: 2,
		liveSoundVolume: 0, // 정적 구간 공연 원음 볼륨 (0이면 원음 없이 정적만). v1.0: part36에 대사·노래가 없어 0
	},

	// 포스터에서 가져온 색. 포인트 컬러는 pink 하나만 사용.
	colors: {
		indigo: '#312d79',
		indigoDeep: '#1b1846',
		pink: '#ee4e9c',
		paper: '#efe6d2',
		ink: '#1d1b22',
		white: '#ffffff',
	},

	// 공연 영상 처리: 저채도 + 남보라 그림자 + 필름 그레인
	grade: {
		saturation: 0.12, // 0 = 흑백, 1 = 원본
		contrast: 1.15,
		brightness: 0.92,
		indigoShadow: 0.28, // 그림자에 남보라를 섞는 정도
		grain: 0.09,
	},

	// 숏츠 화면 가림 영역 (핵심 문구는 이 안쪽에만)
	safe: {top: 250, bottom: 400, right: 150, left: 60},

	// ── 장면 소스 ─────────────────────────────────────
	// video: 파일명 앞부분(촬영ID) + part 번호 + 그 조각 안에서의 시작 초
	//        같은 촬영의 연속 조각은 자동으로 이어져 있으므로 from이 2초를 넘어도 됩니다.
	// image: public/stills 안의 사진. focus = 확대 중심(0~1)
	sources: {
		cloth: {type: 'video', shoot: '20260830_151129', part: 8, from: 0, focus: [0.52, 0.55]},
		shirt: {type: 'video', shoot: '20260830_151741', part: 27, from: 0, focus: [0.5, 0.5]},
		struggle: {type: 'video', shoot: '20260830_150557', part: 36, from: 0, focus: [0.33, 0.5]},
		spotlightMan: {type: 'image', src: 'stills/spotlight_man.jpg', focus: [0.46, 0.5]},
		drawingSide: {type: 'image', src: 'stills/man_drawing_side.jpg', focus: [0.42, 0.45]},
		drawingDown: {type: 'image', src: 'stills/man_drawing_down.jpg', focus: [0.55, 0.5]},
		fistGuitar: {type: 'image', src: 'stills/woman_fist_guitar.jpg', focus: [0.5, 0.42]},
		sign: {type: 'image', src: 'stills/woman_sign.jpg', focus: [0.4, 0.35]},
	},

	// ── 1. 훅 (마디 0) ───────────────────────────────
	hook: {lines: ['이 건물,', '원래 뭐였을까?']},

	// ── 2. 반전 (마디 1) ─────────────────────────────
	reveal: {
		past: '옛 남영동 대공분실', // 1~2박, 기록 문서 위 타자 글씨
		now: ['지금은, ', '무대'], // 3~4박, 두 번째 조각이 포인트 컬러
		source: 'spotlightMan',
	},

	// ── 3. 역사 몽타주 (마디 2~6, 챕터당 1마디) ────────
	// stamp: 1박에 도장처럼 박히는 큰 글자 / label: 작은 설명 / keyword: 2~4박 문구
	// shots: 이 마디 안에서 박 단위로 바뀌는 화면 [시작 박, 소스, 확대 시작, 확대 끝]
	// calm: true면 스케일 펀치·플래시 없이 절제된 페이드
	chapters: [
		{stamp: '1960', label: '4·19', keyword: '학생들, 거리로', calm: false,
			shots: [[0, 'drawingSide', 1.12, 1.28]]},
		{stamp: '1980', label: '5·18', keyword: '그해 5월, 광주', calm: true,
			shots: [[0, 'drawingDown', 1.04, 1.14]]},
		{stamp: '1987', label: '6·10', keyword: '넥타이 부대까지', calm: false,
			shots: [[0, 'cloth', 1.3, 1.45]]},
		{stamp: '여성', label: '인권', keyword: '지워졌던 목소리', calm: false,
			shots: [[0, 'fistGuitar', 1.08, 1.2], [2, 'shirt', 1.25, 1.35]]},
		{stamp: '언론', label: '자유', keyword: '쓰지 못한 기사', calm: false, split: true,
			shots: [[0, 'struggle', 1.6, 1.7], [1, 'shirt', 1.5, 1.6], [2, 'cloth', 1.7, 1.8]]},
	],

	// ── 4. 가속 (마디 7): 박마다 컷 전환, 문구 없음 ─────
	rush: [
		['struggle', 1.35, 0.0],
		['cloth', 1.6, 0.9],
		['sign', 1.5, 0],
		['struggle', 1.9, 1.2],
	] as [string, number, number][],

	// ── 5. 정적 (마디 8) ─────────────────────────────
	silence: {
		source: 'struggle', // 음악이 멈춘 동안 원음과 함께 보여줄 장면
		sourceFrom: 0.5,
		lines: ['이 모든 이야기를,', '한 편의 공연으로'],
		accent: '공연', // 포인트 컬러로 칠할 단어
	},

	// ── 6. 안내 CTA (마디 9~) : 박마다 한 줄씩 ──────────
	cta: {
		photo: 'sign',
		title: '특별도슨트',
		lines: [
			{text: '매주 금·토·일 오후 3시', style: 'strong'},
			{text: '무료 공연', style: 'chip'},
			{text: '민주화운동기념관', style: 'strong'},
			{text: 'M1 B1 상설전시실 1·2', style: 'small'},
			{text: '~11.29 · 문의 02-6440-8982', style: 'small'}, // 예약·문의 방법
		],
		holdFromSec: 21, // 이 시점부터 화면 완전 정지 (읽을 시간)
		fadeOutSec: 24.5, // 루프 연결용 검은 화면 페이드 시작
	},

	// ── 숏츠 커버 ───────────────────────────────────
	cover: {
		source: 'cloth',
		sourceFrom: 0.35,
		kicker: '옛 남영동 대공분실에서',
		title: ['몸으로 부딪힌', '역사'],
		sub: '특별도슨트 · 무료 · 매주 금토일 오후 3시',
	},
} as const;

export type SourceKey = keyof typeof config.sources;
export const BEAT = (60 / config.bpm) * config.fps; // 1박 프레임 수 (120BPM, 30fps → 15)
export const BAR = BEAT * 4;
export const TOTAL_FRAMES = config.durationSec * config.fps;
