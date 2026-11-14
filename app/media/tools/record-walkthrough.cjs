// Records the phone walk-through used for app/media/07-walkthrough-video/v3-full-frame-2x: full-frame and 2x sharp.
// Chrome's screencast in a real 2x window (Playwright's recordVideo films at 1x and pads the frame with grey).
// Usage (frontend on :3000, backend on :8000): node record-walkthrough.cjs <outDir> <batch.csv>
// then: ffmpeg -f concat -safe 0 -i <outDir>/list.txt -vf "fps=30,format=yuv420p" -c:v libx264 -crf 20 -movflags +faststart walkthrough.mp4
const { chromium, devices } = require('playwright');
const fs = require('fs');
const path = require('path');
const out = process.argv[2];
const W = 402, H = 874, DPR = 2; // iPhone 17 full screen, as when opened from the Home Screen
fs.mkdirSync(out, { recursive: true });
(async () => {
  // Real 2x window rather than emulated DPR: the screencast then delivers device pixels.
  const b = await chromium.launch({ args: [`--force-device-scale-factor=${DPR}`, `--window-size=${W},${H}`] });
  const dev = devices['iPhone 17'];
  const c = await b.newContext({ viewport: null, userAgent: dev.userAgent, hasTouch: true });
  const p = await c.newPage();
  const frames = [];
  let cdp;
  const startCast = async () => {
    if (cdp) { try { await cdp.send('Page.stopScreencast'); await cdp.detach(); } catch {} }
    cdp = await c.newCDPSession(p);
    cdp.on('Page.screencastFrame', async (f) => {
      const file = path.join(out, `f${String(frames.length).padStart(5, '0')}.jpg`);
      fs.writeFileSync(file, Buffer.from(f.data, 'base64'));
      frames.push({ file, t: f.metadata.timestamp });
      try { await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }); } catch {}
    });
    await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: W * DPR, maxHeight: H * DPR, everyNthFrame: 1 });
  };
  const pause = (ms) => p.waitForTimeout(ms);
  const go = async (url) => { await p.goto(url, { waitUntil: 'networkidle' }); await startCast(); };
  const scroll = async (dy, steps = 8) => { for (let i = 0; i < steps; i++) { await p.mouse.wheel(0, dy / steps); await pause(60); } };

  await go('http://localhost:3000/');
  await pause(1500);
  await p.getByRole('button', { name: /Ada Moreno/ }).first().click();
  await p.waitForURL(/memos/, { timeout: 40000 });
  await pause(2600);
  await scroll(700); await pause(1200);
  const factor = p.locator('section[aria-labelledby="factors"] button[aria-pressed]').first();
  await factor.click(); await pause(1800);
  await scroll(-700); await pause(1800);
  await factor.scrollIntoViewIfNeeded(); await factor.click(); await pause(800);
  await scroll(1400); await pause(1000); await scroll(1400); await pause(1000);
  await p.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' })); await pause(1000);
  await go('http://localhost:3000/'); await pause(800);
  await p.getByRole('button', { name: /Your bar|Change/ }).first().click(); await pause(1200);
  await p.getByRole('radio', { name: /\$1B\+/ }).click(); await pause(1500);
  await p.getByRole('radio', { name: /Bold/ }).click(); await pause(1500);
  await p.getByRole('button', { name: 'Reset' }).click(); await pause(600);
  await p.getByRole('button', { name: 'Done' }).click(); await pause(900);
  await go('http://localhost:3000/batch'); await pause(1200);
  await p.getByRole('button', { name: 'Or paste rows' }).click();
  await p.fill('#csv-text', fs.readFileSync(process.argv[3], 'utf8')); await pause(800);
  await p.getByRole('button', { name: 'Screen 3 founders' }).click();
  await p.waitForSelector('text=Your list is screened', { timeout: 60000 }); await pause(2500);
  await go('http://localhost:3000/'); await pause(2000);
  const end = Date.now() / 1000;
  await cdp.send('Page.stopScreencast');
  // ffmpeg concat list: each frame lasts until the next one arrives (Chrome only sends frames on change)
  let lines = [];
  const t0 = frames[0].t;
  let gaps = 0;
  for (let i = 0; i < frames.length; i++) {
    const next = i + 1 < frames.length ? frames[i + 1].t : frames[i].t + 1.5;
    const d = Math.max(next - frames[i].t, 0.001);
    if (d > 3) gaps++;
    lines.push(`file '${frames[i].file}'`, `duration ${d.toFixed(4)}`);
  }
  lines.push(`file '${frames[frames.length - 1].file}'`);
  fs.writeFileSync(path.join(out, 'list.txt'), lines.join('\n') + '\n');
  console.log(`frames ${frames.length}, span ${(frames[frames.length - 1].t - t0).toFixed(1)}s, gaps>3s ${gaps}`);
  await c.close();
  await b.close();
})().catch(e => { console.error('CRASH', e.message.split('\n')[0]); process.exit(1); });
