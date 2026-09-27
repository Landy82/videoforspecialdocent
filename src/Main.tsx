import React from 'react';
import {AbsoluteFill, Audio, Img, interpolate, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {BAR, BEAT, config, type SourceKey, TOTAL_FRAMES} from './config';
import {CircleReveal, Flash, Footage, Grain, punchAt, SafeBox, Scrim, Stagger, Stamp, Typewriter, WipeUp} from './components';
import {FONT, loadFonts} from './fonts';

loadFonts();
const C = config.colors;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const SAFE_BOTTOM = config.height - config.safe.bottom; // 1520
const shadow = '0 6px 30px rgba(0,0,0,.55)';

// 섹션 시작 마디 (BPM이 바뀌면 자동으로 따라감)
const S = {
	hook: 0,
	reveal: 1,
	chapters: 2,
	rush: 2 + config.chapters.length,
	silence: config.audio.silenceBar,
	cta: config.audio.silenceBar + 1,
};

// ── 0~2초: 철문 → 질문 ──────────────────────────
const Hook: React.FC = () => {
	const frame = useCurrentFrame();
	const close = interpolate(frame, [0, 5], [0, 1], {...clamp, easing: (t) => t * t});
	const shake = Math.sin(frame * 3.1) * interpolate(frame, [5, 14], [14, 0], clamp);
	const doorsOut = interpolate(frame, [10, 16], [1, 0], clamp);
	const door = (side: 'l' | 'r'): React.CSSProperties => ({
		position: 'absolute',
		top: 0,
		bottom: 0,
		width: config.width / 2,
		[side === 'l' ? 'left' : 'right']: 0,
		transform: `translateX(${(side === 'l' ? -1 : 1) * (1 - close) * (config.width / 2)}px)`,
		background: `repeating-linear-gradient(90deg, #16151c 0 118px, #0d0c12 118px 122px), #121118`,
		boxShadow: side === 'l' ? 'inset -3px 0 0 #2a2833' : 'inset 3px 0 0 #2a2833',
		opacity: doorsOut,
	});
	return (
		<AbsoluteFill style={{backgroundColor: '#050508'}}>
			<AbsoluteFill style={{transform: `translateX(${shake}px)`}}>
				<div style={door('l')} />
				<div style={door('r')} />
			</AbsoluteFill>
			<SafeBox top={760}>
				<Typewriter text={config.hook.lines[0]} start={BEAT} every={2} cursor={false} style={{fontFamily: FONT.serif, fontWeight: 800, fontSize: 96, color: C.paper}} />
				<Typewriter text={config.hook.lines[1]} start={BEAT * 2} every={2} style={{fontFamily: FONT.serif, fontWeight: 800, fontSize: 96, color: C.paper, marginTop: 24}} />
			</SafeBox>
		</AbsoluteFill>
	);
};

// ── 2~4초: 옛 남영동 대공분실 → 지금은, 무대 ───────
const Reveal: React.FC = () => {
	const frame = useCurrentFrame();
	const src = config.sources[config.reveal.source as SourceKey];
	const [a, b] = config.reveal.now;
	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			{frame < BEAT * 2 + 9 ? (
				<AbsoluteFill>
					<Img src={staticFile('fx/paper.jpg')} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${interpolate(frame, [0, BEAT * 2], [1.08, 1], clamp)})`}} />
					<AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 45%, rgba(20,18,40,.45) 100%)'}} />
					<SafeBox top={800}>
						<Typewriter text={config.reveal.past} start={1} every={2} style={{fontFamily: FONT.serif, fontWeight: 800, fontSize: 92, color: C.ink, letterSpacing: 2}} />
					</SafeBox>
				</AbsoluteFill>
			) : null}
			<Sequence from={BEAT * 2}>
				<CircleReveal dur={9} cx={src.focus[0] * 100} cy={src.focus[1] * 100}>
					<Footage source={config.reveal.source} dur={BEAT * 2} zoom={[1.18, 1.08]} />
					<Scrim top={0.2} bottom={0.75} />
					<SafeBox top={SAFE_BOTTOM - 230}>
						<Stagger text={a + b} accent={b} start={3} every={1.5} style={{fontFamily: FONT.display, fontSize: 150, color: C.white, textShadow: shadow}} />
					</SafeBox>
				</CircleReveal>
			</Sequence>
		</AbsoluteFill>
	);
};

// ── 4~14초: 챕터 몽타주 ──────────────────────────
type Chapter = (typeof config.chapters)[number];
const ChapterBar: React.FC<{ch: Chapter; prev?: string}> = ({ch, prev}) => {
	const frame = useCurrentFrame();
	const shots = ch.shots as unknown as [number, string, number, number][];
	const split = 'split' in ch && ch.split;
	const fade = ch.calm ? interpolate(frame, [0, 10, BAR - 8, BAR], [0, 1, 1, 0.35], clamp) : 1;
	const underline = interpolate(frame - BEAT, [4, 12], [0, 1], clamp);
	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			<AbsoluteFill style={{opacity: fade}}>
				{split ? (
					// 3단 분할: 박마다 한 칸씩 열림
					<AbsoluteFill style={{flexDirection: 'row'}}>
						{shots.map(([beat, src, z0, z1], i) => (
							<div key={i} style={{position: 'relative', width: config.width / 3, height: '100%', overflow: 'hidden', borderRight: i < 2 ? `4px solid ${C.indigoDeep}` : undefined}}>
								<Sequence from={beat * BEAT} layout="none">
									<WipeUp dur={6}>
										<Footage source={src} dur={BAR - beat * BEAT} zoom={[z0, z1]} punch />
									</WipeUp>
								</Sequence>
							</div>
						))}
					</AbsoluteFill>
				) : (
					shots.map(([beat, src, z0, z1], i) => {
						const next = shots[i + 1]?.[0] ?? 4;
						const dur = (next - beat) * BEAT;
						return (
							<Sequence key={i} from={beat * BEAT} durationInFrames={dur}>
								<Footage source={src} dur={dur} zoom={[z0, z1]} punch={!ch.calm} />
							</Sequence>
						);
					})
				)}
				<Scrim top={0.6} bottom={0.8} />
			</AbsoluteFill>
			<SafeBox top={config.safe.top + 40}>
				<Stamp text={ch.stamp} prev={prev} label={ch.label} calm={ch.calm} color={ch.calm ? C.paper : C.pink} />
			</SafeBox>
			<SafeBox top={SAFE_BOTTOM - 190}>
				<Stagger
					text={ch.keyword}
					start={BEAT}
					every={ch.calm ? 3 : 1.5}
					calm={ch.calm}
					style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 104, color: C.white, textShadow: shadow, letterSpacing: -2}}
				/>
				<div style={{height: 10, width: 300 * underline, backgroundColor: ch.calm ? C.paper : C.pink, marginTop: 18}} />
			</SafeBox>
			{ch.calm ? null : <Flash />}
		</AbsoluteFill>
	);
};

// ── 14~16초: 박마다 컷 ──────────────────────────
const Rush: React.FC = () => (
	<AbsoluteFill style={{backgroundColor: '#000'}}>
		{config.rush.map(([src, zoom, from], i) => (
			<Sequence key={i} from={i * BEAT} durationInFrames={BEAT}>
				<Footage source={src} dur={BEAT} zoom={[zoom, zoom * 1.04]} from={from} punch />
				<Flash />
			</Sequence>
		))}
	</AbsoluteFill>
);

// ── 16~18초: 정적(원음) → 이 모든 이야기를 ───────────
const Silence: React.FC = () => {
	const frame = useCurrentFrame();
	const silent = config.audio.silenceBeats * BEAT;
	const [l1, l2] = config.silence.lines;
	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			<Footage
				source={config.silence.source}
				from={config.silence.sourceFrom}
				dur={BAR}
				zoom={[1.2, 1.32]}
				muted={config.audio.liveSoundVolume <= 0}
				volume={(f) => (f < silent ? config.audio.liveSoundVolume : 0)}
				dim={frame < silent ? 0 : 0.35}
			/>
			<Scrim top={0.3} bottom={0.85} />
			<SafeBox top={SAFE_BOTTOM - 300}>
				<Stagger text={l1} start={silent} every={1} style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: 84, color: C.paper, textShadow: shadow}} />
				<Stagger
					text={l2}
					start={silent + BEAT}
					every={1}
					accent={config.silence.accent}
					style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 112, color: C.white, textShadow: shadow, marginTop: 10, letterSpacing: -2}}
				/>
			</SafeBox>
		</AbsoluteFill>
	);
};

// ── 18초~: 안내 ─────────────────────────────────
const CtaLine: React.FC<{text: string; style: string; start: number}> = ({text, style, start}) => {
	const frame = useCurrentFrame();
	const t = frame - start;
	const o = interpolate(t, [0, 4], [0, 1], clamp);
	const y = interpolate(t, [0, 6], [40, 0], {...clamp, easing: (x) => 1 - (1 - x) ** 3});
	const base: React.CSSProperties = {opacity: o, transform: `translateY(${y}px)`, fontFamily: FONT.sans, color: C.white};
	if (style === 'chip')
		return (
			<div style={{...base, marginTop: 22, fontWeight: 900, fontSize: 64, color: C.indigo, backgroundColor: C.pink, padding: '6px 34px 10px', borderRadius: 999}}>{text}</div>
		);
	if (style === 'small') return <div style={{...base, marginTop: 14, fontWeight: 700, fontSize: 42, opacity: o * 0.85}}>{text}</div>;
	return <div style={{...base, marginTop: 20, fontWeight: 800, fontSize: 66, letterSpacing: -1}}>{text}</div>;
};

const Cta: React.FC = () => {
	const frame = useCurrentFrame();
	const hold = (config.cta.holdFromSec - S.cta * (BAR / config.fps)) * config.fps; // CTA 시작부터 정지까지 프레임
	const titlePunch = frame < hold ? punchAt(Math.max(0, frame), 0.05) : 1;
	return (
		<WipeUp dur={7}>
			<AbsoluteFill style={{backgroundColor: C.indigo}}>
				{/* 포스터 모티프: 흰 선 사각 프레임 + 공연 사진 */}
				<div style={{position: 'absolute', left: 215, top: 270, width: 560, height: 560, border: `6px solid ${C.white}`, transform: 'translate(22px, 22px)', opacity: 0.35}} />
				<div style={{position: 'absolute', left: 215, top: 270, width: 560, height: 560, overflow: 'hidden', border: `6px solid ${C.white}`}}>
					<Footage source={config.cta.photo} dur={hold} zoom={[1.02, 1.12]} freezeAfter={hold} />
				</div>
				<SafeBox top={880}>
					<Stagger text={config.cta.title} start={0} every={1.5} style={{fontFamily: FONT.display, fontSize: 150, color: C.pink, transform: `scale(${titlePunch})`, lineHeight: 1}} />
					{config.cta.lines.map((l, i) => (
						<CtaLine key={i} text={l.text} style={l.style} start={(i + 1) * BEAT} />
					))}
				</SafeBox>
			</AbsoluteFill>
		</WipeUp>
	);
};

export const Main: React.FC = () => {
	const frame = useCurrentFrame();
	const fadeStart = config.cta.fadeOutSec * config.fps;
	const endFade = interpolate(frame, [fadeStart, TOTAL_FRAMES - 1], [0, 1], clamp);
	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			<Audio src={staticFile(config.audio.bgm)} volume={config.audio.bgmVolume} />
			<Sequence from={S.hook * BAR} durationInFrames={BAR}>
				<Hook />
			</Sequence>
			<Sequence from={S.reveal * BAR} durationInFrames={BAR}>
				<Reveal />
			</Sequence>
			{config.chapters.map((ch, i) => (
				<Sequence key={i} from={(S.chapters + i) * BAR} durationInFrames={BAR}>
					<ChapterBar ch={ch} prev={config.chapters[i - 1]?.stamp} />
				</Sequence>
			))}
			<Sequence from={S.rush * BAR} durationInFrames={BAR}>
				<Rush />
			</Sequence>
			<Sequence from={S.silence * BAR} durationInFrames={BAR}>
				<Silence />
			</Sequence>
			<Sequence from={S.cta * BAR}>
				<Cta />
			</Sequence>
			<Grain />
			<AbsoluteFill style={{backgroundColor: '#000', opacity: endFade}} />
		</AbsoluteFill>
	);
};
