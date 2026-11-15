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


## 10-halomark-screens (16:53) · Current

A tour of the app as it is now: Halomark, with the halo O, on example data. Each screen is shown in light
and dark, as `<device>-<theme>-<n>-<screen>.png`.
- phone:
  1. a memo
  2. the factors that move the score
  3. the Founders list
  4. the Your bar sheet
  5. a screened list
  6. About, at "The name"
- desktop:
  1. a memo
  2. the Founders list
- **Sent:** `phone-light-1-memo`, `phone-dark-3-founders`, `phone-light-5-list-screened`, `phone-dark-6-about-the-name`, `desktop-light-1-memo`, `desktop-dark-2-founders`

## 11-voice-notes (17:44–17:47) · Current

Voice notes (step E5): record a note, ElevenLabs transcribes it, and the facts fill the form for you to check. Typed
notes get a "Fill the form from my notes" link. Shot in a real browser with a fake microphone, against the mock
transcriber and the keyword stand-in sorter, so the words are the example transcript, not real speech.

1. `phone-1-notes-with-record.png`: the notes box with its Record button
2. `phone-2-recording.png`: recording, with the timer and Stop
3. `phone-3-voice-filled.png`: the transcript in the notes and what was filled
   - the example-transcript notice
   - the post-founding fact kept out ("forty design partners")
4. `phone-4-voice-fields-tagged.png`: the filled fields, each tagged "From your voice note"
5. `phone-5-memo-you-voice.png`: the memo's profile after screening, with those fields marked "You (voice)"
6. `phone-6-typed-filled.png`: typed notes filled through the link, tagged "From your notes"
7. `phone-7-kept-your-answer.png`: a hand-picked "2 co-founders" kept over the note's "solo founder"
8. `phone-8-sorting-off-on-server.png`: a server without the Claude key; the transcript still lands in the notes
- `desktop-dark-voice-filled.png`: the voice result on desktop, dark mode
- `first-try-notes-covered/`: the first run of the same shots. **Bad:** on phones the sticky Screen button and the dock covered the notes box and its result. Fixed by reserving scroll space for them and bringing the result into view.
- **Sent:** `phone-3-voice-filled.png`, `phone-4-voice-fields-tagged.png`, `phone-5-memo-you-voice.png`, `phone-6-typed-filled.png`, `phone-7-kept-your-answer.png`

## 12-new-screens (19:20–19:46) · Current

The owner's six new screens, on example data, at 2× (the new screenshot rule). Phones are an emulated iPhone 17;
desktops are 1440px. Named `<device>-<theme>-<n>-<screen>.png`.
- `phone-light-01…03`: the first-run intro
  1. what Halomark does
  2. what a percentage means
  3. try a sample founder
- `phone-light-04-sign-in`, `phone-light-05-profile` (full page), `phone-dark-05-profile`: the on-device profile
- `phone-light-06-delete-confirm`: the "delete all my data" confirmation
- `phone-*-07-how-it-works`, `phone-*-08-model-card`: How it works and the model card, light and dark
- `phone-*-09-calibration`, `phone-*-09b-calibration-tooltip`: the calibration page, and a dot's tooltip
- `phone-*-10-terms`, `phone-*-11-privacy`: the legal drafts
- `phone-*-12-plans`, `phone-light-12b-plans-yearly`: the plans mockup, monthly and yearly
- `phone-light-13-dock-you`: the dock's new You tab
- `phone-dark-02-intro-2-odds`: the intro in dark
- `desktop-light-01-intro`, plus `desktop-{light,dark}-{calibration,plans,how-it-works,sign-in,model-card}`: desktop, both themes
- `first-try-chart-labels-overlap/`: **bad**. The first calibration shots: the x-axis title ran into "Founders in each band", and the y-axis title touched the tick labels. Fixed by spacing the chart's margins.
- **Sent:** `phone-light-02-intro-2-odds`, `phone-light-05-profile`, `phone-light-09b-calibration-tooltip`, `phone-light-08-model-card`, `phone-light-12-plans`, `desktop-light-calibration`

