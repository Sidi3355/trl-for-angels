#!/usr/bin/env node
// Renders preview frames: node scenes/preview.js [sceneId ...] [--t 1,2.5,...] [--every 2]
// Writes scenes/previews/<id>-<t>.png at 1x. Also checks that seeking backwards gives the same pixels.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
(async () => {
  const args = process.argv.slice(2);
  const ti = args.indexOf('--t'), ei = args.indexOf('--every');
  const times = ti >= 0 ? args[ti + 1].split(',').map(Number) : null;
  const every = ei >= 0 ? Number(args[ei + 1]) : 2;
  const ids = args.filter((a, i) => !a.startsWith('--') && i !== ti + 1 - (ti < 0 ? 1e9 : 0) && i !== ei + 1 - (ei < 0 ? 1e9 : 0));
  const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'manifest.json'), 'utf8'));
  const out = path.join(__dirname, 'previews');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const bad = [];
  page.on('pageerror', (e) => bad.push('pageerror: ' + e.message));
  page.on('request', (r) => { if (!r.url().startsWith('file://') && !r.url().startsWith('data:')) bad.push('network request: ' + r.url()); });
  for (const sc of manifest) {
    if (ids.length && !ids.includes(sc.id)) continue;
    await page.goto('file://' + path.join(__dirname, sc.file));
    const ts = times || [];
    if (!times) { for (let t = 0; t < sc.duration; t += every) ts.push(+t.toFixed(2)); ts.push(sc.duration); }
    const hash = {};
    for (const t of ts) {
      await page.evaluate((x) => window.seek(x), t);
      const buf = await page.screenshot({ path: path.join(out, sc.id + '-' + t.toFixed(2) + '.png') });
      hash[t] = crypto.createHash('md5').update(buf).digest('hex');
    }
    // seek backwards and compare
    let same = true;
    for (const t of ts.slice().reverse()) {
      await page.evaluate((x) => window.seek(x), t);
      const buf = await page.screenshot();
      if (crypto.createHash('md5').update(buf).digest('hex') !== hash[t]) { same = false; bad.push(sc.id + ' differs when seeking back to ' + t); }
    }
    const over = await page.evaluate(() => ({ w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight }));
    console.log(sc.id, 'frames:', ts.length, 'backwards seek identical:', same, 'doc', over.w + 'x' + over.h);
  }
  await browser.close();
  if (bad.length) { console.log('PROBLEMS:\n' + bad.join('\n')); process.exit(1); }
})();
