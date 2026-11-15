# Demo video, version 2: the owner's notes

The owner watched version 1 and liked it ("very good"). These are their notes, and what each means for the scenes.
Everything in `BRIEF.md` still holds (brand, honesty, the rendering contract, work only in this folder, no commits).

## Already done outside the scenes

- **New voiceover** (voice George, British). New files in `voiceover/` (`<id>.mp3`, `<id>.alignment.json`,
  `durations.json`); the old ones are in `voiceover/v1-alice/`. Durations: s1 11.47, s2 7.55, s3 15.78, s4 13.56,
  s5 6.03, s6 23.85, s7 11.05, s8 5.62 (94.9 s in all, shorter than before). `script.json` has the new text:
  - s6 now says "open-source" (TRL is "Vela Research's open-source think, reason, learn framework"; Kev is "a
    small open-source decision model").
  - s7 now opens with a bridge back into the app: "Back in the app, there's more."
  - s8 is now "Halomark, calibrated odds for angels. A screening aid. Not investment advice." (ending low).
  - The alignment files already spell "Halomark" (the voice reads "Halo-mark" for pronunciation).
- **Clips re-cut at real speed** (`clips/*/meta.json` has the new lengths): c1_type 7.77 s, c2_research 11.10 s
  (three real-speed excerpts crossfaded: a search arriving, the sources filling in, the verdict landing; **no speed-up
  any more**), c3_profile 9.87, c4_verdict 4.20, c5_bar 7.77, c6_whatif 9.67 (crossfaded join), c7_list 2.60,
  c8_voice 3.03 (crossfaded join), c9_notify 2.53, c10_profile 3.00. Re-time the clip slots to the new scenes.

## What the scenes need

1. **Re-time every scene to the new voiceover** (run `node scenes/build-data.js` first; keep `voice.at` and
   `voiceAt` in step). The total will be shorter than before; that's fine (about 1:45 is good).
2. **No abrupt cuts between scenes** (the owner: "a couple of sloppy abrupt cut-offs", "mainly between the product
   and research scenes, the black and white"). Design proper transitions, on brand (print-like: a sheet of ink or
   paper wiping across, things set and struck; no soft dissolves into mush, no glow). Each scene's last moments
   should hand over to the next scene's first frame, so the joins are continuous:
   - **s5 → s6 (paper → ink)** and **s6 → s7 (ink → paper)** matter most: e.g. an ink sheet wipes up over s5 and
     s6 opens on ink; at the end of s6 a paper sheet wipes up and s7 opens on paper with the phone coming back in.
   - Between the paper scenes, nothing should jump: elements that persist (the running head, the phone) stay put;
     outgoing text leaves (wipes or slides away) before the cut instead of vanishing; captions leave with it.
   - The **end** must not cut off: the end card holds, then the whole frame settles (for example to plain paper or
     ink) over the last ~0.8 s. (The audio is faded out to match.)
   - After you've built it, check every join: render the last frame of each scene and the first frame of the next
     side by side, and make sure they match.
3. **A slightly larger phone** ("just a tad"): about 10–12% bigger, still fitting the frame with breathing room.
4. **Make the phone realistic**: a status bar strip above the app (9:41, signal, Wi-Fi, battery, in the app's ink on
   paper) and a Dynamic Island pill at the top centre of the screen, as on a current iPhone; the app's footage sits
   below the status bar. Keep the device itself plain and unbranded.
5. **Zoom in to show key details** (the owner: "a couple scenes where it zooms into it, to highlight key features or
   details that require it"). Three to five zooms, each one smooth in and out (deterministic, seekable), timed to
   the voice. Look at the clip frames (`clips/<name>/000001.jpg` ...) to find where and when. Good candidates:
   - s3: the sources list filling in as research completes (c2_research, middle excerpt);
   - s3: the anonymised profile text "What the model read" (c3_profile);
   - s4: the verdict "31%" with "All founders: 20%" (c4_verdict);
   - s5: the what-if verdict "Look closer 25%, was 31%" (c6_whatif, after the crossfade);
   - s7: the voice note's "Filled in: Technical · 10-15 years ..." line (c8_voice).
   The footage is 804×1748, so a 2× zoom of the phone is still sharp.
6. **Remove the "sped up" badge** everywhere (nothing is sped up now).
7. **On-screen wording**: "open-source", never just "open" (e.g. Kev under Reason: "a small open-source decision
   model"). Keep TRL credited to Vela Research.
8. Keep everything else that worked: the look, the captions, the research scene, the calibration chart, the end card.

When done: regenerate previews, check the joins as above, and update `scenes/README.md` and `scenes/manifest.json`.
Report back with the scene list and durations, the clip slots, the zooms (scene, time, what), and anything the
assembler must know.
