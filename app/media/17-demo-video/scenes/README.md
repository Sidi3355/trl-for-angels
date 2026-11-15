# Halomark demo video: the motion scenes

## The design idea

"The odds slip." The video is laid out like a printed sheet: ink on paper, one family (Archivo: wide capitals for
labels, normal width for headlines, the narrowest black for figures), hard rules, a running head with a folio, and
the hallmark punch's cut corners on every tag and verdict. Nothing fades in softly. Type is *set* (drops into
place), marks are *struck* (come down like a stamp, and the page takes the blow), panels are *wiped* edge to edge
like a sheet pulled from a press, and figures count up. The research scene turns the sheet over: paper on ink, with
the brand's on-dark blue. The app plays in one plain black phone slab with a hard offset shadow, in the same place
in every app scene, so the cuts between scenes only change the left-hand column.

## Scenes (version 2)

1920×1080, 30 fps. Total 108.6 s (1:49). Version 1's pages are not kept here; this is the cut for the new voice
(George) and the real-speed clips.

| # | id | Duration | Voice at | What's on screen | Clip slots (name, from → to in scene seconds) |
|---|---|---|---|---|---|
| 1 | `s1_hook` | 12.9 s | 0.5 | "Angels screen alone.", analyst and second opinion: none, a stack of name cards, a "gut feeling" stamp; a clean sheet, the mark struck, the wordmark set, "A first pass you can trust."; then the lockup leaves and the running head is set | none |
| 2 | `s2_start` | 9.0 s | 0.6 | The phone comes up. "Type a name.", "The real app" tag, a slip: Tope Awotona / Calendly / the day he founded it | `c1_type` 0.5 → 9.0 |
| 3 | `s3_research` | 17.2 s | 0.5 | Three numbered ideas: only what was public before founding; every fact sourced; names removed | carry `c1_type` → 0.35; `c2_research` 0.35 → 8.9 (starts 1.6 s into the clip); `c3_profile` 8.9 → 17.2 |
| 4 | `s4_verdict` | 14.9 s | 0.5 | Meet · Look closer · Pass, each struck with its punch; then "Your bar." with target, timeline, risk | carry `c3_profile` → 0.35; `c4_verdict` 0.35 → 7.2; `c5_bar` 7.2 → 14.9 |
| 5 | `s5_drivers` | 7.8 s | 0.5 | "What moves the score." and one answer flipping Yes → No, Meet → Look closer; a sheet of ink comes up | carry `c5_bar` → 0.35; `c6_whatif` 0.35 → 7.8 (starts 0.9 s into the clip) |
| 6 | `s6_research` | 25.6 s | 0.6 | Opens on ink. TRL; Think (93 slips, 40 kept), Reason (40 yes/no answers), Learn (chance of each outcome); 600 test founders, the reliability chart and table, "off by about 1 percentage point", the footnote; a sheet of paper comes up | none |
| 7 | `s7_extras` | 12.7 s | 0.7 | Opens on paper; the head is set and the phone comes back up. Four numbered features, the highlight follows the phone; then everything leaves | `c7_list` 1.9 → 4.2; `c8_voice` 4.2 → 7.4; `c9_notify` 7.4 → 9.6; `c10_profile` 9.6 → 12.7 |
| 8 | `s8_close` | 8.5 s | 0.5 | End card: mark, wordmark, "Calibrated odds for angels.", the two small lines. Voice ends at 6.1 s, the card holds, then a sheet of ink closes over it from 7.6 to 8.4 s | none |

