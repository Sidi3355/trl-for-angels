# Halomark demo video: design brief for the motion scenes

You are designing the animated scenes for a 2-minute demo video of **Halomark**, a calibrated founder-screening
app for angel investors (hackathon demo; the audience is judges and angel investors). The owner asked for
"voiceover, good animations, branding and a walkthrough of the app, and a tiny bit of the research", and has asked
before that nothing look AI-generated. Another session records the app footage and assembles the video; you design
and build the scenes.

Work only inside `app/media/17-demo-video/` (this folder). Don't change anything else in the repo, don't commit,
don't push.

## Format

- 1920×1080, 30 fps, landscape. Eight scenes, one per voiceover section, played back to back (about 1:53 in all).
- The voiceover is already recorded: `voiceover/<id>.mp3`, with exact per-character timings in
  `voiceover/<id>.alignment.json` (`characters`, `character_start_times_seconds`, `character_end_times_seconds`) and
  lengths in `voiceover/durations.json`. The text is in `script.json`. Don't change the script.
- Each scene starts its voice at `voice_at` seconds (you choose, e.g. 0.5) and lasts `voice_at + voice + tail`
  (tail about 0.5 s; longer for the last scene so the end card can breathe).

## The brand (match the app; see `brand/` and the screenshots listed below)

- Name: **Halomark**. A halo (for angels) struck into a hallmark punch (the cut-corner stamp an assay office strikes
  into tested gold). The wordmark is HAL◯MARK in Archivo at its widest width, weight 800, capitals, with the halo as
  the O, in the text colour. The boxed mark (punch + halo) is the app icon, in stamp-pad blue. SVG paths and colours:
  `brand/mark.ts.txt` (`MARK_PUNCH`, `MARK_HALO`, `HALO_VIEWBOX`, `BRAND_*`), `brand/app-icon.svg`.
- Type: Archivo (variable: weight and width axes), `brand/Archivo-latin-variable.woff2`. The app uses condensed
  Archivo black for big figures, normal width for text, wide for labels/eyebrows.
- Colours: `brand/tokens-light.css.txt` (paper `#eeeeea`, ink `#0e0f0e`, stamp-pad blue `#1f3bd0`, and the verdict
  colours: green Meet, amber Look closer, ink Pass). Reference board: `brand/brand-board-reference.png`.
- Look of the app: `../15-more-colour/*.png` and `../16-real-kev/*.png` (phone and desktop, light and dark).
- Direction: editorial and print-like ("the odds slip"): ink on paper, hard edges, stamps, tear lines, condensed
  figures, generous whitespace, confident type. Motion should feel like printing and stamping: things set,
  slide, strike, count up. **Avoid** anything that reads as generic AI video: no glowing gradients, blobs, particle
  fields, neon, glassmorphism, robot or brain imagery, sparkles, or "AI" wording on screen.

## The scenes (voice text in `script.json`; durations from `voiceover/durations.json`)

1. `s1_hook` (11.7 s of voice): the problem, then the brand. Angels screen alone: a stack of names and a gut
   feeling. End on the Halomark wordmark/mark being struck, with the line "A first pass you can trust."
2. `s2_start` (8.7 s): app footage `c1_type` in a phone: the dashboard, typing a founder's name (Tope Awotona,
   Calendly) and starting the screening. A small label that this is the real app.
3. `s3_research` (18.4 s): app footage `c2_research` (the live research screen, sped up: show a small "sped up"
   badge with the factor from the manifest) then `c3_profile` (the anonymised profile the model reads). Key ideas
   on screen, not the voice word for word: "Only what was public before founding", "Every fact sourced",
   "Names removed".
4. `s4_verdict` (16.4 s): app footage `c4_verdict` (the verdict slab counting up) then `c5_bar` (changing the bar:
   target, timeline, risk; the verdict updates). Call out "Meet · Look closer · Pass" and "your bar".
