/* Halomark demo video: the seekable timeline.
 *
 * Every scene page calls HM.scene({...}) once, at load. All motion is Web Animations created here and paused;
 * window.seek(t) sets their currentTime, picks the clip frames, and sets the captions. Nothing runs on a clock:
 * no timers, no requestAnimationFrame, no Date, no unseeded random numbers. The same t always gives the same frame.
 */
(function () {
  'use strict';
  var HM = (window.HM = {});
  var S = null;            // the scene config
  var hooks = [];          // pure functions of t, run on every seek (counters and the like)
  var clipState = [];      // one entry per clip slot
  var capEl = null, capTxt = null, capCue = -2;
  var EASE = {
    set: 'cubic-bezier(.16,.84,.24,1)',     // paper settling: fast, then eases to rest
    strike: 'cubic-bezier(.7,0,.9,.4)',     // a stamp coming down: accelerates into the page
    inout: 'cubic-bezier(.6,0,.2,1)',
    linear: 'linear'
  };
  HM.EASE = EASE;

  function el(x) { return typeof x === 'string' ? document.querySelector(x) : x; }
  function els(x) { return typeof x === 'string' ? Array.prototype.slice.call(document.querySelectorAll(x)) : (x.length !== undefined && !x.tagName ? Array.prototype.slice.call(x) : [x]); }
  HM.el = el; HM.els = els;

  /* One animation per element per group of properties, spanning the whole scene.
   * frames: [[timeSeconds, {css props}, easingToNextFrame?], ...] in time order. Held before the first and after the last. */
  HM.tl = function (target, frames) {
    var node = el(target), D = S.duration * 1000, kf = [];
    frames = frames.slice().sort(function (a, b) { return a[0] - b[0]; });
    if (frames[0][0] > 0) frames.unshift([0, frames[0][1], 'linear']);
    var last = frames[frames.length - 1];
    if (last[0] < S.duration) frames.push([S.duration, last[1], 'linear']);
    frames.forEach(function (f) {
      var k = Object.assign({}, f[1]);
      k.offset = Math.min(1, Math.max(0, f[0] / S.duration));
      k.easing = EASE[f[2]] || f[2] || 'linear';
      kf.push(k);
    });
    var a = node.animate(kf, { duration: D, fill: 'both', easing: 'linear' });
    a.pause();
    if (a.persist) a.persist();
    return a;
  };

  /* Print-shop moves. Each takes the time it starts; `out` (optional) is when it leaves again. */
  // set: slides up a little as it appears, like a line of type dropped into place
  HM.set = function (target, t, o) {
    o = o || {};
    var dy = o.dy === undefined ? 34 : o.dy, dur = o.dur || 0.5, stag = o.stagger || 0;
    els(target).forEach(function (n, i) {
      var t0 = t + i * stag;
      var f = [[t0, { opacity: 0, transform: 'translateY(' + dy + 'px)' }, 'set'], [t0 + dur, { opacity: 1, transform: 'translateY(0px)' }]];
      // opacity lands early so type is solid while it is still settling
      f.splice(1, 0, [t0 + dur * 0.35, { opacity: 1, transform: 'translateY(' + dy * 0.22 + 'px)' }, 'set']);
      if (o.out !== undefined) {
        f.push([o.out, { opacity: 1, transform: 'translateY(0px)' }, 'inout']);
        f.push([o.out + 0.3, { opacity: 0, transform: 'translateY(' + -dy * 0.6 + 'px)' }]);
      }
      HM.tl(n, f);
    });
  };
  // strike: comes down onto the page like a stamp: large and faint, then hits, with a small recoil
  HM.strike = function (target, t, o) {
    o = o || {};
    var rot = o.rot || 0, from = o.from || 1.55, dur = o.dur || 0.16, stag = o.stagger || 0;
    els(target).forEach(function (n, i) {
      var t0 = t + i * stag, r = 'rotate(' + rot + 'deg) ';
      var f = [
        [t0 - dur, { opacity: 0, transform: r + 'scale(' + from + ')' }, 'strike'],
        [t0, { opacity: 1, transform: r + 'scale(0.965)' }, 'set'],
        [t0 + 0.14, { opacity: 1, transform: r + 'scale(1)' }]
      ];
      if (o.out !== undefined) {
        f.push([o.out, { opacity: 1, transform: r + 'scale(1)' }, 'inout']);
        f.push([o.out + 0.25, { opacity: 0, transform: r + 'scale(1)' }]);
      }
      HM.tl(n, f);
    });
  };
  // wipe: revealed edge to edge, like a sheet pulled out of a press. dir: up | down | left | right
  HM.wipe = function (target, t, o) {
    o = o || {};
    var dur = o.dur || 0.45, dir = o.dir || 'right', stag = o.stagger || 0;
    var hidden = { right: 'inset(0 100% 0 0)', left: 'inset(0 0 0 100%)', down: 'inset(0 0 100% 0)', up: 'inset(100% 0 0 0)' }[dir];
    var gone = { right: 'inset(0 0 0 100%)', left: 'inset(0 100% 0 0)', down: 'inset(100% 0 0 0)', up: 'inset(0 0 100% 0)' }[dir];
    els(target).forEach(function (n, i) {
      var t0 = t + i * stag;
      var f = [[t0, { clipPath: hidden }, 'inout'], [t0 + dur, { clipPath: 'inset(0 0 0 0)' }]];
      if (o.out !== undefined) { f.push([o.out, { clipPath: 'inset(0 0 0 0)' }, 'inout']); f.push([o.out + dur, { clipPath: gone }]); }
      HM.tl(n, f);
    });
  };
  // out: leaves edge to edge (the opposite of wipe), for something that is there from the start
  HM.out = function (target, t, o) {
    o = o || {};
    var dur = o.dur || 0.4, dir = o.dir || 'left';
    var gone = { right: 'inset(0 0 0 100%)', left: 'inset(0 100% 0 0)', down: 'inset(100% 0 0 0)', up: 'inset(0 0 100% 0)' }[dir];
    els(target).forEach(function (n) { HM.tl(n, [[t, { clipPath: 'inset(0 0 0 0)' }, 'inout'], [t + dur, { clipPath: gone }]]); });
  };
  // fade: plain opacity, for quiet things
  HM.fade = function (target, t, o) {
    o = o || {};
    var dur = o.dur || 0.3, to = o.to === undefined ? 1 : o.to, stag = o.stagger || 0;
    els(target).forEach(function (n, i) {
      var t0 = t + i * stag;
      var f = [[t0, { opacity: o.from || 0 }, 'inout'], [t0 + dur, { opacity: to }]];
      if (o.out !== undefined) { f.push([o.out, { opacity: to }, 'inout']); f.push([o.out + dur, { opacity: o.outTo || 0 }]); }
      HM.tl(n, f);
    });
  };
  // jolt: the page takes the blow of a stamp
  HM.jolt = function (target, t, px) {
    px = px || 5;
    HM.tl(target, [
      [t, { transform: 'translate(0px,0px)' }, 'linear'],
      [t + 0.04, { transform: 'translate(' + px * 0.4 + 'px,' + px + 'px)' }, 'set'],
      [t + 0.22, { transform: 'translate(0px,0px)' }]
    ]);
  };
  // count: a figure counting up between two times (text content, set on seek)
  HM.count = function (target, t0, t1, a, b, fmt) {
    var n = el(target);
    hooks.push(function (t) {
      var p = t <= t0 ? 0 : t >= t1 ? 1 : (t - t0) / (t1 - t0);
      p = 1 - Math.pow(1 - p, 3);
      var v = Math.round(a + (b - a) * p), s = fmt ? fmt(v) : String(v);
      if (n.textContent !== s) n.textContent = s;
    });
  };
  HM.onSeek = function (fn) { hooks.push(fn); };
  // seeded random numbers (mulberry32), for patterns that must be the same on every render
  HM.rng = function (seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
      var x = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
      return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
    };
  };

  /* Brand geometry (brand/mark.ts.txt) */
  var PUNCH = 'M10.87 1.13Q12 0 13.6 0L50.4 0Q52 0 53.13 1.13L62.87 10.87Q64 12 64 13.6L64 50.4Q64 52 62.87 53.13L53.13 62.87Q52 64 50.4 64L13.6 64Q12 64 10.87 62.87L1.13 53.13Q0 52 0 50.4L0 13.6Q0 12 1.13 10.87Z';
  var HALO = 'M10.86 39.7C8.02 31.91 15.19 22.15 26.87 17.9C38.55 13.65 50.31 16.52 53.14 24.3C55.98 32.09 48.81 41.85 37.13 46.1C25.45 50.35 13.69 47.48 10.86 39.7ZM22.49 36.32C20.61 33.2 24.69 27.3 31.6 23.14C38.51 18.99 45.64 18.16 47.51 21.28C49.39 24.4 45.31 30.3 38.4 34.46C31.49 38.61 24.36 39.44 22.49 36.32Z';
  HM.PUNCH = PUNCH; HM.HALO = HALO;
  // fill every <span data-wordmark> with HAL(halo)MARK, each letter its own span so it can be set letter by letter
  // and every <svg data-mark> / <svg data-punch="meet|closer|pass"> with the geometry
  function brand() {
    els('[data-wordmark]').forEach(function (n) {
      var h = '';
      'HAL'.split('').forEach(function (c) { h += '<span class="wl">' + c + '</span>'; });
      h += '<span class="wl"><svg viewBox="10.24 15.94 43.52 32.12"><path fill-rule="evenodd" d="' + HALO + '"/></svg></span>';
      'MARK'.split('').forEach(function (c) { h += '<span class="wl">' + c + '</span>'; });
      n.classList.add('wordmark'); n.innerHTML = h;
    });
    els('svg[data-mark]').forEach(function (n) {
      n.setAttribute('viewBox', '0 0 64 64');
      n.innerHTML = '<path fill="var(--brand)" d="' + PUNCH + '"/><path fill="var(--paper)" fill-rule="evenodd" d="' + HALO + '"/>';
    });
    var icons = {
      meet: '<path d="M23 41L39 25" fill="none" stroke="#04210f" stroke-width="5"/><path d="M26.5 24.5H39.5V37.5" fill="none" stroke="#04210f" stroke-width="5" stroke-linejoin="miter"/>',
      closer: '<path d="M32 18V36" stroke="#2a1800" stroke-width="6" stroke-linecap="square"/><rect x="29" y="42" width="6" height="6" fill="#2a1800"/>',
      pass: '<path d="M22 32H42" stroke="#f4f4f0" stroke-width="5.5" stroke-linecap="square"/>',
      ask: ''
    };
    var fills = { meet: 'var(--meet)', closer: 'var(--closer)', pass: 'var(--pass)' };
    els('svg[data-punch]').forEach(function (n) {
      var k = n.getAttribute('data-punch');
      n.setAttribute('viewBox', '0 0 64 64');
      n.innerHTML = '<path fill="' + fills[k] + '" d="' + PUNCH + '"/>' + icons[k];
    });
  }

  /* Clips: JPEG sequences in ../clips/<name>/000001.jpg ..., described by HM_CLIPS (data.js, from meta.json). */
  function pad(n) { return ('000000' + n).slice(-6); }
  function clipSrc(c, t) {
    var m = c.meta;
    if (m && m.frames > 0) {
      var i = Math.floor((t - c.from) * (m.fps || 30) + 1e-6) + 1;
      i = Math.max(1, Math.min(m.frames, i));
      return '../clips/' + c.name + '/' + pad(i) + '.jpg';
    }
    return '../clips/' + c.name + '/placeholder.png';
  }
  function setImg(img, src) {
    if (img.getAttribute('src') === src && img.complete && img.naturalWidth) return Promise.resolve(true);
    img.setAttribute('src', src);
    return img.decode().then(function () { return true; }, function () { return false; });
  }
  function seekClips(t) {
    return Promise.all(clipState.map(function (c) {
      var want = clipSrc(c, t), ph = '../clips/' + c.name + '/placeholder.png';
      return setImg(c.img, want).then(function (ok) {
        if (ok || want === ph) return ok;
        return setImg(c.img, ph); // a missing frame: fall back to the still
      }).then(function (ok) {
        var real = ok && c.img.getAttribute('src') !== ph;
        c.img.style.visibility = ok ? 'visible' : 'hidden';
        c.real = real;
      });
    })).then(function () {
      // the phone says so when it is showing a still in place of footage (visible in previews; never in the final cut)
      els('.phone').forEach(function (p) {
        var mine = clipState.filter(function (c) { return p.contains(c.img); });
        var cur = mine[0] || null;
        mine.forEach(function (c) { if (t >= c.from) cur = c; });
        p.classList.toggle('is-placeholder', !!cur && !cur.real);
        var tag = p.querySelector('.ph-tag');
        if (tag && cur) tag.textContent = 'Placeholder still · ' + cur.name;
      });
    });
  }

  /* Captions, from the voiceover alignment (HM_VOICE, data.js). Words turn to ink as they are spoken. */
  function buildCap() {
    capEl = document.createElement('div'); capEl.id = 'cap'; capEl.className = 'off';
    capEl.innerHTML = '<div class="bar"></div><div class="txt"></div>';
    document.body.appendChild(capEl);
    capTxt = capEl.querySelector('.txt');
  }
  function seekCap(t) {
    var v = (window.HM_VOICE || {})[S.id];
    if (!v || S.captions === false) { capEl.className = 'off'; return; }
    var tv = t - S.voiceAt, cues = v.cues, idx = -1;
    for (var i = 0; i < cues.length; i++) {
      var c = cues[i], start = c[0].s - 0.12, end = c[c.length - 1].e;
      var next = i + 1 < cues.length ? cues[i + 1][0].s - 0.12 : Infinity;
      var until = Math.min(next, end + 0.7); // hold a little after the last word, never into the next cue
      if (tv >= start && tv < until) { idx = i; break; }
    }
    if (idx !== capCue) {
      capCue = idx;
      capTxt.textContent = '';
      if (idx >= 0) cues[idx].forEach(function (w, j) {
        var s = document.createElement('span'); s.textContent = w.w; capTxt.appendChild(s);
        if (j < cues[idx].length - 1) capTxt.appendChild(document.createTextNode(' '));
      });
    }
    capEl.className = idx < 0 ? 'off' : '';
    if (idx >= 0) {
      var spans = capTxt.children;
      cues[idx].forEach(function (w, j) { spans[j].className = tv >= w.s - 0.03 ? 'said' : ''; });
    }
  }

  var readyP = null;
  /* HM.scene({ id, duration, voiceAt, clips: [{name, from, to, img}], build: function (HM) {...} }) */
  HM.scene = function (cfg) {
    S = cfg;
    window.SCENE = { id: cfg.id, duration: cfg.duration, voiceAt: cfg.voiceAt, clips: (cfg.clips || []).map(function (c) { return { name: c.name, from: c.from, to: c.to }; }) };
    brand();
    buildCap();
    var metas = window.HM_CLIPS || {};
    clipState = (cfg.clips || []).map(function (c) {
      return { name: c.name, from: c.from, to: c.to, img: el(c.img), meta: metas[c.name] || null, real: false };
    });
    // "sped up" badges: <el data-speed="clipname"> shows only when that clip's meta says speed > 1
    els('[data-speed]').forEach(function (n) {
      var m = metas[n.getAttribute('data-speed')];
      var sp = m && m.frames > 0 ? m.speed : 1;
      if (sp > 1) { var x = n.querySelector('[data-x]'); if (x) x.textContent = (Math.round(sp * 10) / 10) + '×'; }
      else n.style.display = 'none';
    });
    readyP = document.fonts.load('800 40px Archivo').then(function () { return document.fonts.ready; }).then(function () {
      if (cfg.build) cfg.build(HM);
    });
    return readyP;
  };

  window.seek = async function (t) {
    await readyP;
    t = Math.max(0, Math.min(S.duration, +t || 0));
    var ms = t * 1000;
    document.getAnimations().forEach(function (a) { a.pause(); a.currentTime = ms; });
    for (var i = 0; i < hooks.length; i++) hooks[i](t);
    seekCap(t);
    await seekClips(t);
    // Drop and rebuild the render layers, so a frame's pixels never depend on which frames were drawn before it
    // (Chromium otherwise reuses a layer rastered at an earlier scale, which shifts a few anti-aliased pixels).
    var st = document.querySelector('.stage');
    st.style.display = 'none'; void st.offsetHeight; st.style.display = ''; void st.offsetHeight;
    return t;
  };
})();