`manifest.json` holds the same, and each page repeats its own values in `window.SCENE`. In a clip slot, `offset`
is how many seconds into the clip the slot starts, and `carry: true` marks the clip the previous scene ended on
(with a negative `from`, so it simply keeps playing or holding until the scene's own first clip wipes over it).

### Zooms

The phone pushes in to 1.9× on a detail and pulls back (0.8 s in, 0.7 s out; in `s7` 0.7 and 0.55). Times are when
the move in starts and when the move out starts.

| Scene | In at | Out at | What |
|---|---|---|---|
| `s3_research` | 6.5 s | 8.1 s | "What the agent found": 8 sources, 9 facts, and the list of what it found ("Every fact comes with its source") |
| `s3_research` | 12.3 s | 15.6 s | The anonymised profile under "What the model read" ("it strips out every name") |
| `s4_verdict` | 3.6 s | 6.3 s | The verdict slab: Meet, 31%, "All founders: 20%" |
| `s5_drivers` | 5.05 s | 6.5 s | The what-if verdict: Look closer, 25%, "was 31%" |
| `s7_extras` | 5.7 s | 6.85 s | The voice note: "Added to your notes. Filled in: Technical · 10–15 years …" |

### Joins

The last frame of each scene is the first frame of the next, pixel for pixel (`node scenes/check.js` renders both
and counts the pixels that differ: 0 at every join; side-by-sides are in `previews/join-*.png`).

- `s1 → s2`: the lockup wipes away and the running head is set; `s2` opens on that head and the phone comes up.
- `s2 → s3 → s4 → s5`: the left column and the folio leave before the cut; the head and the phone stay where they
  are, and the phone keeps showing the clip the scene ended on until the next scene's first clip wipes up over it.
- `s5 → s6` (paper to ink): a sheet of ink wipes up over `s5`; `s6` opens on plain ink and sets its head.
- `s6 → s7` (ink to paper): a sheet of paper wipes up; `s7` opens on plain paper, sets its head, and the phone
  comes back up.
- `s7 → s8`: the list and head wipe away and the phone drops out; `s8` opens on plain paper and strikes the mark.
- The end: a sheet of ink closes over the end card from 7.6 to 8.4 s and the last frames are plain ink. Fade the
  audio (and any music) out over the same 0.8 s.

**Play the scenes back to back with hard cuts and no crossfades.** The transitions are inside the pages; a
dissolve added in the edit would double them.

## For the assembler

- **Rerun `node scenes/build-data.js` after the clips are recorded** (and after any voiceover change). Pages are
  opened with `file://`, where a page can't read local JSON, so the caption timings and every clip's `meta.json`
  (`frames`, `fps`, `speed`) are baked into `scenes/data.js`. Until it is rerun the pages don't know the clips exist
  and keep showing the stills. The script counts the frames actually on disk if `meta.json` claims more.
- **Placeholders.** If a clip has no frames, the phone falls back to `clips/<name>/placeholder.png` and shows a grey
  band reading "Placeholder still · <clip>". `check.js` fails if any frame shows one. All ten clips have frames now.
- **Clip timing.** Frame = `floor((t − from + offset) × fps) + 1`, clamped to 1…frames, so a clip that runs out holds
  its last frame (`c4_verdict` holds from 4.55 s in `s4`; `c7_list` plays from 1.9 s in `s7` and shows its first
  frame while the phone comes up). Each clip after the first wipes up over the one before it during the 0.4 s after
  its `from`. Clips cut short by their slot: `c2_research` (shown from 1.6 s to 10.15 s of 11.1), `c3_profile` (8.3
  of 9.87 s, then 0.35 s more at the top of `s4`), `c6_whatif` (0.9 s to 8.35 s of 9.67), `c9_notify` (2.2 of 2.57 s).
- **No "sped up" badge** any more; `speed` in `meta.json` is ignored.
- **The phone** is 466×1038 px at left 1322, top 21 (about 10% larger than version 1). Its screen is 446×1018: a
  48 px status bar (9:41, a Dynamic Island pill, signal, Wi-Fi, battery, drawn in the page) and the footage below it
  at 446×970. It comes up in `s2`, stays through `s5`, and comes up again in `s7`.
- **Subtitles are drawn by the pages**, so don't add another subtitle track. They sit bottom left (left 96 px,
  bottom 58 px, at most 850 px wide, one or two lines), never under the phone. Each cue is a sentence or clause
  from the alignment file; words turn from grey to ink as they are spoken. They follow the voice at `voiceAt`, and leave
  0.4 s after the last word, before the scene's content does. If the voice is moved, change `voiceAt` in the page and `voice.at` in the manifest together.
- **Files a page loads** (all local, no network): `shared.css`, `data.js`, `seek.js`,
  `../brand/Archivo-latin-variable.woff2`, and `../clips/<name>/<frame>.jpg` or `placeholder.png`. The mark and the
  verdict punches are inline SVG built from the paths in `brand/mark.ts.txt`.
- **Seeking.** `await window.seek(t)` waits for the font, sets every animation's `currentTime`, runs the counters,
  sets the captions, picks and decodes the clip frames, and resolves. Motion is Web Animations created at load and
  paused; three things are set directly in `seek` as pure functions of `t` (figures counting up, caption words,
  and the wipe between clips inside the phone). There are no timers and no clock, and the only random numbers are
  seeded. `seek` rebuilds the render layers on every call, so a frame never depends on which frames were drawn
  before it. `t` is clamped to 0…duration; render `t = 0, 1/30, … , duration − 1/30`.
- **Checks.** `node scenes/check.js` seeks every frame of every scene, compares each page with the manifest, fails
  on a caption over two lines, a placeholder, a page error or a non-local request, and checks every join.
  `node scenes/preview.js [sceneId …] [--t 1,2.5] [--every 2]` writes `scenes/previews/<id>-<t>.png` and checks
  that seeking backwards gives the same pixels.

## What the numbers are

Only the figures in `BRIEF.md`: 93 questions written and 40 kept; 600 test founders; calibration error 0.012,
"off by about 1 percentage point, on average"; the four reliability bins (7.2% → 9.1%, 99; 15.0% → 16.5%, 218;
25.2% → 24.8%, 238; 33.2% → 35.6%, 45) drawn on 0–50% axes at the same scale, with the band above 40% hatched
("No odds above 40%: the model is cautious"); and the footnote about generated data.

Two things on screen are illustrations, not results: the five bars under "Learn" (labelled "Illustration", no
figures) and which of the 93 slips and 40 answers light up (a seeded pattern). The name cards in scene 1 use the
app's own example founders (Jordan Pike, Samir Haddad, Ada Moreno) and Tope Awotona.
