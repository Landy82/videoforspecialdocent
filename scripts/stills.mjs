// 핵심 장면 정지 이미지 + 커버 렌더링: node scripts/stills.mjs [초,초,...] [출력폴더]
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'node:path';
import fs from 'node:fs';

const times = (process.argv[2] ?? '1.2,2.6,3.6,4.6,7,9,11.6,13.4,14.6,16.5,17.8,19.2,22').split(',').map(Number);
const out = process.argv[3] ?? 'out/stills';
fs.mkdirSync(out, {recursive: true});
const browserExecutable = process.env.BROWSER_EXECUTABLE || undefined;
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const comp = await selectComposition({serveUrl, id: 'Shorts', browserExecutable});
for (const t of times) {
  const frame = Math.min(comp.durationInFrames - 1, Math.round(t * comp.fps));
  await renderStill({serveUrl, composition: comp, frame, output: `${out}/t${t.toFixed(1).padStart(4, '0')}.png`, browserExecutable});
  console.log('still', t);
}
const cover = await selectComposition({serveUrl, id: 'Cover', browserExecutable});
await renderStill({serveUrl, composition: cover, output: `${out}/cover.png`, browserExecutable});
console.log('cover done');