## 13-theme-toggle (21:25–21:35) · Current

The light/dark toggle (System, Light, Dark).
- `phone-light-system-chose-dark.png`: a phone set to light, with Dark chosen on You
- `phone-dark-system-chose-light.png`: a phone set to dark, with Light chosen on You
- `phone-*-home-in-*.png`: the home page after a reload, still in the chosen theme
- `desktop-sidebar-toggle-*`: the sidebar's three-icon toggle, dark and light
- `first-try-sidebar-crowded/`: **bad**. The first sidebar version, where the toggle squeezed "Prototype · example scores" onto two lines.
- **Sent:** `phone-light-system-chose-dark.png`, `desktop-sidebar-toggle-dark-crop.png`

## 14-dashboard-settings (21:45–22:00) · Current layout; colours changed in 15

The Dashboard home, the Settings tab and the five-tab dock, on example data (a list of three screened). Light and dark.
- `phone-*-1-dashboard-empty`: the dashboard before anything is screened
- `phone-*-2-dashboard`, `phone-*-2b-dashboard-full`: the dashboard after a list (3 screened: 1 Meet, 1 Look closer, 1 Pass)
- `phone-*-3-founders-filtered`: Founders opened from the Look closer tile
- `phone-*-4-settings`, `phone-*-4b-settings-full`: Settings
- `phone-*-5-you`: You, now just the profile
- `phone-*-dock`: the five-tab dock, close up
- `desktop-*-{dashboard,settings,founders}`: desktop, both themes
- `first-try-odds-card-wraps/`: **bad**. The first desktop dashboards, where "3 pts" wrapped onto two lines in the odds card.
- In the screenshots, Notifications reads "Blocked" because the test browser denies them by default.
- **Sent:** `phone-light-2-dashboard`, `phone-light-dock`, `phone-light-4-settings`, `desktop-light-dashboard`

## 15-more-colour (22:35) · Current

Both themes with a little more brand colour (the accent is now the stamp-pad blue), on example data (a list of three screened). Phones shot at 2×.
- `phone-*-0-intro-odds`: the intro's second screen, with blue odds dots and a blue Next
- `phone-*-1-dashboard`, `desktop-*-1-dashboard`: tinted session tiles, the blue eyebrow and active sidebar item
- `phone-*-2-new`, `desktop-*-2-new`: Screen a founder, with the blue Screen founder button and focus ring
- `phone-*-3-settings`, `desktop-*-3-settings`: Settings (selections stay ink)
- `phone-*-4-plans`, `desktop-*-4-plans`: Plans, with the featured tier in blue
- `phone-*-5-founders`, `desktop-*-5-founders`: the Founders list
- `phone-*-6-memo`, `desktop-*-6-memo`: a memo; the verdict slab is unchanged
- No bad first tries this round: the one problem (the light blue was too dim on the dark phone dock) was caught by a contrast check before any screenshot.
- **Sent:** `phone-light-1-dashboard`, `phone-dark-1-dashboard`, `desktop-light-1-dashboard`, `phone-light-0-intro-odds`

## 16-real-kev (2026-11-15, 08:20–09:00) · Check

