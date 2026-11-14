"use client";

// What moves this founder's chance, ranked at the investor's bar. Each factor's bar is the change in
// chance its current answer makes (diverging: blue raises it, red lowers it). Tapping a factor runs a
// what-if with it flipped (the decision model re-scores; nothing is researched again).
import { useMemo, useState } from "react";

import { IconFlip } from "@/components/icons";
import { Card, SectionTitle, Spinner, Tag, cx } from "@/components/ui";
import { answerLabel } from "@/lib/format";
import { score, type Policy } from "@/lib/policy";
import type { Distributions, Driver } from "@/lib/types";

export function Factors({
  drivers,
  base,
  bar,
  flipped,
  onToggle,
  loading,
  enabled,
  error,
}: {
  drivers: Driver[];
  base: Distributions;
  bar: Policy;
  flipped: Set<string>;
  onToggle: (d: Driver) => void;
  loading: boolean;
  enabled: boolean;
  error: string | null;
}) {
  const [all, setAll] = useState(false);
  const ranked = useMemo(() => {
    const b = score(base, bar.target, bar.timeline_years);
    return drivers
      .map((d) => ({ d, impact: b - score(d.distributions, bar.target, bar.timeline_years) }))
      .sort((x, y) => Math.abs(y.impact) - Math.abs(x.impact));
  }, [drivers, base, bar.target, bar.timeline_years]);
  if (!ranked.length) return null;
  const maxImpact = Math.max(...ranked.map((r) => Math.abs(r.impact)), 0.01);
  const visible = all ? ranked : ranked.slice(0, 5);

  return (
    <section aria-labelledby="factors">
      <SectionTitle id="factors" action={loading ? <span className="flex items-center gap-1.5 text-[13px] text-muted"><Spinner size={13} /> Re-scoring</span> : undefined}>
        What moves the score
      </SectionTitle>
      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-line px-4 py-2.5 text-[12.5px] text-muted">
          <span>{enabled ? "Tap a factor to see the verdict if it were the other way." : "Ranked by how much each answer moves the chance."}</span>
          <span className="flex items-center gap-3">
            <span className="flex items-center gap-1.5"><span className="h-2 w-3 rounded-sm bg-[var(--viz-up)]" />Raises it</span>
            <span className="flex items-center gap-1.5"><span className="h-2 w-3 rounded-sm bg-[var(--viz-down)]" />Lowers it</span>
          </span>
        </div>
        <ul>
          {visible.map(({ d, impact: own }) => {
            const on = flipped.has(d.id);
            // A flipped row shows its what-if answer, so its bar is that answer's effect: the opposite.
            const impact = on ? -own : own;
            const w = (Math.abs(impact) / maxImpact) * 50;
            const pts = Math.round(impact * 100);
            const Row = enabled ? "button" : "div";
            return (
              <li key={d.id} className="border-t border-line first:border-t-0">
                <Row
                  {...(enabled ? { type: "button" as const, onClick: () => onToggle(d), "aria-pressed": on, disabled: loading } : {})}
                  className={cx("block w-full px-4 py-3.5 text-left transition-colors", enabled && "hover:bg-surface-2 disabled:cursor-wait", on && "bg-accent-soft/60")}
                >
                  <p className="text-[15px] leading-snug">{d.label}</p>
                  <div className="mt-2.5 flex items-center gap-3">
                    <span className={cx("inline-flex min-w-[3.25rem] items-center justify-center gap-1 rounded-md px-1.5 py-0.5 text-[12.5px] font-semibold", on ? "bg-accent text-accent-ink" : "bg-surface-2 text-ink-2")}>
                      {on && <IconFlip size={12} strokeWidth={2.4} />}
                      {answerLabel(on ? d.flipped : d.current)}
                    </span>
                    <div className="relative h-2 flex-1" aria-hidden>
                      <span className="absolute inset-y-[-3px] left-1/2 w-px bg-line-strong" />
                      <span
                        className="absolute inset-y-0 rounded-full"
                        style={{
                          background: impact >= 0 ? "var(--viz-up)" : "var(--viz-down)",
                          width: `${Math.max(w, 1.5)}%`,
                          left: impact >= 0 ? "50%" : `${50 - Math.max(w, 1.5)}%`,
                        }}
                      />
                    </div>
                    <span className="w-14 text-right text-[13px] font-semibold tabular text-ink-2">
                      {pts > 0 ? "+" : pts < 0 ? "−" : "±"}
                      {Math.abs(pts)} pts
                    </span>
                  </div>
                  {on && (
                    <p className="mt-2 text-[12.5px] text-accent">
                      <Tag tone="accent">What-if</Tag> scoring as if the answer were {answerLabel(d.flipped).toLowerCase()}
                    </p>
                  )}
                </Row>
              </li>
            );
          })}
        </ul>
        {ranked.length > 5 && (
          <button type="button" onClick={() => setAll((v) => !v)} className="w-full border-t border-line px-4 py-3 text-left text-[14px] font-medium text-accent hover:bg-surface-2">
            {all ? "Show the top 5" : `Show all ${ranked.length} factors`}
          </button>
        )}
      </Card>
      {error && <p className="mt-2 px-1 text-[13px] text-danger">{error}</p>}
      <p className="mt-2 px-1 text-[12.5px] leading-snug text-faint">Points are the change in chance at your bar if that one answer were the other way, with everything else held fixed.</p>
    </section>
  );
}
