"use client";

// How it could end and how long it could take: two stacked bars on ordinal ramps (validated with
// the dataviz palette script), with a bracket over the bands that count towards the investor's bar.
import { Card, SectionTitle, cx } from "@/components/ui";
import { percent } from "@/lib/format";
import type { Policy } from "@/lib/policy";
import { OUTCOME_BANDS, YEARS_BANDS, type Distributions } from "@/lib/types";

const OUTCOME_LABEL: Record<string, string> = {
  "shut down": "Shut down",
  "under $50M": "Under $50M",
  "$50M-$500M": "$50M–$500M",
  "$500M-$1B": "$500M–$1B",
  "over $1B": "Over $1B",
};
const YEARS_LABEL: Record<string, string> = { "under 5": "Under 5 years", "5-8": "5–8 years", "over 8": "Over 8 years" };
const TARGET_START = { "$50M": 2, "$500M": 3, "$1B": 4 } as const;
const TIMELINE_END = { null: 3, 8: 2, 5: 1 } as const;

function Stacked({ title, bands, colors, counted, bracketLabel }: { title: string; bands: { key: string; label: string; p: number }[]; colors: string[]; counted: (i: number) => boolean; bracketLabel: string }) {
  const total = bands.reduce((s, b) => s + b.p, 0) || 1;
  const first = bands.findIndex((_, i) => counted(i));
  const last = bands.length - 1 - [...bands].reverse().findIndex((_, i) => counted(bands.length - 1 - i));
  const left = (bands.slice(0, first).reduce((s, b) => s + b.p, 0) / total) * 100;
  const width = (bands.slice(first, last + 1).reduce((s, b) => s + b.p, 0) / total) * 100;
  const sum = bands.filter((_, i) => counted(i)).reduce((s, b) => s + b.p, 0);

  return (
    <div>
      <div className="flex items-end justify-between gap-3">
        <h3 className="text-[15px] font-bold">{title}</h3>
        {first >= 0 && (
          <p className="text-right text-[13px] font-medium leading-tight text-muted">
            {bracketLabel}
            <span className="cond ml-2 align-[-0.12em] text-[30px] font-extrabold leading-none text-ink">{percent(sum)}</span>
          </p>
        )}
      </div>
      {first >= 0 && (
        <div className="relative mt-2 h-2.5" aria-hidden>
          <div className="absolute bottom-0 h-2 rounded-t-[4px] border-x-2 border-t-2 border-ink" style={{ left: `${left}%`, width: `max(4px, calc(${width}% - 2px))` }} />
        </div>
      )}
      <div className="mt-1 flex h-7 gap-[2px] overflow-hidden rounded-[8px]" role="img" aria-label={bands.map((b) => `${b.label} ${percent(b.p)}`).join(", ")}>
        {bands.map((b, i) => (
          <div key={b.key} title={`${b.label}: ${percent(b.p)}`} className="h-full transition-[width] duration-500 ease-out" style={{ width: `${(b.p / total) * 100}%`, minWidth: b.p > 0 ? 2 : 0, background: colors[i] }} />
        ))}
      </div>
      <ul className="mt-3.5 grid grid-cols-1 gap-x-8 gap-y-1.5 sm:grid-cols-2">
        {bands.map((b, i) => (
          <li key={b.key} className="flex items-center gap-2.5 text-[14px]">
            <span className="h-3 w-3 shrink-0 rounded-[3px]" style={{ background: colors[i] }} aria-hidden />
            <span className={cx("flex-1", counted(i) ? "font-semibold text-ink" : "text-muted")}>{b.label}</span>
            <span className={cx("tabular", counted(i) ? "font-bold text-ink" : "text-muted")}>{percent(b.p)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Outcome({ d, bar }: { d: Distributions; bar: Policy }) {
  const start = TARGET_START[bar.target];
  const end = TIMELINE_END[String(bar.timeline_years) as "null" | "8" | "5"];
  return (
    <section aria-labelledby="outcome">
      <SectionTitle id="outcome">How it could end</SectionTitle>
      <Card className="space-y-8 p-5 sm:p-6">
        <Stacked
          title="Outcome"
          bands={OUTCOME_BANDS.map((b) => ({ key: b, label: OUTCOME_LABEL[b], p: d.outcome[b] }))}
          colors={["var(--viz-o1)", "var(--viz-o2)", "var(--viz-o3)", "var(--viz-o4)", "var(--viz-o5)"]}
          counted={(i) => i >= start}
          bracketLabel={`${{ "$50M": "$50M+", "$500M": "$500M+", "$1B": "$1B+" }[bar.target]}`}
        />
        <Stacked
          title="Years to get there"
          bands={YEARS_BANDS.map((b) => ({ key: b, label: YEARS_LABEL[b], p: d.years[b] }))}
          colors={["var(--viz-y1)", "var(--viz-y2)", "var(--viz-y3)"]}
          counted={(i) => i < end}
          bracketLabel={bar.timeline_years ? `Within ${bar.timeline_years} years` : "Any time"}
        />
      </Card>
    </section>
  );
}