5. `s5_drivers` (6.5 s): app footage `c6_whatif` (what moves the score; tapping one flips the verdict).
6. `s6_research` (25.4 s): the research, as motion graphics (no app footage). TRL (Think, Reason, Learn; Vela
   Research's open-source library):
   - **Think:** Claude Opus 5.5 wrote 93 yes/no questions about founders; the best 40 were kept.
   - **Reason:** Kev-0.6B (a small open decision model) answers the 40 questions for each founder.
   - **Learn:** a fine-tuned Kev-0.6B turns the 40 answers into the chance of each outcome.
   - **Calibration:** on 600 test founders it never saw, the odds were off by about 1 percentage point on average
     (calibration error 0.012). Reliability bins (predicted → actual share who succeeded, founders per bin):
     0–10%: 7.2% → 9.1% (99); 10–20%: 15.0% → 16.5% (218); 20–30%: 25.2% → 24.8% (238); 30–40%: 33.2% → 35.6% (45).
     Draw the chart honestly: these four points near the diagonal; nothing above 40% (the model is cautious).
   - A small honest footnote on screen: "Trained and tested mostly on generated founder data (2,950 of 3,000
     profiles). No real-world accuracy claimed."
7. `s7_extras` (10.1 s): app footage `c7_list` (screening a list), `c8_voice` (voice note), `c9_notify`
   (notification), `c10_profile` (the on-device profile). A quick, tidy montage; labels like "Screen a list",
   "Voice notes", "Notified when it's done", "Your profile stays on your phone".
8. `s8_close` (5.7 s of voice; hold the card about 2 s more): end card. The mark, the wordmark, "Calibrated odds for
   angels", small: "Screening aid, not investment advice." and "Built with TRL (Vela Research), Kev, Claude and
   ElevenLabs."

Subtitles: show the voiceover as captions (a line or two at a time, in sync from the alignment files), styled to
the brand, in a consistent place that never covers the phone's content.

## App footage (the contract)

- Phone clips are JPEG sequences at 30 fps, 804×1748 pixels (the phone screen at 2×, full screen, no browser
  chrome): `clips/<name>/000001.jpg`, `000002.jpg`, … and `clips/<name>/meta.json` = `{"frames": N, "fps": 30,
  "speed": 1}` (`speed` > 1 for a sped-up clip; show the badge then). They're being recorded now, so they may not
  exist yet. Until they do, use a still placeholder: copy a relevant screenshot from `../16-real-kev/` or
  `../15-more-colour/` (phone, light) to `clips/<name>/placeholder.png` and fall back to it.
- Put each clip in a phone shape you design (a simple, non-branded device or a rounded screen with a shadow; don't
  imitate a specific manufacturer's hardware). Scale it to fit comfortably in 1080 px of height. If a clip is shorter
  than its slot, hold its last frame; if longer, the scene's own duration wins (the assembler trims).
- Plan the clip slots in each scene in the manifest (which clip, from which second to which second of the scene).

## Rendering contract (important: the video is rendered frame by frame)

- Each scene is a standalone HTML page, `scenes/<id>.html`, 1920×1080, with shared `scenes/shared.css` and
  `scenes/seek.js`. Load the font with `@font-face` from `../brand/Archivo-latin-variable.woff2`. No network
  requests (no CDNs, no Google Fonts).
- All motion must be **deterministic and seekable**: CSS animations or the Web Animations API only, created at load,
  then paused. No `setTimeout`/`setInterval`/`requestAnimationFrame`-driven state, no `Date.now()`, no random
  numbers unless seeded.
- Each page defines `window.SCENE = {id, duration}` and `async window.seek(t)` (t in seconds from the scene's start)
  that: sets `currentTime = t*1000` on every animation in `document.getAnimations()`; sets each clip `<img>` to the
  right frame (`clips/<name>/<index>.jpg`, from the slot's start and the clip's fps; holds the last frame; the
  placeholder if there are no frames) and awaits `img.decode()`; updates the subtitles for t; and resolves when the
  frame is ready. The renderer opens each page, calls `await seek(t)` for t = 0, 1/30, 2/30, … and screenshots.
- `scenes/manifest.json`: `[{ "id", "file", "duration", "voice": {"file": "../voiceover/<id>.mp3", "at": <s>},
  "clips": [{"name", "from": <s>, "to": <s>}] }]` in order.
- Check your own work: render previews with Playwright (Chromium is installed; `require('playwright')` works; open
  the pages with `file://`) at a few times per scene into `scenes/previews/<id>-<t>.png` (1× is fine), look at them,
  and fix what looks wrong: overlaps, text running off the frame, unreadable contrast, empty frames. Make sure every
  scene seeks correctly to any t (seek backwards too).

When done, write `scenes/README.md`: the design idea in a few lines, the scene list with durations, and anything the
assembler should know. Report back briefly with the same.
