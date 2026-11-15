#!/usr/bin/env node
// Checks the whole cut:  node scenes/check.js
//  1. every page agrees with manifest.json (id, duration, voice start, clip slots);
//  2. every frame of every scene seeks without an error, and no caption runs past two lines;
//  3. every join: the last frame of a scene against the first frame of the next (written side by side to
//     previews/join-<n>.png), with the number of pixels that differ.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
(async () => {
  const m = JSON.parse(fs.readFileSync(path.join(__dirname, 'manifest.json'), 'utf8'));
  const out = path.join(__dirname, 'previews');
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const errs = [];
  p.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
  p.on('console', (c) => { if (c.type() === 'error') errs.push('console: ' + c.text()); });
  p.on('request', (r) => { if (!r.url().startsWith('file://') && !r.url().startsWith('data:')) errs.push('network request: ' + r.url()); });
  let total = 0;
  const first = {}, last = {};
  for (const s of m) {
    await p.goto('file://' + path.join(__dirname, s.file));
    const sc = await p.evaluate(() => window.SCENE);
    if (sc.id !== s.id || sc.duration !== s.duration || sc.voiceAt !== s.voice.at || JSON.stringify(sc.clips) !== JSON.stringify(s.clips))
      errs.push('manifest and page disagree: ' + s.id + ' ' + JSON.stringify(sc));
    const n = Math.round(s.duration * 30);
    const r = await p.evaluate(async (n) => {
      let lines = 0, ph = 0;
      for (let i = 0; i <= n; i++) {
        await window.seek(i / 30);
        const t = document.querySelector('#cap .txt');
        if (!document.querySelector('#cap').classList.contains('off')) lines = Math.max(lines, Math.round(t.getBoundingClientRect().height / parseFloat(getComputedStyle(t).lineHeight)));
        if (document.querySelector('.phone.is-placeholder')) ph++;
      }
      return { lines, ph };
    }, n);
    if (r.lines > 2) errs.push(s.id + ': a caption runs to ' + r.lines + ' lines');
    if (r.ph) errs.push(s.id + ': ' + r.ph + ' frames show a placeholder still');
    await p.evaluate(() => window.seek(0)); first[s.id] = path.join(out, '_first-' + s.id + '.png'); await p.screenshot({ path: first[s.id] });
    await p.evaluate((d) => window.seek(d), s.duration); last[s.id] = path.join(out, '_last-' + s.id + '.png'); await p.screenshot({ path: last[s.id] });
    total += s.duration;
    console.log(s.id, s.duration + ' s', n + ' frames', 'caption lines <= ' + r.lines);
  }
  await b.close();
  for (let i = 0; i + 1 < m.length; i++) {
    const a = last[m[i].id], c = first[m[i + 1].id];
    let diff = '?';
    try { execFileSync('compare', ['-metric', 'AE', a, c, 'null:'], { stdio: ['ignore', 'pipe', 'pipe'] }); diff = '0'; }
    catch (e) { diff = String(e.stderr || '').trim().split(/\s/)[0]; }
    try { execFileSync('convert', [a, c, '+append', '-resize', '50%', path.join(out, 'join-' + (i + 1) + '-' + m[i].id + '-to-' + m[i + 1].id + '.png')]); } catch (e) {}
    console.log('join ' + m[i].id + ' -> ' + m[i + 1].id + ': ' + diff + ' pixels differ');
    if (diff !== '0') errs.push('join ' + m[i].id + ' -> ' + m[i + 1].id + ' does not match (' + diff + ' pixels)');
  }
  Object.values(first).concat(Object.values(last)).forEach((f) => fs.unlinkSync(f));
  console.log('total ' + total.toFixed(1) + ' s');
  console.log(errs.length ? 'PROBLEMS:\n' + errs.join('\n') : 'all checks passed');
  process.exit(errs.length ? 1 : 0);
})();
