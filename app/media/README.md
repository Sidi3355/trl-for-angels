# App media: every screenshot and video, in order

Every image and video made while building the app, including the rejected and superseded ones, kept so
the design history can be followed and nothing has to be re-shot. The folders are numbered in the order
the work happened (all on 2026-11-14, times in UTC). The owner's rule: **every image and video goes here**,
good or bad.

**Status words used below**

| Status | Meaning |
|---|---|
| Current | What the app looks like now |
| Rejected | The owner saw it and asked for something different (their words are quoted) |
| Superseded | Replaced before the owner saw it, or replaced by a later fix |
| Check | Internal verification shots, never meant as a deliverable |

Files marked **sent** were the ones shown to the owner at the time.

**Naming.** Walk-through screenshots are `<device>-<theme>-<step>-<screen>.png`. Device is `phone` (an
emulated iPhone 17, 402px wide, shot at 3×) or `desktop` (1440px wide). Theme is `light` or `dark`.
The step numbers follow one walk through the app: 1 empty list, 2 progress, 3 memo, 4 full memo, 5 what-if,
5b what-if factors, 6 list, 7 "Your bar" sheet, 8 list at a $1B bar, 9 new screening, 10 about.
The list screen is called "deals" in file names even after the screen itself was renamed "Founders",
because the screenshot script kept its old names.

## 01-prototype (13:19–13:27) · Rejected

The first working prototype (task 4): blue accent, a long form, a stacked memo, the passcode gate.
Owner: "it looks and feels shit as a user, and its so complicated."

- `light-*` and `dark-*`, numbered 1–7: home, progress, memo top, full memo, controls, what-if, home after a screening
- `memo-part1–4.png`: the memo in four slices
- `sheet-light.png`, `sheet-dark.png`: the controls sheet
- `form-filled.png`, `typed-memo.png`: a screening typed in by hand, and its memo
- `gate-1.png`, `sheet-gate-typed.png`: the passcode gate (the passcode was later dropped)
- **Sent:** `light-1-home`, `light-2-progress`, `light-3-memo-top`, `light-memo-controls-drivers`, `dark-6-whatif`

## 02-redesign-1 (14:38–14:41) · Rejected

The first redesign: Inter and Space Grotesk, cool neutrals, an ink-blue accent, the list called "Deals",
"Your bar" as one global sheet. Owner: "this still looks really AI generated. make it look cool."

- the full walk-through: phone and desktop, light and dark, steps 1–10 (40 files)
- `s-dark.png`, `s-new-about.png`: side-by-side overviews
- `chk-examples.png`: a check of the example-founder buttons
- **Sent:** `phone-light-6-deals`, `phone-light-3-memo`, `phone-light-7-bar-sheet`, `phone-dark-5-whatif`, `desktop-light-3-memo`

## 03-deals-renamed-to-founders (14:45) · Superseded

The same design with "Deals" renamed "Founders", after the owner asked "whys it called deals" and said the
app is for angels, not VCs.

- `founders-home.png`
- `founders-memo.png`
- `founders-sheet.png`

## 04-redesign-2-fable (14:57–15:05) · Current design

The second redesign, by a Claude Fable 5.2 design agent: "the odds slip". Black ink on paper, colour only
on the verdict slab, Archivo at three widths, and a floating dock on phones.

- `iteration-1/`, `iteration-2/`: the agent's own verification runs while it worked
- `final/`: the finished walk-through, phone and desktop, light and dark
- `review/`: overviews made while reviewing the agent's work
- **Sent:** `final/phone-light-6-deals`, `final/phone-light-7-bar-sheet`, `final/desktop-light-5-whatif`, `final/desktop-dark-6-deals`

These still show the old verdict words (Advance / Escalate / Pass) and the old name, Screener.

## 05-checks-labels-gauge (15:05–15:16) · Check

Checks after the redesign and after the owner chose the verdict words **Meet / Look closer / Pass** (15:13).

- `light-` and `dark-memo-advance` / `-escalate` / `-pass.png`: one memo per verdict, in both themes.
  - These were re-shot after the label change, so they show Meet / Look closer / Pass.
  - The 15:11 versions that were **sent** (an Advance memo in light, a Pass memo in dark) were overwritten. They survive only in `04-redesign-2-fable/review/memos-advance-pass-light-dark.png`.
- `light-notfound.png`, `dark-notfound.png`, `gate.png`: the not-found page and the passcode gate
- `phone-list.png`, `desktop-list.png`: the Founders list with the new labels
- `phone-zone.png`, `desktop-zone.png`, `gauge-zones-overview.png`: the gauge with its Pass / Look closer / Meet zones and the solid needle
  - The earlier hollow marker read as a "0".
- `meet-look-closer-labels-overview.png`: the new labels across screens

## 06-phone-features-and-lists (15:34–15:35) · Current

Steps 2–4: notifications, sharing into the app, screening a list, and the scrolling fixes.

