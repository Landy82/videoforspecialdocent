import clips from '../public/clips/index.json';
import {config, type SourceKey} from './config';

// 원본 조각 1개의 실제 길이(초). 연속 조각을 이어 붙인 파일 안에서 위치를 계산할 때 사용.
const PART_SEC = 2.0167;

export type Resolved =
	| {type: 'video'; file: string; offsetSec: number; focus: readonly number[]}
	| {type: 'image'; file: string; focus: readonly number[]};

export const resolveSource = (key: SourceKey | string, extraFrom = 0): Resolved => {
	const s = config.sources[key as SourceKey];
	if (!s) throw new Error(`config.sources에 '${key}'가 없습니다`);
	if (s.type === 'image') return {type: 'image', file: s.src, focus: s.focus};
	const clip = clips.find((c) => c.shoot === s.shoot && c.parts.includes(s.part));
	if (!clip) {
		// 아직 변환되지 않은 영상은 첫 번째 클립으로 대신 표시 (미리보기용)
		console.warn(`클립 없음: ${s.shoot}_part${s.part} → 대체 클립 사용`);
		const fb = clips[0];
		return {type: 'video', file: fb.file, offsetSec: Math.min(extraFrom, fb.duration - 0.6), focus: s.focus};
	}
	const offsetSec = (s.part - clip.parts[0]) * PART_SEC + s.from + extraFrom;
	return {type: 'video', file: clip.file, offsetSec: Math.min(offsetSec, clip.duration - 0.6), focus: s.focus};
};
