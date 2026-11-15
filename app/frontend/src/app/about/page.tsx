"use client";

// How it works: the pipeline in plain words, what anonymising keeps and why, what's built on TRL (Vela Research's
// open-source library) and what this project added, how to read a verdict, links to the model card and the
// calibration page, sharing from other apps, and privacy in short.
import Link from "next/link";
import { useEffect, useState } from "react";

import { useApp } from "@/components/AppState";
import { IconChevronRight } from "@/components/icons";
import { Disclaimer, Logo, Notice, Page, PageHeader, SectionTitle, VerdictTile, linkClass } from "@/components/ui";
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
    body: "Names come out, but what they tell you stays: a university becomes its degree, subject and world-ranking band, and an employer becomes a short description with its size, industry and how long they stayed. The result is the standard profile the models were trained on, line for line.",
  },
  {
    title: "Ask",
    who: "TRL's questions, answered by Kev",
    body: "A checklist of 40 yes/no questions, such as \u201cHas the founder had a prior exit?\u201d, written once with TRL during the research, is answered for this founder by Kev, a small open-source decision model.",
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

const WHY_ANONYMOUS = [
  ["The model only knows this format", "It learned from 3,000 profiles written exactly this way, most of them generated, so it has never seen a real university or company name and couldn't use one reliably."],
  ["Names leak hindsight", "Language models know what became of well-known companies and their alumni. A name would let the model recall outcomes instead of judging the background, and the founder's own company name would give the answer away."],
  ["No brand-name shortcuts", "The training data was built so that no single detail decides the outcome. The ranking band and the employer's description keep the real signal without the halo of the name."],
] as const;

const TRL_STEPS = [
  {
    step: "Think",
    trl: "A language model writes yes/no questions that tell outcomes apart.",
    here: "Claude Opus 5.5 wrote 93 questions about founders, once. The 40 that predicted best are kept.",
  },
  {
    step: "Reason",
    trl: "A model answers every question for each sample.",
    here: "Kev-0.6B, an open-source decision model, answers them in place of TRL's usual answerer (TypeSafe's Jev), to run for free.",
  },
  {
    step: "Learn",
    trl: "A classical model turns the answers into a prediction (an elastic net by default).",
    here: "A fine-tuned Kev makes the final call instead, added to TRL as a new option, and compared with TRL's own.",
  },
] as const;

export default function AboutPage() {
  const { health } = useApp();
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

      {health?.mock && (
        <div className="mt-4">
          <Notice tone="info" title="Prototype">
            Parts of this server still run on stand-ins (shown on each memo), so treat those scores as examples.
          </Notice>
        </div>
      )}

      <section className="mt-12" aria-labelledby="names">
        <SectionTitle id="names" note="You still see who the founder is, and every source, in the memo. Only what the model reads is anonymised.">
          Why names are removed
        </SectionTitle>
        <dl>
          {WHY_ANONYMOUS.map(([k, v]) => (
            <div key={k} className="grid gap-1 border-b border-line py-3.5 sm:grid-cols-[220px_1fr] sm:gap-6">
              <dt className="text-[15px] font-bold tracking-[-0.01em]">{k}</dt>
              <dd className="text-[14.5px] leading-relaxed text-ink-2">{v}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-3 text-[13.5px] leading-relaxed text-muted">
          The exact university or employer can carry more than a ranking band. Letting the model read that detail would be a research change: new training data and retraining.
        </p>
      </section>

      <section className="mt-12" aria-labelledby="trl">
        <SectionTitle id="trl">Built on TRL, by Vela Research</SectionTitle>
        <p className="max-w-[66ch] text-[15px] leading-relaxed text-ink-2">
          The scoring in Halomark runs on <strong className="font-bold text-ink">TRL (Think, Reason, Learn)</strong>, an open-source library from{" "}
          <strong className="font-bold text-ink">Vela Research</strong>, released under the MIT licence. TRL is their work. Halomark uses it, adapts it and builds on it: the
          framework, its question-writing and its answering pipeline are Vela&apos;s; the choices and additions below are this project&apos;s.
        </p>
        <ol className="mt-5">
          {TRL_STEPS.map(({ step, trl, here }, i) => (
            <li key={step} className="grid gap-2 border-t border-line-strong py-4 sm:grid-cols-[120px_1fr_1fr] sm:gap-6">
              <p className="text-[19px] font-bold tracking-[-0.02em]">
                <span className="cond mr-2 text-[28px] font-black">{i + 1}</span>
                {step}
              </p>
              <p className="text-[14.5px] leading-relaxed text-ink-2">
                <span className="eyebrow block text-muted">In TRL</span>
                {trl}
              </p>
              <p className="text-[14.5px] leading-relaxed text-ink-2">
                <span className="eyebrow block text-accent">In Halomark</span>
                {here}
              </p>
            </li>
          ))}
        </ol>
        <div className="mt-2 rounded-[18px] bg-surface-2 px-4 py-4 text-[14.5px] leading-relaxed text-ink-2">
          <p className="font-bold text-ink">What this project added</p>
          <ul className="mt-2 space-y-1.5">
            {[
              "In a fork of TRL: a final step that hands the decision to a decision model (Jev, Kev or any model with the same interface), and option descriptions for multiple-choice questions.",
              "Kev fine-tuned on TRL's answers, with calibrated odds, compared against TRL's own final steps on the same founders.",
              "Around it, the app: web research limited to before the founding date, the anonymised profile, your bar, and the memo.",
            ].map((t) => (
              <li key={t} className="flex gap-3">
                <span className="mt-[0.6em] h-[3px] w-3 shrink-0 rounded-full bg-ink" aria-hidden />
                {t}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[13.5px] text-muted">
            In testing, no final step beat TRL&apos;s default on accuracy; the fine-tuned Kev gave the best-calibrated odds.
          </p>
        </div>
        <p className="mt-3 text-[14px]">
          <a href="https://github.com/Vela-Research/think-reason-learn" target="_blank" rel="noopener noreferrer" className={linkClass}>
            TRL on GitHub (Vela Research)
          </a>
          <span className="text-muted"> · </span>
          <a href="https://github.com/jaredpalmer/kev" target="_blank" rel="noopener noreferrer" className={linkClass}>
            Kev on GitHub
          </a>
        </p>
      </section>

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
