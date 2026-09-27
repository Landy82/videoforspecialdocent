import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BEAT, config, type SourceKey} from './config';
import {FONT} from './fonts';
import {resolveSource} from './sources';

const C = config.colors;
const G = config.grade;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// 비트마다 살짝 튀는 스케일 펀치 100 → 108 → 100%
export const punchAt = (frame: number, amount = 0.08) => {
	const p = frame % BEAT;
	return p < 2 ? 1 + amount * (p / 2) : 1 + amount * Math.max(0, 1 - (p - 2) / 6);
};

// ── 공연 영상/사진 한 컷: 저채도 + 남보라 그림자 + 천천히 확대 ──
export const Footage: React.FC<{
	source: SourceKey | string;
	dur: number;
	zoom?: [number, number];
	from?: number; // 소스 시작 초 추가 오프셋
	punch?: boolean;
	muted?: boolean;
	volume?: number | ((f: number) => number);
	dim?: number; // 0~1 어둡게
	freezeAfter?: number; // 이 프레임 이후 확대 정지
}> = ({source, dur, zoom = [1.1, 1.2], from = 0, punch = false, muted = true, volume = 1, dim = 0, freezeAfter}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const r = resolveSource(source, from);
	const f = freezeAfter !== undefined ? Math.min(frame, freezeAfter) : frame;
	const scale = interpolate(f, [0, dur], zoom, clamp) * (punch ? punchAt(frame) : 1);
	const style: React.CSSProperties = {
		width: '100%',
		height: '100%',
		objectFit: 'cover',
		objectPosition: `${r.focus[0] * 100}% ${r.focus[1] * 100}%`,
		transform: `scale(${scale})`,
		transformOrigin: `${r.focus[0] * 100}% ${r.focus[1] * 100}%`,
		filter: `saturate(${G.saturation}) contrast(${G.contrast}) brightness(${G.brightness * (1 - dim)})`,
	};
	return (
		<AbsoluteFill style={{overflow: 'hidden', backgroundColor: '#000'}}>
			{r.type === 'video' ? (
				<OffthreadVideo src={staticFile(r.file)} startFrom={Math.round(r.offsetSec * fps)} muted={muted} volume={volume} style={style} />
			) : (
				<Img src={staticFile(r.file)} style={style} />
			)}
			<AbsoluteFill style={{backgroundColor: C.indigo, mixBlendMode: 'screen', opacity: G.indigoShadow}} />
		</AbsoluteFill>
	);
};

// 필름 그레인 (전 구간)
export const Grain: React.FC<{opacity?: number}> = ({opacity = G.grain}) => {
	const frame = useCurrentFrame();
	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			<Img src={staticFile(`fx/grain_${frame % 6}.png`)} style={{width: '100%', height: '100%', mixBlendMode: 'overlay', opacity}} />
		</AbsoluteFill>
	);
};

// 위아래 어둡게 (글자 가독성)
export const Scrim: React.FC<{top?: number; bottom?: number}> = ({top = 0.55, bottom = 0.7}) => (
	<AbsoluteFill
		style={{
			background: `linear-gradient(180deg, rgba(10,9,24,${top}) 0%, rgba(10,9,24,0) 32%, rgba(10,9,24,0) 58%, rgba(10,9,24,${bottom}) 100%)`,
		}}
	/>
);

// 1프레임 화이트 플래시
export const Flash: React.FC<{at?: number}> = ({at = 0}) => {
	const frame = useCurrentFrame();
	return frame === at ? <AbsoluteFill style={{backgroundColor: '#fff'}} /> : null;
};

// 안전 영역 안쪽 박스 (가림 영역 회피)
export const SafeBox: React.FC<{top: number; children: React.ReactNode; align?: 'center' | 'left'; style?: React.CSSProperties}> = ({
	top,
	children,
	align = 'center',
	style,
}) => {
	const s = config.safe;
	return (
		<div
			style={{
				position: 'absolute',
				left: s.left,
				width: config.width - s.left - s.right,
				top,
				textAlign: align,
				display: 'flex',
				flexDirection: 'column',
				alignItems: align === 'center' ? 'center' : 'flex-start',
				...style,
			}}
		>
			{children}
		</div>
	);
};

// 글자 단위 스태거 등장
export const Stagger: React.FC<{
	text: string;
	start?: number;
	every?: number;
	style?: React.CSSProperties;
	accent?: string;
	accentColor?: string;
	rise?: number;
	calm?: boolean;
}> = ({text, start = 0, every = 1.5, style, accent, accentColor = C.pink, rise = 36, calm = false}) => {
	const frame = useCurrentFrame();
	const accentStart = accent ? text.indexOf(accent) : -1;
	return (
		<div style={{whiteSpace: 'pre', ...style}}>
			{[...text].map((ch, i) => {
				const t = frame - start - i * every;
				const o = interpolate(t, [0, calm ? 8 : 3], [0, 1], clamp);
				const y = calm ? 0 : interpolate(t, [0, 5], [rise, 0], {...clamp, easing: Easing.out(Easing.back(2))});
				const isAccent = accentStart >= 0 && i >= accentStart && i < accentStart + (accent?.length ?? 0);
				return (
					<span key={i} style={{display: 'inline-block', opacity: o, transform: `translateY(${y}px)`, color: isAccent ? accentColor : undefined}}>
						{ch}
					</span>
				);
			})}
		</div>
	);
};

