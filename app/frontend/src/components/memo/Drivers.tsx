// What moves this founder's score, ranked at the current controls, with what-if toggles.
// Ranking uses the flipped distributions the memo already carries; a toggle asks the backend to
// re-run the decider with the flips applied (no new research).
import { useMemo, useState } from "react";

import { Spinner, cx } from "@/components/ui";
import { percent, points } from "@/lib/format";
import { score, type Policy } from "@/lib/policy";
import type { Distributions, Driver } from "@/lib/types";

const show = (v: unknown) => (typeof v === "string" ? v : JSON.stringify(v));

export function Drivers({
  drivers,
  base,
  policy,
  flipped,
  onToggle,
  loading,
  supported,
}: {
  drivers: Driver[];
  base: Distributions;
  policy: Policy;
  flipped: Set<string>;
  onToggle: (d: Driver) => void;
  loading: boolean;
  supported: boolean;
}) {
  const [all, setAll] = useState(false);
  const ranked = useMemo(() => {
    const b = score(base, policy.target, policy.timeline_years);
    return drivers
      .map((d) => {
        const flippedScore = score(d.distributions, policy.target, policy.timeline_years);
        return { d, flippedScore, delta: flippedScore - b };
      })
      .sort((x, y) => Math.abs(y.delta) - Math.abs(x.delta));
  }, [drivers, base, policy.target, policy.timeline_years]);

  if (!drivers.length) return <p className="px-4 py-3 text-[15px] text-muted">No drivers for this memo.</p>;
  const visible = all ? ranked : ranked.slice(0, 5);

  return (
    <div>
      {visible.map(({ d, flippedScore, delta }) => {
        const on = flipped.has(d.id);
        const helps = delta < 0;
        const width = Math.min(100, Math.abs(delta) * 400);
        return (
          <div key={d.id} className="relative px-4 py-3 [&+&]:before:absolute [&+&]:before:left-4 [&+&]:before:right-0 [&+&]:before:top-0 [&+&]:before:h-px [&+&]:before:bg-line">
            <p className="text-[15px] leading-snug">{d.label}</p>
            <div className="mt-2 flex items-center justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 text-[13px] text-muted">
                  <span>
                    Now <strong className="font-semibold text-ink">{show(on ? d.flipped : d.current)}</strong>
                  </span>
                  <span aria-hidden>·</span>
                  <span className={helps ? "text-advance" : "text-danger"}>{helps ? "helps" : "holds back"}</span>
                </div>
                <div className="mt-1.5 flex items-center gap-2">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-card-2">
                    <div className={cx("h-full rounded-full", helps ? "bg-advance" : "bg-danger")} style={{ width: `${width}%` }} />
                  </div>
                  <span className="w-[86px] text-right text-[12px] tabular-nums text-muted">
                    if {show(d.flipped)}: {points(delta)}
                  </span>
                </div>
                <span className="sr-only">If it were {show(d.flipped)}, the chance would be {percent(flippedScore)}.</span>
              </div>
              {supported && (
                <button
                  type="button"
                  onClick={() => onToggle(d)}
                  disabled={loading}
                  aria-pressed={on}
                  className={cx(
                    "shrink-0 rounded-full px-3 py-1.5 text-[13px] font-medium disabled:opacity-60",
                    on ? "bg-accent text-accent-ink" : "bg-accent-soft text-accent active:opacity-60",
                  )}
                >
                  {on ? "Undo" : `Try ${show(d.flipped)}`}
                </button>
              )}
            </div>
          </div>
        );
      })}
      <div className="flex items-center justify-between border-t border-line px-4 py-2.5">
        {ranked.length > 5 ? (
          <button type="button" onClick={() => setAll((v) => !v)} className="text-[15px] text-accent active:opacity-60">
            {all ? "Show top 5" : `Show all ${ranked.length}`}
          </button>
        ) : (
          <span />
        )}
        {loading && (
          <span className="flex items-center gap-1.5 text-[13px] text-muted">
            <Spinner className="h-3.5 w-3.5" /> Re-scoring…
          </span>
        )}
      </div>
    </div>
  );
}
