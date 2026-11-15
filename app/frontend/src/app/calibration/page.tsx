// How accurate are the odds? One reliability chart, three numbers in plain words, one honest limits
// line. Every number comes from src/data/calibration.json (written by scripts/calibration-from-results.py
// from the research results), so provisional numbers can be swapped for final ones without code changes.
import type { Metadata } from "next";
import Link from "next/link";

import { ReliabilityChart, type Bin } from "@/components/ReliabilityChart";
import { Disclaimer, Page, PageHeader, SectionTitle, Tag, linkClass } from "@/components/ui";
import data from "@/data/calibration.json";
import { gapPoints } from "@/lib/format";

export const metadata: Metadata = { title: "How accurate are the odds?" };

const pct = (x: number) => `${Math.round(x * 100)}%`;
/** 0.556 -> "about 6 in 10" */
const inTen = (x: number) => `about ${Math.round(x * 10)} in 10`;

export default function CalibrationPage() {
  const bins = data.bins as Bin[];
  const hits = Math.round(data.precision * data.flagged);
  const found = Math.round(data.recall * data.successes);
  const high = bins.filter((b) => b.low >= 0.5).reduce((n, b) => n + b.count, 0);
  const top = Math.max(...bins.filter((b) => b.count > 0).map((b) => b.high));
  const splitName = data.split === "test" ? "test" : "validation";
  const headline = [
    {
      value: gapPoints(data.ece),
      label: "Typical gap between the odds and what happened",
      detail: `On average, the chance it gave was within about ${gapPoints(data.ece).replace("pts", "percentage points").replace("pt", "percentage point")} of the share who actually succeeded.`,
    },
    {
      value: `${Math.round(data.precision * 10)} in 10`,
      label: "Of the founders it rated highest, this many succeeded",
      detail: `${hits} of the ${data.flagged} it rated highest reached ${data.target}, against ${inTen(data.base_rate)} of all ${data.founders} founders.`,
    },
    {
      value: `${Math.round(data.recall * 100)}%`,
      label: "Of the founders who succeeded, the share it rated highest",
      detail: `It picked out ${found} of the ${data.successes} who succeeded. Most successes look ordinary on paper, which is why a pass is never a no.`,
    },
  ];

  return (
    <Page>
      <PageHeader
        back={{ href: "/about", label: "How it works" }}
        title="How accurate are the odds?"
        subtitle="A chance is only useful if it's honest: of all the founders given about 30%, about 30% should succeed. Here's that check, on founders the model never learned from."
      />

      <div className="flex flex-wrap items-center gap-2 text-[13.5px] text-muted">
        <Tag tone={data.status === "final" ? "good" : "warn"}>{data.status === "final" ? "Final" : "Provisional"}</Tag>
        <span>
          {data.model}, {data.founders} {splitName} founders, success means {data.target}.
        </span>
      </div>
      {data.model_note && <p className="mt-2 max-w-[62ch] text-[13.5px] leading-relaxed text-muted">{data.model_note}</p>}

      <section className="mt-8" aria-labelledby="chart">
        <SectionTitle id="chart" note="Each dot is a group of founders given similar odds. On the dashed line, the odds were exactly right.">
          When it gave a chance, how many succeeded?
        </SectionTitle>
        <ReliabilityChart bins={bins} />
      </section>

      <section className="mt-10" aria-labelledby="numbers">
        <SectionTitle id="numbers">In plain words</SectionTitle>
        <dl className="grid gap-x-8 sm:grid-cols-3">
          {headline.map((h) => (
            <div key={h.label} className="border-b border-line py-4 sm:border-b-0">
              <dt className="text-[14px] font-semibold leading-snug text-ink-2">{h.label}</dt>
              <dd className="mt-1">
                <span className="cond block text-[52px] font-black leading-[0.95] tracking-[-0.01em]">{h.value}</span>
                <span className="mt-1.5 block text-[13.5px] leading-relaxed text-muted">{h.detail}</span>
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <p className="mt-8 max-w-[66ch] rounded-[14px] bg-surface-2 px-4 py-3 text-[14px] leading-relaxed text-ink-2">
        <strong className="font-bold">The honest limit:</strong> these are {data.founders} founders from a mostly generated dataset (2,950 of 3,000 profiles are synthetic), so they show how honest the odds
        are on that data, not on real founders.{" "}
        {high === 0
          ? `It never gave a founder odds above ${pct(top)}: it is cautious, so it rarely singles anyone out, and the right of the chart is empty.`
          : `Few founders got odds of ${pct(0.5)} or more (${high}), so the top of the chart rests on little data.`}
      </p>

      <p className="mt-6 text-[14px] text-muted">
        More about the model and its data in the{" "}
        <Link href="/model-card" className={linkClass}>
          model card
        </Link>
        .
      </p>
      <p className="mt-2 text-[12px] text-faint">
        Source: {data.source}. Updated {data.updated}.
      </p>
      <Disclaimer className="mt-10" />
    </Page>
  );
}
