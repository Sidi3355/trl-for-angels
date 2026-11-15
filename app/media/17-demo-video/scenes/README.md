# Halomark demo video: the motion scenes

## The design idea

"The odds slip." The video is laid out like a printed sheet: ink on paper, one family (Archivo: wide capitals for
labels, normal width for headlines, the narrowest black for figures), hard rules, a running head with a folio, and
the hallmark punch's cut corners on every tag and verdict. Nothing fades in softly. Type is *set* (drops into
place), marks are *struck* (come down like a stamp, and the page takes the blow), panels are *wiped* edge to edge
like a sheet pulled from a press, and figures count up. The research scene turns the sheet over: paper on ink, with
the brand's on-dark blue. The app plays in one plain black phone slab with a hard offset shadow, in the same place
in every app scene, so the cuts between scenes only change the left-hand column.

## Scenes

1920×1080, 30 fps. Voice starts 0.5 s into every scene. Total 113.3 s (1:53).

| # | id | Duration | What's on screen | Clip slots (name, from → to, in scene seconds) |
|---|---|---|---|---|
| 1 | `s1_hook` | 12.7 s | "Angels screen alone.", analyst and second opinion: none, a stack of name cards, a "gut feeling" stamp; then a clean sheet, the mark struck, the wordmark set, "A first pass you can trust." | none |
| 2 | `s2_start` | 9.8 s | The phone comes up. "Type a name.", "The real app" tag, a slip: Tope Awotona / Calendly / the day he founded it | `c1_type` 0.4 → 9.8 |
| 3 | `s3_research` | 19.4 s | Three numbered ideas: only what was public before founding; every fact sourced; names removed. "Sped up N×" tag, then "What the model reads" | `c2_research` 0 → 13.1; `c3_profile` 13.1 → 19.4 |
| 4 | `s4_verdict` | 17.4 s | Meet · Look closer · Pass, each struck with its punch; then "Your bar." with target, timeline, risk | `c4_verdict` 0.3 → 8.6; `c5_bar` 8.6 → 17.4 |
| 5 | `s5_drivers` | 7.6 s | "What moves the score." and one answer flipping Yes → No, Meet → Look closer | `c6_whatif` 0.3 → 7.6 |
| 6 | `s6_research` | 26.5 s | Dark. TRL; Think (93 slips, 40 kept), Reason (40 yes/no answers), Learn (chance of each outcome); then 600 test founders, the reliability chart and table, "off by about 1 percentage point", the footnote | none |
| 7 | `s7_extras` | 11.1 s | Four numbered features; the highlight follows the phone | `c7_list` 0 → 2.6; `c8_voice` 2.6 → 5.65; `c9_notify` 5.65 → 8.2; `c10_profile` 8.2 → 11.1 |
| 8 | `s8_close` | 8.8 s | End card: mark, wordmark, "Calibrated odds for angels.", the two small lines. Voice ends at 6.25 s; the card holds 2.5 s more | none |

`manifest.json` holds the same (ids, files, durations, voice file and start, clip slots), and each page repeats its
own values in `window.SCENE` (`id`, `duration`, `voiceAt`, `clips`).

## For the assembler

- **Rerun `node scenes/build-data.js` after the clips are recorded** (and after any voiceover change). Pages are
  opened with `file://`, where a page can't read local JSON, so the caption timings and every clip's `meta.json`
  (`frames`, `fps`, `speed`) are baked into `scenes/data.js`. Until it is rerun the pages don't know the clips exist
  and keep showing the stills. The script counts the frames actually on disk if `meta.json` claims more.
- **Placeholders.** `clips/<name>/placeholder.png` are screenshots from `../15-more-colour/` and `../16-real-kev/`
  (804×1362, so they don't fill the 804×1748 screen). While a phone shows one, a grey band at the bottom of its
  screen says "Placeholder still · <clip>". If that band is in a rendered frame, the clip wasn't picked up. A
  missing single frame also falls back to the still.
- **Clip timing.** Frame = `floor((t - from) × fps) + 1`, clamped to 1…frames: the first frame is held before the
  slot starts and the last one after the clip runs out. In `s3`, `s4` and `s7` the next clip wipes up over the
  previous one at its `from` (0.35–0.45 s), so the first few frames of `c3_profile`, `c5_bar`, `c8_voice`,
  `c9_notify` and `c10_profile` are partly covered.
- **The "sped up" tag** (scene 3) shows only when `c2_research`'s `meta.json` has `speed` > 1, and prints that
  factor (e.g. "Sped up 6×"). It leaves at 12.7 s, before `c3_profile` comes in.
- **The phone's screen** is 408×887 px on the 1080p frame (the 804×1748 clip at about half size), at left 1308,
  top 147.5. The phone slides up in scene 2 and is already in place at t = 0 in scenes 3, 4, 5 and 7, so those cut
  cleanly from one to the next.
- **Subtitles are drawn by the pages**, so don't add another subtitle track. They sit bottom left (left 96 px,
  bottom 58 px, at most 1040 px wide, one or two lines), never under the phone. Each cue is a sentence or clause
  from the alignment file; words turn from grey to ink as they are spoken. They follow the voice at `voiceAt`
  (0.5 s), so if the voice is moved, change `voiceAt` in the page and `voice.at` in the manifest together.
- **Files a page loads** (all local, no network): `shared.css`, `data.js`, `seek.js`,
  `../brand/Archivo-latin-variable.woff2`, and `../clips/<name>/<frame>.jpg` or `placeholder.png`. The mark and the
  verdict punches are inline SVG built from the paths in `brand/mark.ts.txt`.
- **Seeking.** `await window.seek(t)` waits for the font, sets every animation's `currentTime`, runs the counters,
  sets the captions, decodes the clip images, and resolves. All motion is Web Animations created at load and paused;
  there are no timers, no clock, and the only random numbers are seeded. `seek` also rebuilds the render layers on
  every call, so a frame's pixels don't depend on which frames were drawn before it (checked: seeking backwards
  gives byte-identical screenshots). `t` is clamped to 0…duration.
- **Previews.** `node scenes/preview.js [sceneId …] [--t 1,2.5] [--every 2]` writes `scenes/previews/<id>-<t>.png`,
  checks backwards seeking, and fails on any page error or non-local request.

## What the numbers are

Only the figures in `BRIEF.md`: 93 questions written and 40 kept; 600 test founders; calibration error 0.012,
"off by about 1 percentage point, on average"; the four reliability bins (7.2% → 9.1%, 99; 15.0% → 16.5%, 218;
25.2% → 24.8%, 238; 33.2% → 35.6%, 45) drawn on 0–50% axes at the same scale, with the band above 40% hatched
("No odds above 40%: the model is cautious"); and the footnote about generated data.

Two things on screen are illustrations, not results: the five bars under "Learn" (labelled "Illustration", no
figures) and which of the 93 slips and 40 answers light up (a seeded pattern). The name cards in scene 1 use the
app's own example founders (Jordan Pike, Samir Haddad, Ada Moreno) and Tope Awotona.
