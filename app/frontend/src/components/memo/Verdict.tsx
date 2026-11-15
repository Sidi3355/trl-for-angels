"use client";

// The verdict slab: the decision as a block of colour, the chance in huge condensed figures, and a
// to-scale gauge against the investor's thresholds. The stub under the tear line is the bar itself.
import { useApp } from "@/components/AppState";
import { BarSummary } from "@/components/BarSheet";
import { IconSliders } from "@/components/icons";
import { SLAB, VerdictIcon, cx, useCountTo } from "@/components/ui";
import { DECISION_COPY, chanceOf, percent } from "@/lib/format";
import type { Verdict as V } from "@/lib/types";

function niceMax(x: number): number {
  for (const m of [0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1]) if (x <= m) return m;
  return 1;
}

/**
 * A to-scale track drawn in the slab's own ink: a hatched pass zone, a tinted escalate zone, a solid
 * advance zone, the founder's marker (and the starting point during a what-if).
 */
export function Gauge({ prob, advance, pass, baseline }: { prob: number; advance: number | null; pass: number | null; baseline?: number }) {
  const max = niceMax(Math.max(prob, baseline ?? 0, advance ?? 0, pass ?? 0) * 1.3 || 0.1);
  const x = (v: number) => Math.min(100, Math.max(0, (v / max) * 100));
  const p = pass ?? 0;
  const a = advance ?? max;
  const zones = [
    { key: "pass", from: 0, to: p, fill: "hatch opacity-55", label: "Pass" },
    { key: "escalate", from: p, to: a, fill: "bg-current opacity-30", label: "Look closer" },
    { key: "advance", from: a, to: max, fill: "bg-current opacity-90", label: "Meet" },
  ].filter((z) => z.to > z.from);
  const ticks = [pass, advance].filter((t): t is number => t !== null && t > 0 && t < max);
  const sameTick = ticks.length === 2 && percent(ticks[0]) === percent(ticks[1]);

  return (
    <div className="px-[11px]" role="img" aria-label={`Chance ${percent(prob)}. Pass below ${percent(pass)}, meet from ${percent(advance)}.`}>
      <div className="relative h-[18px]">
        <div className="absolute inset-0 flex gap-[3px]">
          {zones.map((z, i) => (
            <div key={z.key} className={cx("h-full", z.fill, i === 0 && "rounded-l-[5px]", i === zones.length - 1 && "rounded-r-[5px]")} style={{ width: `${x(z.to) - x(z.from)}%` }} />
          ))}
        </div>
        {baseline !== undefined && (
          <span className="absolute top-1/2 h-[18px] w-[18px] -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-dashed border-current bg-[var(--slab)]" style={{ left: `${x(baseline)}%` }} aria-hidden />
        )}
        <span
          className="absolute top-1/2 h-[32px] w-[7px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-current shadow-[0_0_0_3px_var(--slab)] transition-[left] duration-700 ease-[cubic-bezier(0.2,0.9,0.2,1)]"
          style={{ left: `${x(prob)}%` }}
          aria-hidden
        />
      </div>
      <div className="tabular relative mt-2.5 h-4 text-[11.5px] font-semibold opacity-75" aria-hidden>
        <span className="absolute left-0">0%</span>
        {ticks.map((t, i) =>
          sameTick && i === 1 ? null : (
            <span key={i} className="absolute -translate-x-1/2" style={{ left: `${x(t)}%` }}>
              {percent(t)}
            </span>
          ),
        )}
        <span className="absolute right-0">{percent(max)}</span>
      </div>
      <div className="eyebrow relative mt-1 h-4" aria-hidden>
        {zones.map((z) =>
          x(z.to) - x(z.from) >= 19 ? (
            <span key={z.key} className="absolute -translate-x-1/2 whitespace-nowrap" style={{ left: `${(x(z.from) + x(z.to)) / 2}%` }}>
              {z.label}
            </span>
          ) : null,
        )}
      </div>
    </div>
  );
}

