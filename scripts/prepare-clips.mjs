// 원본 8K 영상 조각(YYYYMMDD_HHMMSS_partNN.mp4)을 편집용 1080×1920 H.264 영상으로 변환한다.
// 같은 촬영(파일명 앞부분이 같음)에서 part 번호가 연속된 조각끼리는 하나로 이어 붙인다.
// 결과: public/clips/<촬영ID>_pAA-pBB.mp4 + public/clips/index.json
// 사용법: npm run clips   (이미 변환된 클립은 건너뜀)
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const SRC_DIRS = [ROOT, path.join(ROOT, 'assets', 'video')];
const OUT = path.join(ROOT, 'public', 'clips');
const BIN = path.join(ROOT, 'node_modules', '@remotion', 'compositor-linux-x64-gnu');
const env = {...process.env, LD_LIBRARY_PATH: BIN};
const ffmpeg = (args) => execFileSync(path.join(BIN, 'ffmpeg'), ['-v', 'error', '-y', ...args], {env, stdio: 'inherit'});
const probeDuration = (f) =>
	Number(execFileSync(path.join(BIN, 'ffprobe'), ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], {env}).toString().trim());

const RE = /^(\d{8}_\d{6})_part(\d+)\.mp4$/i;
const parts = [];
for (const dir of SRC_DIRS) {
	if (!fs.existsSync(dir)) continue;
	for (const name of fs.readdirSync(dir)) {
		const m = name.match(RE);
		if (m) parts.push({shoot: m[1], part: Number(m[2]), file: path.join(dir, name)});
	}
}
parts.sort((a, b) => a.shoot.localeCompare(b.shoot) || a.part - b.part);

// 연속된 part끼리 묶기
const runs = [];
for (const p of parts) {
	const last = runs.at(-1);
	if (last && last.shoot === p.shoot && last.parts.at(-1).part === p.part - 1) last.parts.push(p);
	else runs.push({shoot: p.shoot, parts: [p]});
}

fs.mkdirSync(OUT, {recursive: true});
const index = [];
for (const run of runs) {
	const pad = (n) => String(n).padStart(2, '0');
	const id = `${run.shoot}_p${pad(run.parts[0].part)}-p${pad(run.parts.at(-1).part)}`;
	const out = path.join(OUT, `${id}.mp4`);
	if (!fs.existsSync(out)) {
		console.log(`변환: ${id} (${run.parts.length}개 조각)`);
		const list = path.join(OUT, `${id}.txt`);
		fs.writeFileSync(list, run.parts.map((p) => `file '${p.file.replace(/'/g, "'\\''")}'`).join('\n'));
		ffmpeg(['-f', 'concat', '-safe', '0', '-i', list,
			'-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p',
			'-r', '30', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
			'-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', out]);
		fs.rmSync(list);
	}
	index.push({id, file: `clips/${id}.mp4`, shoot: run.shoot, parts: run.parts.map((p) => p.part), duration: probeDuration(out)});
}
fs.writeFileSync(path.join(OUT, 'index.json'), JSON.stringify(index, null, 2));
console.log(`완료: 클립 ${index.length}개 → public/clips/index.json`);
