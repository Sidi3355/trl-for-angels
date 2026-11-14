"use client";

// How it works, what the numbers mean, privacy, and the app's settings.
import { useEffect, useState } from "react";

import { useApp } from "@/components/AppState";
import { BarSummary } from "@/components/BarSheet";
import { IconLock } from "@/components/icons";
import { Button, Disclaimer, Logo, Page, PageHeader, SectionTitle, VerdictTile, cx } from "@/components/ui";
import { API_URL, getPasscode, setPasscode } from "@/lib/api";
import { DECISION_LABELS } from "@/lib/format";
import { clearDeals } from "@/lib/session";

const STEPS = [
  { title: "Research", body: "An AI agent searches the web for the founder's background, and keeps only what was true on the day the company was founded. Every fact links to its source." },
  { title: "Anonymise", body: "Names of people, companies and universities are removed, and the background is written into the same standard profile the model was trained on." },
  { title: "Score", body: "Screening questions are answered from the profile, and a calibrated decision model estimates how big the outcome could be, and how long it could take." },
  { title: "Decide", body: "Your bar turns that chance into meet, look closer or pass. Change it any time: every verdict updates instantly." },
];

const row = "flex items-center justify-between gap-4 border-b border-line py-4";

export default function AboutPage() {
  const { bar, openBarSheet, health, healthError, deals } = useApp();
  const [hasCode, setHasCode] = useState(false);
  useEffect(() => setHasCode(Boolean(getPasscode())), []);
  const [cleared, setCleared] = useState(false);

  return (
    <Page>
      <PageHeader title="How it works" subtitle="Angels screen alone. Halomark does the first pass for you: research, a calibrated score, and the reasons behind it." />

      <ol className="grid gap-x-10 sm:grid-cols-2">
        {STEPS.map(({ title, body }, i) => (
          <li key={title} className="flex gap-4 border-t border-line-strong py-5">
            <span className="cond w-7 shrink-0 text-[56px] font-black leading-[0.8]" aria-hidden>
              {i + 1}
            </span>
            <div>
              <p className="text-[19px] font-bold tracking-[-0.02em]">{title}</p>
              <p className="mt-1.5 text-[14.5px] leading-relaxed text-muted">{body}</p>
            </div>
          </li>
        ))}
      </ol>

      <section className="mt-10">
        <SectionTitle note="The chance is the share of founders with a background like this who reached your target in the model's data. It is calibrated, so 30% means about 3 in 10.">
          Reading a verdict
        </SectionTitle>
        <ul>
          {(
            [
              ["advance", "The chance clears your bar. Worth a meeting."],
              ["escalate", "Close to your bar. Your judgement decides."],
              ["pass", "Below your bar. Few founders like this reached your target in testing."],
            ] as const
          ).map(([d, text]) => (
            <li key={d} className="flex items-center gap-4 border-b border-line py-3.5">
              <VerdictTile decision={d} size={44} />
              <p className="text-[15px] leading-snug text-ink-2">
                <strong className="block text-[17px] font-bold tracking-[-0.015em] text-ink">{DECISION_LABELS[d]}</strong>
                {text}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-12" aria-labelledby="the-name">
        <SectionTitle id="the-name">The name</SectionTitle>
        <div className="flex items-start gap-4">
          <Logo size={44} className="mt-0.5 shrink-0" />
          <p className="max-w-[62ch] text-[15px] leading-relaxed text-ink-2">
            A hallmark is the small stamp an assay office strikes into gold once it has tested the metal. Halomark does that for an angel. It tests a founder against your bar and stamps the
            verdict: meet, look closer or pass. The halo struck into the stamp stands for you, the angel.
          </p>
        </div>
      </section>

      <section className="mt-12">
        <SectionTitle>Settings</SectionTitle>
        <div className="-mt-3.5">
          <div className={row}>
            <span className="min-w-0">
              <span className="block text-[15.5px] font-semibold">Your bar</span>
              <span className="block text-[13.5px] text-muted">
                <BarSummary bar={bar} />
              </span>
            </span>
            <Button variant="secondary" onClick={openBarSheet}>
              Change
            </Button>
          </div>
          <div className={row}>
            <span className="min-w-0">
              <span className="block text-[15.5px] font-semibold">This session&apos;s founders</span>
              <span className="block text-[13.5px] text-muted">{cleared ? "Cleared." : `${deals.length} founder${deals.length === 1 ? "" : "s"}. Gone when you close the app.`}</span>
            </span>
            <Button variant="secondary" disabled={!deals.length} onClick={() => { clearDeals(); setCleared(true); }}>
              Clear
            </Button>
          </div>
          {hasCode && (
            <div className={row}>
              <span className="flex items-center gap-2 text-[15.5px] font-semibold">
                <IconLock size={17} className="text-muted" /> Passcode saved for this session
              </span>
              <Button variant="secondary" onClick={() => { setPasscode(null); setHasCode(false); }}>
                Forget
              </Button>
            </div>
          )}
          <div className={row}>
            <span className="min-w-0">
              <span className="block text-[15.5px] font-semibold">Service</span>
              <span className="block truncate text-[13.5px] text-muted">{API_URL.replace(/^https?:\/\//, "")}</span>
            </span>
            <span className={cx("flex shrink-0 items-center gap-1.5 text-[13.5px] font-semibold", healthError ? "text-danger" : health ? "text-ink" : "text-muted")}>
              {health && !healthError && <span className={cx("h-2 w-2 rounded-full", health.mock ? "bg-escalate-fill" : "bg-advance-fill")} aria-hidden />}
              {healthError ? "Offline" : health ? (health.mock ? "Online · prototype, example scores" : "Online") : "Checking…"}
            </span>
          </div>
        </div>
      </section>

      <ShareSetup />

      <section className="mt-12">
        <SectionTitle>Privacy</SectionTitle>
        <ul className="space-y-2.5 text-[15px] leading-relaxed text-ink-2">
          {[
            "Only public information is used.",
            "Your notes appear in the memo and are never sent to the model. Facts in them can fill the form, and you check every value before screening.",
            "Voice notes are transcribed by ElevenLabs and the notes sorted by Claude; the recording isn't kept by Halomark.",
            "Nothing is kept after your session: memos are deleted on the server, and the founders list lives only in this app until you close it.",
          ].map((t) => (
            <li key={t} className="flex gap-3">
              <span className="mt-[0.6em] h-[3px] w-3 shrink-0 rounded-full bg-ink" aria-hidden />
              {t}
            </li>
          ))}
        </ul>
      </section>

      <Disclaimer className="mt-12" />
    </Page>
  );
}

/** How to send a LinkedIn profile or website from another app straight into Halomark. */
function ShareSetup() {
  const [origin, setOrigin] = useState("");
  const [copied, setCopied] = useState(false);
  useEffect(() => setOrigin(window.location.origin), []);
  const link = `${origin}/share?url=`;
  return (
    <section className="mt-12" aria-labelledby="share-setup">
      <SectionTitle id="share-setup" note="Shared links open a confirm screen, so nothing is screened until you tap Screen founder.">
        Share from other apps
      </SectionTitle>
      <div className="space-y-6 text-[15px] leading-relaxed text-ink-2">
        <div>
          <p className="font-bold text-ink">iPhone: a one-time Shortcut</p>
          <ol className="mt-2 list-decimal space-y-1.5 pl-5">
            <li>Open the Shortcuts app and tap <strong className="text-ink">+</strong> to make a new shortcut. Name it &ldquo;Screen founder&rdquo;.</li>
            <li>Turn on <strong className="text-ink">Show in Share Sheet</strong> (in the shortcut&apos;s settings) and set it to receive <strong className="text-ink">URLs</strong>.</li>
            <li>Add the action <strong className="text-ink">URL Encode</strong> with the Shortcut Input.</li>
            <li>Add the action <strong className="text-ink">Open URLs</strong>, with this address followed by the URL Encoded Text:</li>
          </ol>
          <div className="mt-3 flex items-center gap-2 rounded-[14px] border-[1.5px] border-line-strong bg-surface p-1.5 pl-3.5">
            <code id="share-link" className="min-w-0 flex-1 truncate font-mono text-[13px] text-ink">{link}</code>
            <button
              type="button"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(link);
                  setCopied(true);
                } catch {
                  const el = document.getElementById("share-link");
                  if (el) window.getSelection()?.selectAllChildren(el);
                }
              }}
              className="shrink-0 rounded-full bg-ink px-3.5 py-2 text-[13px] font-bold text-bg"
            >
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <p className="mt-2 text-[13.5px] text-muted">Then, in LinkedIn or Safari, tap Share and choose Screen founder. It opens in Safari.</p>
        </div>
        <div>
          <p className="font-bold text-ink">Android</p>
          <p className="mt-1">Add Halomark to your home screen (Chrome menu, then Install app). Halomark then appears in the share menu of any app.</p>
        </div>
      </div>
    </section>
  );
}