- `share.png`: a LinkedIn link shared into the app
- `notify-on.png`: notifications switched on for a running screening
- `notify-hint.png`: the iPhone "Add to Home Screen first" hint
- `batch-upload.png`, `batch-running.png`, `batch-done.png`, `batch-error.png`, `batch-desktop.png`: screening a list
  - `batch-error.png` shows the error for a bad CSV, with the rows at fault
- `founders-after-batch.png`: the screened list's founders joining the Founders list
- `memo-scrolled.png`: the what-if bar appearing once the verdict scrolls away
- `about.png`: How it works, with the iPhone Shortcut steps
- `overview-share-notify-list.png`
- **Sent:** `overview-share-notify-list.png`, `batch-desktop.png`

## 07-walkthrough-video (15:37–16:40)

A 40-second phone walk-through: screening a founder, the what-if factors, changing your bar, and
screening a list. Example data. v1–v3 carry the old name, Screener; v4 is Halomark.

| Version | Status | What's wrong or right |
|---|---|---|
| `v1-rejected-padded/` | Rejected, **sent** | Playwright's recorder filmed the page at half the video's size and filled the rest with grey. The phone height was also the in-browser view (402×681). Owner: "not the full size of the video". |
| `v2-superseded-low-res/` | Superseded | Full frame at full screen height (402×874), but only 1× resolution, so soft on a phone. Never sent. |
| `v3-full-frame-2x/` | Superseded, **sent** | Full frame, full screen and 2× sharp (804×1748), 42s. Replaced only because of the rename. |
| `v4-halomark/` | Current, **sent** | The same walk-through, re-recorded the same way after the Halomark rebrand. |

Contents of each version folder:
- `v1-rejected-padded/`:
  - the video
  - the raw `.webm` it came from
  - stills at 3, 12, 30 and 39 seconds
  - the raw frame at 12s that shows the grey padding
- `v2-superseded-low-res/`: the video and a strip of stills
- `v3-full-frame-2x/`:
  - the video and a strip of stills
  - one full-size frame at 9s
  - `capture-test-2x.jpg`, the test frame that showed the 2× capture works
- `v4-halomark/`: the video, a strip of stills and one full-size frame at 1s

## 08-halomark-brand (16:30–16:40) · Current for the app icon; the in-app wordmark changed in 09

The product was renamed **Halomark**: a halo for angels, and close to *hallmark*, the stamp that certifies tested gold.
A Claude Fable 5.2 design agent made the identity.
- **The mark:** a cut-corner hallmark punch with a halo struck into it, which also stands in for the O in HAL◯MARK.
- **Colour:** stamp-pad blue, used for the mark and app icon only.

- `brand-board.png`: the whole identity on one page
  - the mark
  - the name in light and dark
  - the icon from 180px down to 16px
  - the icon on a mock Home Screen
  - colours and type
- `directions.png`: the three rejected directions and the chosen one
  - an HM maker's mark: reads as a clothing brand, mush at 16px
  - a halo as the H's crossbar: the obvious idea, looks like a planet
  - a halo alone: elegant, but says nothing about stamping
- `sketches/`: the agent's working renders of each direction, plus a crop of the About page
- `phone-<screen>-<theme>.png`: home (with a screening, and empty), memo, about, new, batch and share, in light and dark
  - `phone-about-name-*.png` shows the new "The name" section. Its wording was tightened afterwards, so the live text differs slightly.
- `desktop-home-light.png`, `desktop-home-dark.png`
- **Sent:** `brand-board.png`, `directions.png`, `phone-home-light.png`, `phone-memo-dark.png`, `phone-about-name-light.png`

## 09-wordmark-plain-halo (16:45–16:50) · Current

The owner's change: the app icon keeps the halo in its blue octagonal punch, but inside the app the O of
HALOMARK is the halo alone, in the same colour as the letters.
- `phone-header-*.png`, `desktop-sidebar-*.png`: the wordmark at its real sizes (17px on phones, 21px on desktop), light and dark
- `phone-home-*.png`, `desktop-home-*.png`: the whole home screen with it
- `phone-not-found-*.png`: the not-found page, which now shows the halo instead of the boxed mark
- `wordmark-large-vs-real-O.png`: the wordmark at 120px above Archivo's own O, used to match the halo's height and overshoot to a real letter
  - The first shots had the halo sitting on the baseline, overshooting only at the top. They were overwritten by the re-shoot after the fix.
- `link-preview-image.png`: the link-preview image, regenerated with the same wordmark
- **Sent:** `phone-header-light.png`, `desktop-sidebar-dark.png`, `phone-home-dark.png`, `wordmark-large-vs-real-O.png`

The walk-through video (07, v4) and the brand board (08) still show the earlier boxed O in the header.


- `record-walkthrough.cjs`: the script that recorded v3 and v4, with the ffmpeg command in its header, so the video can be re-shot after design changes
- `walkthrough-batch.csv`: the three example founders it pastes into "Screen a list"

## Not included

- **Raw video frames.** The screen recorder saves one image per screen change, about 3,000 JPEGs for v2, v3 and v4. Each one is already inside its video.
- **Anything before 13:00.** Tasks 1–3 (the API contract, the backend and the research agent) produced no images.
