// Renders the demo video from the scenes (scenes/manifest.json): each scene page is opened at 1920x1080, stepped
// frame by frame with its seek(t), and screenshotted; ffmpeg then encodes each scene and joins them with the
// voiceover (each section placed at its scene's start plus voice.at).
// Usage: node tools/render-video.cjs [sceneId ...]   (default: every scene; then the full video)
// Output: build/<id>.mp4 per scene (silent), build/voice.wav, and halomark-demo.mp4.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const SCENES = path.join(ROOT, 'scenes');
const BUILD = path.join(ROOT, 'build');
const FPS = 30;
const manifest = JSON.parse(fs.readFileSync(path.join(SCENES, 'manifest.json'), 'utf8'));
const only = process.argv.slice(2);
const ff = (args) => execFileSync('ffmpeg', ['-y', '-loglevel', 'error', ...args], { stdio: 'inherit' });

async function renderScene(browser, scene) {
  const dir = path.join(BUILD, 'frames', scene.id);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  await page.goto('file://' + path.join(SCENES, scene.file), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  const n = Math.round(scene.duration * FPS);
  for (let i = 0; i < n; i++) {
    await page.evaluate((t) => window.seek(t), i / FPS);
    await page.screenshot({ path: path.join(dir, `${String(i + 1).padStart(6, '0')}.jpg`), type: 'jpeg', quality: 94 });
  }
  await page.close();
  ff(['-framerate', String(FPS), '-i', path.join(dir, '%06d.jpg'), '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
    '-pix_fmt', 'yuv420p', path.join(BUILD, `${scene.id}.mp4`)]);
  console.log(scene.id, n, 'frames', errors.length ? 'ERRORS: ' + [...new Set(errors)].slice(0, 3).join(' | ') : '');
}

function assemble() {
  // video: the scenes back to back
  const list = path.join(BUILD, 'scenes.txt');
  fs.writeFileSync(list, manifest.map((s) => `file '${path.join(BUILD, s.id + '.mp4')}'`).join('\n') + '\n');
  ff(['-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', path.join(BUILD, 'video.mp4')]);
  // audio: each section at its scene's start + voice.at
  let start = 0;
  const inputs = [], filters = [];
  manifest.forEach((s, i) => {
    inputs.push('-i', path.resolve(SCENES, s.voice.file));
    const ms = Math.round((start + s.voice.at) * 1000);
    filters.push(`[${i}:a]aresample=48000,adelay=${ms}|${ms}[a${i}]`);
    start += s.duration;
  });
  const mix = manifest.map((_, i) => `[a${i}]`).join('') + `amix=inputs=${manifest.length}:normalize=0,atrim=0:${start.toFixed(3)},apad=whole_dur=${start.toFixed(3)}[out]`;
  ff([...inputs, '-filter_complex', filters.join(';') + ';' + mix, '-map', '[out]', '-ac', '2', path.join(BUILD, 'voice.wav')]);
  ff(['-i', path.join(BUILD, 'video.mp4'), '-i', path.join(BUILD, 'voice.wav'), '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
    '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-shortest', '-movflags', '+faststart', path.join(ROOT, 'halomark-demo.mp4')]);
  console.log('halomark-demo.mp4:', start.toFixed(2), 's');
}

(async () => {
  fs.mkdirSync(BUILD, { recursive: true });
  const browser = await chromium.launch();
  const todo = manifest.filter((s) => !only.length || only.includes(s.id));
  // a few scenes at a time
  const queue = [...todo];
  await Promise.all([0, 1, 2].map(async () => { while (queue.length) await renderScene(browser, queue.shift()); }));
  await browser.close();
  // join the video whenever every scene has been rendered (a partial re-render re-joins too)
  if (manifest.every((s) => fs.existsSync(path.join(BUILD, `${s.id}.mp4`)))) assemble();
})().catch((e) => { console.error('CRASH', e.message); process.exit(1); });