export function VerdictCard({ verdict, baseline, whatIf, loading, onReset }: { verdict: V; baseline: V; whatIf: boolean; loading: boolean; onReset: () => void }) {
  const { bar, openBarSheet } = useApp();
  const copy = DECISION_COPY[verdict.decision];
  const pol = verdict.policy;
  // No validation founder reached this target and timeline (e.g. $1B+ within 5 years), so there are no thresholds.
  const noBar = pol.advance_threshold === null && pol.pass_threshold === null;
  const changed = whatIf && baseline.probability !== verdict.probability;
  const shown = useCountTo(verdict.probability);
  const figure = percent(shown).replace("%", "");

  return (
    <div
      className={cx("slab overflow-hidden rounded-[30px] transition-[background-color,color,opacity] duration-500", SLAB[verdict.decision], loading && "opacity-80")}
      style={{ "--slab": `var(--slab-${verdict.decision})` } as React.CSSProperties}
    >
      <div className="px-6 pb-6 pt-5 sm:px-7 sm:pt-6">
        <div className="flex items-center justify-between gap-3">
          <p className="eyebrow">{whatIf ? "What-if verdict" : "Verdict"}</p>
          {whatIf ? (
            <button type="button" onClick={onReset} className="-my-1 rounded-full border-[1.5px] border-current px-3 py-1 text-[13px] font-bold transition-opacity hover:opacity-70">
              Reset
            </button>
          ) : (
            <span className="flex h-8 w-8 items-center justify-center rounded-full border-[1.5px] border-current">
              <VerdictIcon decision={verdict.decision} size={16} />
            </span>
          )}
        </div>

        <p className="mt-2 text-[50px] font-black leading-[0.9] tracking-[-0.05em] sm:text-[58px]">{copy.title}</p>
        <p className="mt-2.5 text-[15.5px] font-medium leading-snug opacity-85">
          {noBar ? "No bar for this target and timeline: too few founders got there to judge. Try a longer timeline." : copy.line}
        </p>

        <div className="mt-6 flex items-end gap-4 sm:mt-7">
          <p className="cond text-[136px] font-black leading-[0.74] tracking-[-0.02em] sm:text-[150px]">
            {verdict.probability_is_estimate && <span className="mr-1 align-[0.28em] text-[0.36em] font-bold opacity-70">≈</span>}
            {figure}
            <span className="text-[0.5em]">%</span>
          </p>
          <p className="min-w-0 pb-1 text-[15px] font-semibold leading-tight">
            chance of
            <br />
            {chanceOf(pol.target, pol.timeline_years)}
            {changed && (
              <span className="tabular mt-1.5 block text-[13.5px] font-medium opacity-75">
                was <span className="line-through">{percent(baseline.probability)}</span>
              </span>
            )}
          </p>
        </div>

        <div className="mt-7 sm:mt-8">
          <Gauge prob={verdict.probability} advance={pol.advance_threshold} pass={pol.pass_threshold} baseline={changed ? baseline.probability : undefined} />
        </div>

        {verdict.filters_failed.length > 0 && (
          <p className="mt-5 rounded-[12px] border-[1.5px] border-current px-3 py-2 text-[13.5px] font-semibold">
            Outside your filters: {verdict.filters_failed.map((f) => (f === "repeat_founder" ? "founded before" : f === "sectors" ? "sector" : f)).join(", ")}.
          </p>
        )}
      </div>

      {/* tear line, then the stub: the bar this verdict was judged against */}
      <div className="relative" aria-hidden>
        <div className="mx-6 border-t-2 border-dashed border-current opacity-35" />
        <span className="absolute -left-[11px] top-1/2 h-[22px] w-[22px] -translate-y-1/2 rounded-full bg-bg" />
        <span className="absolute -right-[11px] top-1/2 h-[22px] w-[22px] -translate-y-1/2 rounded-full bg-bg" />
      </div>
      <button type="button" onClick={openBarSheet} className="group flex w-full items-center gap-3 px-6 py-4 text-left sm:px-7">
        <span className="min-w-0 flex-1">
          <span className="eyebrow block opacity-75">Your bar</span>
          <span className="mt-1 block truncate text-[15px] font-bold">
            <BarSummary bar={bar} />
          </span>
        </span>
        <span className="flex h-9 items-center gap-1.5 rounded-full border-[1.5px] border-current px-3.5 text-[13.5px] font-bold transition-colors group-hover:bg-current/10">
          <IconSliders size={15} strokeWidth={2.2} /> Change
        </span>
      </button>
    </div>
  );
}
