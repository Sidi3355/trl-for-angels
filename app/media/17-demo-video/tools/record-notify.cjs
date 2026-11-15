// Records c9_notify for the demo video: a screening in progress with its "Notify me when it's ready" button.
// Uses a made-up example founder (matched by its placeholder address: canned research, no cost). Headless Chrome
// always reports notification permission as denied, so the clip shows the button, not a permission state.
// Usage: node record-notify.cjs <rawDir>
const { chromium, devices } = require('playwright');
const fs = require('fs');
const path = require('path');
const raw = process.argv[2];
const W = 402, H = 874, DPR = 2, B = 'http://localhost:3000';
(async () => {
  const b = await chromium.launch({ args: [`--force-device-scale-factor=${DPR}`, `--window-size=${W},${H}`] });
  const c = await b.newContext({ viewport: null, userAgent: devices['iPhone 17'].userAgent, hasTouch: true });
  await c.addInitScript(() => { try { localStorage.setItem('screener.onboarded', '1'); } catch {} });
  const p = await c.newPage();
  await p.goto(B + '/', { waitUntil: 'networkidle' });
  // the dashboard's second example founder (Samir Haddad): its input carries the placeholder address
  const dir = path.join(raw, 'c9_notify');
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const frames = [];
  const cdp = await c.newCDPSession(p);
  cdp.on('Page.screencastFrame', async (f) => {
    const file = `f${String(frames.length).padStart(5, '0')}.jpg`;
    fs.writeFileSync(path.join(dir, file), Buffer.from(f.data, 'base64'));
    frames.push({ file, t: f.metadata.timestamp });
    try { await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }); } catch {}
  });
  await p.locator('section[aria-labelledby="latest"] button').nth(1).click();
  await p.waitForURL(/screenings\//);
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: W * DPR, maxHeight: H * DPR, everyNthFrame: 1 });
  await p.getByRole('button', { name: /Notify me/ }).waitFor();
  await p.waitForTimeout(3200);
  await cdp.send('Page.stopScreencast');
  fs.writeFileSync(path.join(dir, 'frames.json'), JSON.stringify({ frames, end: Date.now() / 1000 }));
  console.log('c9_notify', frames.length, 'frames');
  await b.close();
})().catch((e) => { console.error('CRASH', e.message); process.exit(1); });
