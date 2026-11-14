"use client";

// The verdict at the investor's bar: decision, chance, a to-scale gauge against the thresholds.
import { useApp } from "@/components/AppState";
import { BarSummary } from "@/components/BarSheet";
import { IconSliders } from "@/components/icons";
import { Card, VerdictIcon, cx } from "@/components/ui";
import { DECISION_COPY, chanceOf, percent } from "@/lib/format";
import type { Verdict as V } from "@/lib/types";

const ICON_TILE = {
  advance: "bg-advance-soft text-advance",
  escalate: "bg-escalate-soft text-escalate",
  pass: "bg-pass-soft text-pass",
};

function niceMax(x: number): number {
  for (const m of [0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1]) if (x <= m) return m;
  return 1;
}

/** A to-scale track: pass zone, escalate zone, advance zone, the founder's marker (and the baseline in a what-if). */
export function Gauge({ prob, advance, pass, baseline }: { prob: number; advance: number | null; pass: number | null; baseline?: number }) {
  const max = niceMax(Math.max(prob, baseline ?? 0, advance ?? 0, pass ?? 0) * 1.3 || 0.1);
  const x = (v: number) => Math.min(100, Math.max(0, (v / max) * 100));
  const p = pass ?? 0;
  const a = advance ?? max;
  const zones = [
    { key: "pass", from: 0, to: p, fill: "bg-pass-fill/30", label: "Pass", text: "text-pass" },
    { key: "escalate", from: p, to: a, fill: "bg-escalate-fill/40", label: "Escalate", text: "text-escalate" },
    { key: "advance", from: a, to: max, fill: "bg-advance-fill/35", label: "Advance", text: "text-advance" },
  ].filter((z) => z.to > z.from);
  const ticks = [pass, advance].filter((t): t is number => t !== null && t > 0 && t < max);
  const sameTick = ticks.length === 2 && percent(ticks[0]) === percent(ticks[1]);

  return (
    <div className="mt-6" role="img" aria-label={`Chance ${percent(prob)}. Pass below ${percent(pass)}, advance from ${percent(advance)}.`}>
      <div className="relative flex h-3 gap-[2px]">
        {zones.map((z, i) => (
          <div key={z.key} className={cx("h-full", z.fill, i === 0 && "rounded-l-full", i === zones.length - 1 && "rounded-r-full")} style={{ width: `${x(z.to) - x(z.from)}%` }} />
        ))}
        {baseline !== undefined && (
          <span className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-dashed border-muted bg-surface" style={{ left: `${x(baseline)}%` }} aria-hidden />
        )}
        <span className="absolute top-1/2 h-[22px] w-[22px] -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-surface bg-ink shadow-md transition-[left] duration-500 ease-out" style={{ left: `${x(prob)}%` }} aria-hidden />
      </div>
      <div className="relative mt-2 h-4 text-[11.5px] tabular text-muted" aria-hidden>
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
      <div className="relative mt-1 h-4 text-[12px] font-semibold" aria-hidden>
        {zones.map((z) =>
          x(z.to) - x(z.from) >= 16 ? (
            <span key={z.key} className={cx("absolute -translate-x-1/2 whitespace-nowrap", z.text)} style={{ left: `${(x(z.from) + x(z.to)) / 2}%` }}>
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
  const changed = whatIf && baseline.probability !== verdict.probability;

  return (
    <Card className={cx("p-5 transition-opacity sm:p-6", loading && "opacity-70")}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className={cx("flex h-11 w-11 items-center justify-center rounded-2xl", ICON_TILE[verdict.decision])}>
            <VerdictIcon decision={verdict.decision} size={22} />
          </span>
          <div>
            <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-muted">{whatIf ? "What-if verdict" : "Verdict"}</p>
            <p className="font-display text-[30px] font-semibold leading-none tracking-[-0.02em]">{copy.title}</p>
          </div>
        </div>
        {whatIf && (
          <button type="button" onClick={onReset} className="rounded-full bg-accent-soft px-3 py-1.5 text-[13px] font-semibold text-accent hover:opacity-80">
            Reset
          </button>
        )}
      </div>
      <p className="mt-3 text-[15px] leading-snug text-ink-2">{copy.line}</p>

      <div className="mt-6 flex items-baseline gap-3">
        <span className="font-display text-[56px] font-semibold leading-[0.9] tracking-[-0.03em] tabular">
          {verdict.probability_is_estimate && <span className="text-[38px] text-muted">≈</span>}
          {percent(verdict.probability)}
        </span>
        {changed && (
          <span className="text-[17px] tabular text-muted">
            was <span className="line-through">{percent(baseline.probability)}</span>
          </span>
        )}
      </div>
      <p className="mt-2 text-[15px] text-muted">chance of {chanceOf(pol.target, pol.timeline_years)}</p>

      <Gauge prob={verdict.probability} advance={pol.advance_threshold} pass={pol.pass_threshold} baseline={changed ? baseline.probability : undefined} />

      {verdict.filters_failed.length > 0 && (
        <p className="mt-4 rounded-xl bg-warn-soft px-3 py-2 text-[13.5px] text-warn">
          Outside your filters: {verdict.filters_failed.map((f) => (f === "repeat_founder" ? "founded before" : f === "sectors" ? "sector" : f)).join(", ")}.
        </p>
      )}

      <button type="button" onClick={openBarSheet} className="mt-5 flex w-full items-center gap-3 rounded-2xl bg-surface-2 px-4 py-3 text-left transition-colors hover:bg-surface-3">
        <IconSliders size={18} className="shrink-0 text-muted" />
        <span className="min-w-0 flex-1">
          <span className="block text-[12px] font-medium text-muted">Your bar</span>
          <span className="block truncate text-[14px] font-semibold">
            <BarSummary bar={bar} />
          </span>
        </span>
        <span className="text-[14px] font-medium text-accent">Change</span>
      </button>
    </Card>
  );
}