The app on the **real models** for the first time: research's real `rules.json`, `thresholds.json` and `model.json`, base Kev answering the 40 questions and the trained production Kev deciding, both served by research's `kev_server` in this sandbox (CPU). The research agent was still the mock, so the founders are the made-up examples. Phones shot at 2×.
- `phone-light-1-memo-verdict`: Ada Moreno, Meet at 32% (the memo appeared 14 s after the tap)
- `phone-light-2-factors-pending`, `-3-factors-partial`, `-4-factors-complete`: "What moves the score" filling in after the memo opens (0 of 40, then 5 of 40 at 38 s, then all at about 3.5 minutes)
- `phone-light-5-what-if`: Samir Haddad's top factor flipped: Look closer at 21%, was 27%
- `phone-light-6-questions`: the 40 real screening questions with base Kev's answers
- `phone-light-7-bar-no-data`, `-8-verdict-no-bar`: $1B+ within 5 years, where no validation founder got there: "Not enough data", and the verdict says there's no bar
- `phone-light-9-calibration`, `desktop-*-calibration`: the calibration page on the final test numbers (C3, 600 founders, 1 pt)
- `desktop-*-model-card`: the model card's new status and limits
- `phone-*-10-kev-off-demo-cache`: Ada Moreno with the Kev server **switched off**: the same verdict, every driver and the new "All founders: 20%" line, all from the demo cache (`backend/screener/data/kev_demo_cache.json`)
- `first-try-mid-load/`: **bad**. The first what-if shot, taken before the answer arrived (it still showed 32%), and a bar-sheet shot with the "Not enough data" note below the fold.
- **Sent:** `phone-light-1-memo-verdict`, `phone-light-2-factors-pending`, `phone-light-5-what-if`, `phone-light-9-calibration`

## 17-demo-video (2026-11-15, 08:55–10:20) · Current

**`halomark-demo.mp4`**: the 1:53 demo video, 1920×1080, 30 fps, -16 LUFS. App walkthrough on the real models and research's real artefacts, with one real founder (Tope Awotona: live research, about 3 minutes shown sped up 14.3× and labelled as such) and the made-up example founders for the montage.
- **Design:** motion scenes by Claude Fable 5.2 (`scenes/`, "the odds slip": ink on paper, struck stamps, the research scene inverted). Brief: `BRIEF.md`; Fable's notes: `scenes/README.md`.
- **Voiceover:** ElevenLabs, voice Alice, eleven_multilingual_v2, one file per section (`voiceover/`), from `script.json`. 1,174 characters, plus about 230 for the voice-note demo audio (`voice-note/`, a second voice played into the browser's simulated microphone, then transcribed and sorted for real).
- **Footage:** recorded by `tools/record-clips.cjs` and `tools/record-notify.cjs` (phone at 2×), cut to the scenes' slots by `tools/frames-to-clips.py`; the raw frames and 30 fps frame sequences are git-ignored. Rendered frame by frame by `tools/render-video.cjs` (each scene's `seek(t)`), joined with the voice by ffmpeg.
- `poster.png`: the title card; `contact-sheet.jpg`: a frame every 4 seconds.
- **Research spend:** two live research runs on Tope Awotona ($0.32, then $0.28): the first screening timed out while the machine was overloaded (fixed: `KEV_TIMEOUT_S` 180) and its footage showed the "0 sources" bug (fixed).
- **Found and fixed while filming:** the real research agent never reported its sources to the progress screen; the memo's question list showed rule ids while drivers filled in; a pasted web address ran off the progress title.
- **Sent:** `halomark-demo.mp4`

## 18-how-it-works-trl (2026-11-15, 10:10) · Current

How it works, two new sections (owner's request): **Why names are removed** (what anonymising keeps: a university's degree, subject and ranking band; an employer's description, size, industry and tenure; and the three reasons) and **Built on TRL, by Vela Research** (TRL is Vela Research's open-source, MIT-licensed library; each step "In TRL" against "In Halomark"; what this project added; links to TRL and Kev on GitHub). The model card's wording matches. Phones shot at 2×.
- `*-why-names`, `*-built-on-trl`: each section, phone and desktop, light and dark
- `*-light-full`: the whole page
- **Sent:** `desktop-light-built-on-trl`, `phone-light-why-names`

## tools

- `record-walkthrough.cjs`: the script that recorded v3 and v4, with the ffmpeg command in its header, so the video can be re-shot after design changes
- `walkthrough-batch.csv`: the three example founders it pastes into "Screen a list"

## Not included

- **Raw video frames.** The screen recorder saves one image per screen change, about 3,000 JPEGs for v2, v3 and v4. Each one is already inside its video.
- **Anything before 13:00.** Tasks 1–3 (the API contract, the backend and the research agent) produced no images.
