// Playwright로 index.html의 window.seek(t)를 프레임마다 호출해 캡처한다.
//   node motion/render.mjs stills <frames> <outdir> [t1 t2 ...]   — 지정 시각만 (기본: 박마다)
//   node motion/render.mjs video  <frames> <outdir> [workers]      — 60fps × 서브프레임 3장 → <outdir>/sub/%05d.jpg
//   node motion/render.mjs audio  <out.wav>                        — Web Audio(OfflineAudioContext) 사운드트랙
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';
const require = createRequire(import.meta.url);
let pw;
try { pw = require('playwright'); } catch {
  const root = process.env.NPM_ROOT || require('child_process').execSync('npm root -g').toString().trim();
  pw = require(path.join(root, 'playwright'));
}
const HERE = path.dirname(fileURLToPath(import.meta.url));
const [mode, a1, a2, ...rest] = process.argv.slice(2);
const FPS = 60, SUB = 3, DUR = 30;

async function page(frames) {
  const browser = await pw.chromium.launch({ args: ['--allow-file-access-from-files', '--disable-web-security', '--disable-dev-shm-usage'] });
  const p = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  p.on('pageerror', e => console.error('pageerror', e.message));
  const url = 'file://' + path.join(HERE, 'index.html') + (frames ? '?frames=' + encodeURIComponent(path.resolve(frames)) : '');
  await p.goto(url);
  await p.evaluate(() => window.ready);
  return { browser, p };
}

async function shoot(p, t, file) {
  await p.evaluate(t => window.seek(t), t);
  await p.screenshot({ path: file, type: 'jpeg', quality: 92, clip: { x: 0, y: 0, width: 1080, height: 1920 } });
}

if (mode === 'stills') {
  fs.mkdirSync(a2, { recursive: true });
  const times = rest.length ? rest.map(Number) : Array.from({ length: 60 }, (_, i) => i * .5 + .42);
  const { browser, p } = await page(a1);
  for (const t of times) await shoot(p, t, path.join(a2, `t_${t.toFixed(2)}.jpg`));
  await browser.close();
} else if (mode === 'video') {
  const out = path.join(a2, 'sub');
  fs.mkdirSync(out, { recursive: true });
  const workers = Number(rest[0] || 6);
  const N = DUR * FPS * SUB;
  const from = Number(rest[1] || 0), to = Number(rest[2] || N);
  const jobs = Array.from({ length: workers }, async (_, w) => {
    let ctx = await page(a1), done = 0;
    for (let i = from + w; i < to; i += workers) {
      const f = path.join(out, String(i).padStart(5, '0') + '.jpg');
      if (fs.existsSync(f)) continue;                      // 이어서 렌더 가능
      for (let attempt = 0; ; attempt++) {
        try {
          if (done > 0 && done % 400 === 0) { await ctx.browser.close(); ctx = await page(a1); }  // 메모리 정리
          await shoot(ctx.p, i / (FPS * SUB), f + '.tmp.jpg');
          break;
        } catch (e) {                                       // 탭이 죽으면 새로 띄워 같은 프레임부터
          console.error('retry', i, e.message.split('\n')[0]);
          if (attempt > 3) throw e;
          try { await ctx.browser.close(); } catch {}
          ctx = await page(a1);
        }
      }
      fs.renameSync(f + '.tmp.jpg', f);
      done++;
      if (i % 600 < workers) console.log('sub', i, '/', N);
    }
    await ctx.browser.close();
  });
  await Promise.all(jobs);
} else if (mode === 'audio') {
  const browser = await pw.chromium.launch();
  const p = await browser.newPage();
  p.on('pageerror', e => console.error('pageerror', e.message));
  await p.goto('file://' + path.join(HERE, 'audio.html'));
  const b64 = await p.evaluate(() => window.renderWav());
  fs.writeFileSync(a1, Buffer.from(b64, 'base64'));
  await browser.close();
} else {
  console.log('usage: stills|video|audio');
}
