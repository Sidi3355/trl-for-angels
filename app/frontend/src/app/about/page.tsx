"use client";

// How it works: the pipeline in plain words, how to read a verdict, links to the model card and the
// calibration page, sharing from other apps, and privacy in short. Settings live on the account page.
import Link from "next/link";
import { useEffect, useState } from "react";

import { IconChevronRight } from "@/components/icons";
import { Button, Disclaimer, Logo, Notice, Page, PageHeader, SectionTitle, VerdictTile } from "@/components/ui";
import { DECISION_LABELS } from "@/lib/format";

const STEPS = [
  {
    title: "Research",
    who: "Research agent (Claude)",
    body: "Searches the web for the founder's background and keeps only what was true on the day the company was founded. Every fact links to its source, and anything you entered wins over the agent.",
  },
  {
    title: "Anonymise",
    who: "A fixed profile",
    body: "Names of people, companies and universities are removed, and the background is written into the same standard profile the models were trained on, line for line.",
  },
  {
    title: "Ask",
    who: "TRL's questions, answered by Kev",
    body: "A checklist of yes/no questions, such as \u201cHas the founder had a prior exit?\u201d, written once by TRL during the research, is answered for this founder by Kev, a small open decision model.",
  },
  {
    title: "Score",
    who: "A fine-tuned, calibrated Kev",
    body: "Turns the answers into the chance of each outcome, from shut down to over $1B, and how long it could take. Calibrated, so 30% means about 3 in 10.",
  },
  {
    title: "Your settings",
    who: "Your bar",
    body: "Your target, timeline, risk appetite and filters turn those chances into one number: the chance this founder reaches your target.",
  },
  {
    title: "Verdict",
    who: "Meet \u00b7 Look closer \u00b7 Pass",
    body: "Clears your bar: meet. Close to it: look closer. Below it: pass. The memo shows what moved the score, and lets you flip any answer to see what changes.",
  },
];

function MoreLink({ href, title, note }: { href: string; title: string; note: string }) {
  return (
    <Link href={href} className="group flex items-center justify-between gap-4 rounded-[18px] border border-line bg-surface px-4 py-4 transition-colors hover:border-ink">
      <span>
        <span className="block text-[17px] font-bold tracking-[-0.015em]">{title}</span>
        <span className="block text-[13.5px] text-muted">{note}</span>
      </span>
      <IconChevronRight size={20} className="shrink-0 text-muted transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}

export default function AboutPage() {
  return (
    <Page>
      <PageHeader title="How it works" subtitle="From a founder's name to Meet, Look closer or Pass, in six steps. Each one does one job, and the memo shows its work." />

      <ol className="grid gap-x-10 sm:grid-cols-2">
        {STEPS.map(({ title, who, body }, i) => (
          <li key={title} className="flex gap-4 border-t border-line-strong py-5">
            <span className="cond w-8 shrink-0 text-[56px] font-black leading-[0.8]" aria-hidden>
              {i + 1}
            </span>
            <div>
              <p className="text-[19px] font-bold tracking-[-0.02em]">{title}</p>
              <p className="eyebrow mt-0.5 text-muted">{who}</p>
              <p className="mt-1.5 text-[14.5px] leading-relaxed text-ink-2">{body}</p>
            </div>
          </li>
        ))}
      </ol>

      <div className="mt-4">
        <Notice tone="info" title="Prototype">
          Until the trained models are plugged in, steps 3 and 4 use a placeholder, so treat every score as an example.
        </Notice>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <MoreLink href="/calibration" title="How accurate are the odds?" note="What 30% really means, checked" />
        <MoreLink href="/model-card" title="Model card" note="The model, its data and its limits" />
      </div>

      <section className="mt-12">
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

      <ShareSetup />

      <section className="mt-12">
        <SectionTitle>Privacy in short</SectionTitle>
        <ul className="space-y-2.5 text-[15px] leading-relaxed text-ink-2">
          {[
            "Only public information is used, and only what was true when the company was founded.",
            "Your notes appear in the memo and are never sent to the model. Facts in them can fill the form, and you check every value before screening.",
            "Nothing is kept on our servers after your session. Your profile and settings stay on this device.",
            "Claude researches and sorts notes, ElevenLabs transcribes voice notes, and Kev scores the anonymised profile.",
          ].map((t) => (
            <li key={t} className="flex gap-3">
              <span className="mt-[0.6em] h-[3px] w-3 shrink-0 rounded-full bg-ink" aria-hidden />
              {t}
            </li>
          ))}
        </ul>
        <p className="mt-4 text-[14px]">
          <Link href="/privacy" className="font-semibold underline decoration-line-strong underline-offset-[3px] hover:decoration-ink">
            The full privacy notice (draft)
          </Link>
        </p>
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
