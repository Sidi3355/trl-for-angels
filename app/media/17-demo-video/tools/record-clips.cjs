// Records the phone clips for the demo video (app/media/17-demo-video), as raw screencast frames per segment.
// Real stack: frontend :3000, backend :8000 with AGENT=claude (real research), ANSWERER/DECIDER=kev (real models),
// ARTIFACTS_DIR=shared/artifacts. One real founder (Tope Awotona, about $0.25 of research); the rest are the
// made-up example founders. The voice-note clip feeds voice-note/note.wav to the browser's fake microphone.
// Usage: node record-clips.cjs <rawDir> <noteWav> <batchCsv>   then tools/frames-to-clips.py makes 30 fps clips.
const { chromium, devices } = require('playwright');
const fs = require('fs');
const path = require('path');
const [raw, noteWav, csvPath] = process.argv.slice(2);
const W = 402, H = 874, DPR = 2;
const B = 'http://localhost:3000';
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

(async () => {
  const b = await chromium.launch({
    args: [`--force-device-scale-factor=${DPR}`, `--window-size=${W},${H}`, '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream', `--use-file-for-fake-audio-capture=${noteWav}`, '--autoplay-policy=no-user-gesture-required'],
  });
  const dev = devices['iPhone 17'];
  const c = await b.newContext({ viewport: null, userAgent: dev.userAgent, hasTouch: true });
  await c.grantPermissions(['microphone', 'notifications'], { origin: B });
  await c.addInitScript(() => { try { localStorage.setItem('screener.onboarded', '1'); } catch {} });
  const p = await c.newPage();
  p.on('pageerror', (e) => log('PAGE ERROR', e.message));
  let cdp = null, seg = null;
  const start = async (name) => {
    const dir = path.join(raw, name);
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(dir, { recursive: true });
    seg = { name, dir, frames: [] };
    const s = seg;
    cdp = await c.newCDPSession(p);
    cdp.on('Page.screencastFrame', async (f) => {
      const file = path.join(s.dir, `f${String(s.frames.length).padStart(5, '0')}.jpg`);
      fs.writeFileSync(file, Buffer.from(f.data, 'base64'));
      s.frames.push({ file: path.basename(file), t: f.metadata.timestamp });
      try { await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }); } catch {}
    });
    await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: W * DPR, maxHeight: H * DPR, everyNthFrame: 1 });
    log('start', name);
  };
  const stop = async () => {
    await p.waitForTimeout(150);
    try { await cdp.send('Page.stopScreencast'); await cdp.detach(); } catch {}
    const end = Date.now() / 1000;
    fs.writeFileSync(path.join(seg.dir, 'frames.json'), JSON.stringify({ frames: seg.frames, end }));
    log('stop', seg.name, seg.frames.length, 'frames,', seg.frames.length ? (end - seg.frames[0].t).toFixed(1) : 0, 's');
  };
  const pause = (ms) => p.waitForTimeout(ms);
  const smoothTo = async (y, ms = 900) => {
    await p.evaluate(([y]) => window.scrollTo({ top: y, behavior: 'smooth' }), [y]);
    await pause(ms);
  };
  const scrollToEl = async (locator, offset = 90, ms = 1100) => {
    const y = await locator.evaluate((el, off) => el.getBoundingClientRect().top + window.scrollY - off, offset);
    await smoothTo(Math.max(0, y), ms);
  };

  // ONLY=founder records c1-c6 (the real founder); ONLY=extras records c7-c10 (no research, no cost).
  // MEMO_URL=<a finished memo> resumes after the live research, without paying for it again.
  const only = process.env.ONLY || 'all';
  if (only !== 'extras') {
  let memoUrl = process.env.MEMO_URL || null;
  if (!memoUrl) {
  // ---- c1: the dashboard, typing a real founder's name
  await p.goto(B + '/', { waitUntil: 'networkidle' });
  await pause(600);
  await start('c1_type');
  await pause(900);
  await p.locator('#quick').click();
  await p.keyboard.type('Tope Awotona', { delay: 95 });
  await pause(700);
  await p.getByRole('button', { name: 'Screen founder' }).click();
  await p.waitForURL(/screenings\//, { timeout: 20000 });
  await pause(1600);
  await stop();

  // ---- c2: the live research, through to the memo (sped up in the edit)
  const t0 = Date.now();
  await start('c2_research');
  await p.waitForURL(/memos\//, { timeout: 600000 });
  await p.getByText('Verdict', { exact: true }).first().waitFor({ timeout: 60000 });
  await pause(2500);
  await stop();
  memoUrl = p.url();
  log('research + verdict took', ((Date.now() - t0) / 1000).toFixed(0), 's; memo', memoUrl);
  fs.writeFileSync(path.join(raw, 'memo-url.txt'), memoUrl);
  } else {
    await p.goto(memoUrl, { waitUntil: 'networkidle' });
  }

  // ---- c3: the anonymised profile the model reads
  await start('c3_profile');
  await pause(500);
  const hood = p.getByRole('button', { name: /Under the hood/ });
  await scrollToEl(hood, 300, 1600);
  await hood.click();
  await pause(700);
  await scrollToEl(p.getByText('What the model read'), 70, 1200);
  await pause(2600);
  await smoothTo(await p.evaluate(() => window.scrollY + 420), 1400);
  await pause(1200);
  await stop();

  // ---- c4: the verdict, counting up on arrival
  await p.goto(memoUrl, { waitUntil: 'domcontentloaded' });
  await start('c4_verdict');
  await p.getByText('Verdict', { exact: true }).first().waitFor({ timeout: 30000 });
  await pause(4200);
  await stop();

  // ---- c5: changing the bar
  await start('c5_bar');
  await pause(500);
  await p.getByRole('button', { name: /Your bar/ }).first().click();
  await pause(1100);
  await p.getByRole('radio', { name: /\$1B\+/ }).click();
  await pause(900);
  await p.getByRole('radio', { name: '8 years' }).click();
  await pause(900);
  await p.getByRole('radio', { name: /Bold/ }).click();
  await pause(1100);
  await p.getByRole('button', { name: 'Done' }).click();
  await pause(2400);
  await stop();
  // back to the default bar, off camera
  await p.getByRole('button', { name: /Your bar/ }).first().click();
  await pause(500);
  await p.getByRole('button', { name: 'Reset' }).first().click();
  await pause(300);
  await p.getByRole('button', { name: 'Done' }).click();
  await pause(500);

  // ---- c6: what moves the score, then a what-if (two takes, cut together in the edit)
  log('waiting for every driver');
  await p.waitForFunction(() => !document.querySelector('section[aria-labelledby="factors"] [role="status"]'), null, { timeout: 900000 });
  log('drivers complete');
  await smoothTo(0, 300);
  await start('c6a_factors');
  await pause(400);
  await scrollToEl(p.locator('#factors'), 70, 1400);
  await pause(1500);
  await p.locator('section[aria-labelledby="factors"] li button').first().click();
  await pause(900);
  await stop();
  await p.waitForFunction(() => !document.body.innerText.includes('Re-scoring'), null, { timeout: 180000 });
  await pause(500);
  await start('c6b_whatif');
  await pause(300);
  await smoothTo(0, 1300);
  await pause(2600);
  await stop();

  // ---- c7: screening a list (the made-up example founders: canned research, real Kev answers from the demo cache)
  } // end of the real founder's clips
  if (only === 'founder') { await b.close(); log('done'); return; }

  await p.goto(B + '/batch', { waitUntil: 'networkidle' });
  await pause(500);
  await start('c7_list');
  await pause(500);
  await p.getByRole('button', { name: 'Or paste rows' }).click();
  await pause(400);
  await p.fill('#csv-text', fs.readFileSync(csvPath, 'utf8'));
  await pause(700);
  await p.getByRole('button', { name: /Screen 3 founders/ }).click();
  await p.waitForSelector('text=Your list is screened', { timeout: 120000 });
  await pause(2500);
  await stop();

  // ---- c8: a voice note fills the form (real transcription and sorting; the "microphone" plays note.wav)
  await p.goto(B + '/new', { waitUntil: 'networkidle' });
  await pause(500);
  const rec = p.getByRole('button', { name: 'Record a voice note' });
  await scrollToEl(rec, 330, 50);
  await start('c8a_record');
  await pause(500);
  await rec.click();
  await pause(3200);
  await stop();
  await pause(7500); // the rest of the note
  await p.getByRole('button', { name: /Stop recording/ }).click();
  log('recorded; waiting for the form to fill');
  await p.waitForFunction(() => /Filled in:|From your voice note/.test(document.body.innerText), null, { timeout: 120000 }).catch(() => log('no fill signal'));
  await pause(1500);
  await smoothTo(0, 300);
  await start('c8b_filled');
  await pause(400);
  await smoothTo(await p.evaluate(() => Math.max(0, document.body.scrollHeight * 0.18)), 1600);
  await pause(1800);
  await stop();

  // ---- c9: notifications
  await p.goto(B + '/settings', { waitUntil: 'networkidle' });
  await pause(400);
  await start('c9_notify');
  await pause(400);
  await scrollToEl(p.getByText('Notifications', { exact: true }).first(), 240, 1200);
  await pause(2200);
  await stop();

  // ---- c10: the on-device profile
  await p.goto(B + '/account', { waitUntil: 'networkidle' });
  await pause(400);
  await p.getByPlaceholder('e.g. Sam Rivera').fill('Sam Rivera');
  await p.getByRole('button', { name: 'Continue' }).click();
  await pause(800);
  await smoothTo(0, 200);
  await start('c10_profile');
  await pause(600);
  for (const s of ['fintech', 'developer tools', 'healthtech']) {
    const chip = p.getByRole('checkbox', { name: s, exact: true }).first();
    if (await chip.count()) { await chip.click(); await pause(450); }
  }
  await pause(500);
  await smoothTo(260, 1200);
  await pause(1200);
  await stop();

  await b.close();
  log('done');
})().catch((e) => { console.error('CRASH', e.message.split('\n').slice(0, 3).join(' | ')); process.exit(1); });