// 타자기 글씨 (한 글자씩, 커서)
export const Typewriter: React.FC<{text: string; start?: number; every?: number; style?: React.CSSProperties; cursor?: boolean}> = ({
	text,
	start = 0,
	every = 2,
	style,
	cursor = true,
}) => {
	const frame = useCurrentFrame();
	const n = Math.max(0, Math.min(text.length, Math.floor((frame - start) / every) + 1));
	const typing = frame >= start && n < text.length;
	const blink = typing || Math.floor(frame / 8) % 2 === 0;
	return (
		<div style={{whiteSpace: 'pre', ...style}}>
			{frame >= start ? text.slice(0, n) : ''}
			{cursor && frame >= start ? <span style={{opacity: blink ? 1 : 0}}>▍</span> : null}
		</div>
	);
};

// 굴러가는 연도 숫자 (1960 → 1980 → 1987)
const RollDigit: React.FC<{from: number; to: number; progress: number; size: number}> = ({from, to, progress, size}) => {
	const steps = (to - from + 10) % 10;
	const seq = Array.from({length: steps + 1}, (_, i) => (from + i) % 10);
	const y = -progress * steps * size;
	return (
		<span style={{display: 'inline-block', height: size, overflow: 'hidden', verticalAlign: 'top'}}>
			<span style={{display: 'block', transform: `translateY(${y}px)`}}>
				{seq.map((d, i) => (
					<span key={i} style={{display: 'block', height: size, lineHeight: `${size}px`}}>
						{d}
					</span>
				))}
			</span>
		</span>
	);
};

export const RollingYear: React.FC<{from?: string; to: string; progress: number; size: number}> = ({from, to, progress, size}) => {
	if (!from || !/^\d{4}$/.test(from) || !/^\d{4}$/.test(to)) return <span style={{lineHeight: `${size}px`}}>{to}</span>;
	return (
		<span style={{display: 'inline-flex'}}>
			{[...to].map((d, i) => (
				<RollDigit key={i} from={Number(from[i])} to={Number(d)} progress={progress} size={size} />
			))}
		</span>
	);
};

// 도장처럼 박히는 연도/챕터명 (사각 도장 테두리 = Higgsfield 생성 텍스처)
export const Stamp: React.FC<{text: string; prev?: string; label: string; calm?: boolean; color?: string}> = ({
	text,
	prev,
	label,
	calm = false,
	color = C.pink,
}) => {
	const frame = useCurrentFrame();
	const size = 188;
	const scale = calm ? 1 : interpolate(frame, [0, 3, 6], [1.7, 0.96, 1], clamp);
	const opacity = calm ? interpolate(frame, [0, 12], [0, 1], clamp) : interpolate(frame, [0, 1], [0, 1], clamp);
	const roll = interpolate(frame, [0, 9], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
	const shake = calm ? 0 : Math.sin(frame * 2.4) * interpolate(frame, [3, 10], [7, 0], clamp);
	return (
		<div style={{display: 'flex', alignItems: 'center', gap: 34, transform: `translateX(${shake}px)`}}>
			<div
				style={{
					position: 'relative',
					padding: '40px 52px 30px',
					transform: `rotate(-4deg) scale(${scale})`,
					opacity,
					fontFamily: FONT.display,
					fontSize: size,
					color,
					lineHeight: 1,
				}}
			>
				<div
					style={{
						position: 'absolute',
						inset: 0,
						backgroundColor: color,
						WebkitMaskImage: `url(${staticFile('fx/stamp_rect.png')})`,
						WebkitMaskSize: '100% 100%',
						maskImage: `url(${staticFile('fx/stamp_rect.png')})`,
						maskSize: '100% 100%',
					}}
				/>
				<RollingYear from={prev} to={text} progress={calm ? 1 : roll} size={size} />
			</div>
			<div
				style={{
					fontFamily: FONT.sans,
					fontWeight: 900,
					fontSize: 76,
					color: C.white,
					opacity: interpolate(frame, [calm ? 6 : 3, calm ? 16 : 7], [0, 1], clamp),
					textShadow: '0 4px 24px rgba(0,0,0,.6)',
				}}
			>
				{label}
			</div>
		</div>
	);
};

// 원형 마스크 리빌
export const CircleReveal: React.FC<{children: React.ReactNode; at?: number; dur?: number; cx?: number; cy?: number}> = ({
	children,
	at = 0,
	dur = 9,
	cx = 50,
	cy = 45,
}) => {
	const frame = useCurrentFrame();
	const r = interpolate(frame - at, [0, dur], [0, 150], {...clamp, easing: Easing.out(Easing.cubic)});
	return <AbsoluteFill style={{clipPath: `circle(${r}% at ${cx}% ${cy}%)`}}>{children}</AbsoluteFill>;
};

// 아래에서 위로 여는 마스크 (와이프)
export const WipeUp: React.FC<{children: React.ReactNode; at?: number; dur?: number}> = ({children, at = 0, dur = 7}) => {
	const frame = useCurrentFrame();
	const t = interpolate(frame - at, [0, dur], [100, 0], {...clamp, easing: Easing.out(Easing.cubic)});
	return <AbsoluteFill style={{clipPath: `inset(${t}% 0 0 0)`}}>{children}</AbsoluteFill>;
};
