// Model card: what the model is, what it predicts, what it learned from, and its limits. Facts come from
// the research branch's results/METHODS.md and results/data/README.md (2026-11-14); keep them in step.
import type { Metadata } from "next";
import Link from "next/link";

import { Notice, Page, PageHeader, SectionTitle, linkClass } from "@/components/ui";

export const metadata: Metadata = { title: "Model card" };

type Row = [string, React.ReactNode];

function Rows({ rows }: { rows: Row[] }) {
  return (
    <dl className="-mt-1.5">
      {rows.map(([k, v]) => (
        <div key={k} className="grid gap-1 border-b border-line py-3.5 sm:grid-cols-[200px_1fr] sm:gap-6">
          <dt className="text-[14px] font-bold tracking-[-0.01em]">{k}</dt>
          <dd className="text-[14.5px] leading-relaxed text-ink-2">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function Bullets({ items }: { items: React.ReactNode[] }) {
  return (
    <ul className="space-y-2.5 text-[14.5px] leading-relaxed text-ink-2">
      {items.map((t, i) => (
        <li key={i} className="flex gap-3">
          <span className="mt-[0.6em] h-[3px] w-3 shrink-0 rounded-full bg-ink" aria-hidden />
          <span>{t}</span>
        </li>
      ))}
    </ul>
  );
}

export default function ModelCardPage() {
  return (
    <Page>
      <PageHeader
        back={{ href: "/about", label: "How it works" }}
        eyebrow="Model card"
        title="The model behind Halomark"
        subtitle="What it is, what it predicts, what it learned from, and where it falls short."
      />

      <Notice tone="warn" title="Screening aid, not investment advice">
        The model estimates odds from a founder&apos;s background on the day the company was founded. It was trained mostly on generated data, so no real-world accuracy is claimed. In this
        prototype the scores are examples until the trained model is plugged in.
      </Notice>

      <section className="mt-10">
        <SectionTitle>The model</SectionTitle>
        <Rows
          rows={[
            ["Name", "Kev-0.6B, fine-tuned for Halomark"],
            [
              "What it is",
              <>
                A small, open-source decision model (Apache-2.0): Qwen3-0.6B-Base with a rank-16 LoRA and a pointer head that turns the model&apos;s reading into a probability for each option. Kev is an
                open-source reconstruction of TypeSafe&apos;s Jev, released as <span className="font-mono text-[13px]">jaredpalmer/kev-0.6b</span>.
              </>,
            ],
            [
              "How it's built",
              "With TRL (Think, Reason, Learn), Vela Research's open-source library (MIT licence), adapted for this project. Claude Opus 5.5 wrote a checklist of yes/no questions about founders once; base Kev answers them for each founder; a fine-tuned Kev makes the final call, a step this project added to TRL.",
            ],
            [
              "What it reads",
              "TRL's answers to its 40 best questions. Reading the anonymised profile directly did as well on the validation founders; the answers were chosen because they gave slightly better-calibrated odds there, and they let the memo show which questions drive each verdict.",
            ],
            ["Calibration", "One temperature per question, fitted on the validation founders, so a 30% means about 3 in 10."],
            [
              "Status",
              <>
                The yes/no version is trained and tested:{" "}
                <Link href="/calibration" className={linkClass}>
                  its scores on 600 test founders
                </Link>
                . The app&apos;s version, which also predicts the outcome band and timing, is training now (November 2026). Until it&apos;s plugged in, the app shows example scores.
              </>,
            ],
          ]}
        />
      </section>

      <section className="mt-10">
        <SectionTitle>What it predicts</SectionTitle>
        <Rows
          rows={[
            ["Outcome", "The chance of each final outcome: shut down, under $50M, $50M–$500M, $500M–$1B, over $1B (exit or IPO value, or funding raised if still private)."],
            ["Timing", "The chance of reaching that outcome in under 5 years, 5–8 years, or over 8."],
            ["Your verdict", "Your bar turns these into the chance of reaching your target within your timeline, then Meet, Look closer or Pass."],
            ["Not predicted", "Anything about the company after founding, the deal terms, the market, or whether you should invest."],
          ]}
        />
      </section>

      <section className="mt-10">
        <SectionTitle>Training data</SectionTitle>
        <Rows
          rows={[
            ["Size", "3,000 anonymised founder profiles, each describing the founder on the day the company was founded."],
            ["Where they come from", "50 are based on real founders and companies, with outcomes checked by web search. The other 2,950 are generated, modelled on those 50."],
            [
              "How generated outcomes work",
              "Each generated profile gets a background score from its fields (industry experience, prior exits, team size, education, experience, industry), plus random noise, then is ranked into outcome bands. So outcomes depend on the profile, but only weakly.",
            ],
            ["Success", "Reaching $500M or more: 600 of 3,000 founders (1 in 5)."],
            ["Splits", "2,000 to learn from, 400 to make every choice on (validation), 600 kept back for the final test, read once."],
          ]}
        />
      </section>

      <section className="mt-10">
        <SectionTitle>How founders are described</SectionTitle>
        <Rows
          rows={[
            [
              "Founding-date cutoff",
              "Only what was true on the day the company was founded: background, education, jobs, earlier startups and exits. Traction, funding and later events stay in your notes and never reach the model.",
            ],
            [
              "Anonymisation",
              "No names of people, companies, universities or products, no exact dates or places. What the names said stays: a university becomes its degree, subject and QS ranking band; an employer becomes a description such as “a payments company”, with its size, industry and how long they stayed. The model sees the same fixed profile it was trained on.",
            ],
            ["Unknowns", "A detail the research couldn't confirm is written as unknown, never guessed."],
          ]}
        />
      </section>

      <section className="mt-10">
        <SectionTitle>Known limits</SectionTitle>
        <Bullets
          items={[
            "Mostly generated data: 2,950 of the 3,000 outcomes come from a scoring rule plus noise, so the model learns that rule, not real founder dynamics. No real-world accuracy is claimed; VCBench is the intended real test.",
            "Timing is weak: in the generated data, years to outcome depend only on the outcome band, so the timeline control is an estimate.",
            "Few successes to learn from: 400 in training and 120 in the test set, so every score comes with wide uncertainty.",
            "Honest but cautious: on the test founders its odds were the best calibrated of every method tried, but it never gave anyone more than 40%, so it singles out few founders. It was not more accurate than TRL's standard model.",
            "Real research is messier than training: profiles found on the web have more unknowns than the training profiles.",
            "Kev answers TRL's questions instead of Jev, TRL's usual answerer, and reads the 40 best questions rather than all of them, to fit free GPUs.",
            "It can be confidently wrong about one person: a percentage describes founders like this one, not this founder.",
          ]}
        />
      </section>

      <section className="mt-10">
        <SectionTitle>Use it for</SectionTitle>
        <Bullets
          items={[
            "A first pass on founders you'd otherwise screen alone, with the reasons laid out.",
            "Spotting what's unknown or conflicting before a meeting.",
            <>
              Not for: deciding to invest or not, judging a person, or anything beyond a screening aid. <strong className="font-semibold text-ink">Screening aid, not investment advice.</strong>
            </>,
          ]}
        />
      </section>

      <p className="mt-10 text-[14px] text-muted">
        See how honest the odds are on the{" "}
        <Link href="/calibration" className={linkClass}>
          calibration page
        </Link>
        . Method details: <span className="font-mono text-[12.5px]">results/METHODS.md</span> in the project&apos;s research.
      </p>
    </Page>
  );
}
