"use client";

// What moves this founder's chance, ranked at the investor's bar. Each factor's bar is the change in
// chance its current answer makes (diverging: blue raises it, red lowers it). Tapping a factor runs a
// what-if with it flipped (the decision model re-scores; nothing is researched again).
import { useMemo, useState } from "react";

import { IconFlip } from "@/components/icons";
import { SectionTitle, Spinner, Tag, cx, linkClass } from "@/components/ui";
import { answerLabel } from "@/lib/format";
import { score, type Policy } from "@/lib/policy";
import type { Distributions, Driver } from "@/lib/types";

export function Factors({
  drivers,
  status,
  total,
  base,
  bar,
  flipped,
  onToggle,
  loading,
  enabled,
  error,
}: {
  drivers: Driver[];
  status: "complete" | "pending" | "failed";
  total: number | null;
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
  if (!ranked.length && status === "complete") return null;
  const maxImpact = Math.max(...ranked.map((r) => Math.abs(r.impact)), 0.01);
  const visible = all ? ranked : ranked.slice(0, 5);

  return (
    <section aria-labelledby="factors">
      <SectionTitle
        id="factors"
        action={loading ? <span className="flex items-center gap-1.5 text-[13px] font-medium text-muted"><Spinner size={13} /> Re-scoring</span> : undefined}
        note={enabled ? "Tap one to see the verdict if it were the other way." : "Ranked by how much each answer moves the chance."}
      >
        What moves the score
      </SectionTitle>
      {status === "pending" && (
        <p role="status" className="mb-3 flex items-start gap-2 rounded-[14px] bg-accent-soft px-3.5 py-3 text-[13.5px] leading-snug text-ink-2">
          <Spinner size={14} className="mt-[2px] shrink-0" />
          <span>
            Checking each answer the other way round{total ? `: ${drivers.length} of ${total} done` : ""}. The model takes a few seconds per question, so this fills in over the next
            few minutes. The verdict above is already final.
          </span>
        </p>
      )}
      {status === "failed" && (
        <p className="mb-3 rounded-[14px] bg-surface-2 px-3.5 py-3 text-[13.5px] leading-snug text-ink-2">
          The model stopped answering{drivers.length ? ` after ${drivers.length} of ${total ?? drivers.length} questions` : ""}, so this list is incomplete. The verdict above isn&apos;t affected.
        </p>
      )}
      <div className="mb-1 flex items-center gap-4 text-[12.5px] font-medium text-muted">
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-3.5 rounded-[3px] bg-[var(--viz-down)]" />Lowers the chance</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-3.5 rounded-[3px] bg-[var(--viz-up)]" />Raises it</span>
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
            <li key={d.id} className="border-b border-line">
              <Row
                {...(enabled ? { type: "button" as const, onClick: () => onToggle(d), "aria-pressed": on, disabled: loading } : {})}
                className={cx(
                  "group -mx-3 block w-[calc(100%+24px)] rounded-[14px] px-3 py-4 text-left transition-colors duration-150",
                  enabled && "hover:bg-surface disabled:cursor-wait",
                  on && "bg-surface shadow-[inset_0_0_0_2px_var(--ink)]",
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <p className="text-[15.5px] font-medium leading-snug">{d.label}</p>
                  <span className="cond shrink-0 text-[26px] font-extrabold leading-[0.95]">
                    {pts > 0 ? "+" : pts < 0 ? "−" : "±"}
                    {Math.abs(pts)}
                    <span className="ml-0.5 text-[0.55em] font-bold text-muted">pts</span>
                  </span>
                </div>
                <div className="mt-3 flex items-center gap-3">
                  <span className={cx("inline-flex h-6 min-w-[3rem] items-center justify-center gap-1 rounded-full px-2.5 text-[12.5px] font-bold", on ? "bg-ink text-bg" : "bg-surface-3 text-ink-2")}>
                    {on && <IconFlip size={12} strokeWidth={2.6} />}
                    {answerLabel(on ? d.flipped : d.current)}
                  </span>
                  <div className="relative h-2.5 flex-1" aria-hidden>
                    <span className="absolute inset-0 rounded-full bg-[var(--viz-track)]" />
                    <span className="absolute inset-y-[-4px] left-1/2 w-[2px] -translate-x-1/2 rounded-full bg-ink" />
                    <span
                      className="absolute inset-y-0 transition-[width,left] duration-500 ease-out"
                      style={{
                        background: impact >= 0 ? "var(--viz-up)" : "var(--viz-down)",
                        width: `${Math.max(w, 1.5)}%`,
                        left: impact >= 0 ? "50%" : `${50 - Math.max(w, 1.5)}%`,
                        borderRadius: impact >= 0 ? "0 99px 99px 0" : "99px 0 0 99px",
                      }}
                    />
                  </div>
                </div>
                {on && (
                  <p className="mt-2.5 flex items-center gap-1.5 text-[12.5px] font-medium text-ink-2">
                    <Tag tone="accent">What-if</Tag> scoring as if the answer were {answerLabel(d.flipped).toLowerCase()}
                  </p>
                )}
              </Row>
            </li>
          );
        })}
      </ul>
      {ranked.length > 5 && (
        <button type="button" onClick={() => setAll((v) => !v)} className={cx(linkClass, "mt-4 text-[14px]")}>
          {all ? "Show the top 5" : `Show all ${ranked.length} factors`}
        </button>
      )}
      {error && <p className="mt-3 text-[13px] font-medium text-danger">{error}</p>}
      <p className="mt-3 text-[12.5px] leading-snug text-faint">Points are the change in chance at your bar if that one answer were the other way, with everything else held fixed.</p>
    </section>
  );
}
