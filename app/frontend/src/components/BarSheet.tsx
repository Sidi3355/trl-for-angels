"use client";

// "Your bar": target, timeline, risk appetite and filters, with a plain reading of what the
// setting means on validation founders. Changes apply instantly everywhere; nothing is re-scored.
import { useState } from "react";

import { useApp } from "@/components/AppState";
import { IconChevronDown } from "@/components/icons";
import { Button, Segmented, Sheet, Tag, cx } from "@/components/ui";
import { activeFilterCount } from "@/lib/bar";
import { percent } from "@/lib/format";
import { DEFAULT_POLICY, resolve, tableFor, type Policy } from "@/lib/policy";
import type { Filters, Thresholds } from "@/lib/types";

type Tri = "any" | "yes" | "no";
const triOf = (v: boolean | null | undefined): Tri => (v === true ? "yes" : v === false ? "no" : "any");
const boolOf = (t: Tri): boolean | null => (t === "yes" ? true : t === "no" ? false : null);

function oneIn(p: number | null): string {
  if (p === null || p <= 0) return "";
  if (p >= 0.5) return `${Math.round(p * 10)} in 10`;
  return `about 1 in ${Math.max(2, Math.round(1 / p))}`;
}

export function BarSummary({ bar }: { bar: Policy }) {
  const t = { "$50M": "$50M+", "$500M": "$500M+", "$1B": "$1B+" }[bar.target];
  const h = bar.timeline_years ? `in ${bar.timeline_years} yrs` : "any time";
  const r = { cautious: "cautious", balanced: "balanced", bold: "bold" }[bar.risk];
  const n = activeFilterCount(bar);
  return (
    <>
      {t} · {h} · {r}
      {n > 0 && ` · ${n} filter${n > 1 ? "s" : ""}`}
    </>
  );
}

export function BarSheet() {
  const { bar, setBar, thresholds, barSheetOpen, closeBarSheet } = useApp();
  if (!barSheetOpen) return null;
  return <BarSheetBody bar={bar} setBar={setBar} thresholdsReady={thresholds} onClose={closeBarSheet} />;
}

function BarSheetBody({ bar, setBar, thresholdsReady, onClose }: { bar: Policy; setBar: (p: Policy) => void; thresholdsReady: Thresholds | null; onClose: () => void }) {
  const [showFilters, setShowFilters] = useState(activeFilterCount(bar) > 0);
  const f = bar.filters;
  const setFilter = (patch: Partial<Filters>) => setBar({ ...bar, filters: { ...f, ...patch } });
  const target = { "$50M": "$50M+", "$500M": "$500M+", "$1B": "$1B+" }[bar.target];
  const horizon = bar.timeline_years ? ` within ${bar.timeline_years} years` : "";

  let readout: React.ReactNode = <p className="text-[14px] text-muted">Loading the validation table…</p>;
  if (thresholdsReady) {
    const r = resolve(thresholdsReady, bar);
    const table = tableFor(thresholdsReady, bar.target, bar.timeline_years);
    readout = (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-5">
          <div>
            <p className="cond text-[56px] font-black leading-[0.82]">{percent(r.expected_precision)}</p>
            <p className="mt-2 text-[13px] leading-snug text-ink-2">of founders you advance reach {target}{horizon} ({oneIn(r.expected_precision)})</p>
          </div>
          <div>
            <p className="cond text-[56px] font-black leading-[0.82]">{percent(r.expected_recall)}</p>
            <p className="mt-2 text-[13px] leading-snug text-ink-2">of the founders who reach it get advanced</p>
          </div>
        </div>
        <p className="border-t border-line-strong pt-3 text-[13px] leading-snug text-muted">
          For comparison, {percent(table.base_rate)} of all founders reach {target}
          {horizon}. Auto-pass skips {percent(r.missed_winners_if_pass)} of eventual winners.
          {r.sparse && (
            <>
              {" "}
              <Tag tone="warn">Rough</Tag> only {r.n_positive} test founders reached this target, so these rates are noisy.
            </>
          )}
        </p>
        <p className="text-[12px] text-faint">
          Measured on {table.n} validation founders{thresholdsReady.mock ? " (example data until the real model is trained)" : ""}.
        </p>
      </div>
    );
  }

  return (
    <Sheet
      open
      onClose={onClose}
      title="Your bar"
      footer={
        <div className="flex items-center gap-3">
          <Button variant="secondary" size="lg" onClick={() => setBar(DEFAULT_POLICY)}>
            Reset
          </Button>
          <Button full size="lg" onClick={onClose}>
            Done
          </Button>
        </div>
      }
    >
      <p className="text-[15px] leading-snug text-muted">What counts as a win for you, and how picky to be. Applies to every founder, instantly.</p>

      <div className="mt-5 space-y-5">
        <div>
          <p className="mb-2 text-[15px] font-bold tracking-[-0.01em]">Target outcome</p>
          <Segmented
            label="Target outcome"
            size="lg"
            value={bar.target}
            onChange={(target) => setBar({ ...bar, target })}
            options={[
              { value: "$50M", label: "$50M+", hint: "Solid exit" },
              { value: "$500M", label: "$500M+", hint: "Big outcome" },
              { value: "$1B", label: "$1B+", hint: "Unicorn" },
            ]}
          />
        </div>
        <div>
          <p className="mb-2 text-[15px] font-bold tracking-[-0.01em]">Within</p>
          <Segmented
            label="Timeline"
            value={bar.timeline_years}
            onChange={(timeline_years) => setBar({ ...bar, timeline_years })}
            options={[
              { value: null, label: "Any time" },
              { value: 8, label: "8 years" },
              { value: 5, label: "5 years" },
            ]}
          />
          {bar.timeline_years !== null && <p className="mt-1.5 text-[12.5px] text-muted">With a timeline the chance is an estimate: it treats outcome size and timing as independent.</p>}
        </div>
        <div>
          <p className="mb-2 text-[15px] font-bold tracking-[-0.01em]">Risk appetite</p>
          <Segmented
            label="Risk appetite"
            size="lg"
            value={bar.risk}
            onChange={(risk) => setBar({ ...bar, risk })}
            options={[
              { value: "cautious", label: "Cautious", hint: "Fewer, surer" },
              { value: "balanced", label: "Balanced", hint: "In between" },
              { value: "bold", label: "Bold", hint: "More, riskier" },
            ]}
          />
        </div>

        <div className="rounded-[20px] bg-surface-2 p-5 ring-1 ring-inset ring-line">
          <p className="eyebrow mb-4 text-muted">What this bar means</p>
          {readout}
        </div>

        <div className="border-t border-line pt-4">
          <button type="button" onClick={() => setShowFilters((v) => !v)} aria-expanded={showFilters} className="flex w-full items-center justify-between text-left">
            <span>
              <span className="block text-[15px] font-bold tracking-[-0.01em]">
                Hard filters{activeFilterCount(bar) > 0 && <span className="ml-1.5 rounded-full bg-accent px-1.5 py-[1px] text-[11px] text-accent-ink">{activeFilterCount(bar)}</span>}
              </span>
              <span className="block text-[13px] text-muted">Founders outside them are flagged, whatever their score.</span>
            </span>
            <IconChevronDown size={18} className={cx("text-muted transition-transform", showFilters && "rotate-180")} />
          </button>
          {showFilters && (
            <div className="mt-4 space-y-4">
              <div>
                <p className="mb-1.5 text-[13.5px] font-medium text-ink-2">Team</p>
                <Segmented label="Team" value={f.team ?? "any"} onChange={(v) => setFilter({ team: v === "any" ? null : (v as "solo" | "team") })} options={[{ value: "any", label: "Any" }, { value: "solo", label: "Solo" }, { value: "team", label: "Team" }]} />
              </div>
              <div>
                <p className="mb-1.5 text-[13.5px] font-medium text-ink-2">Technical founder</p>
                <Segmented label="Technical founder" value={triOf(f.technical)} onChange={(v) => setFilter({ technical: boolOf(v) })} options={[{ value: "any", label: "Any" }, { value: "yes", label: "Yes" }, { value: "no", label: "No" }]} />
              </div>
              <div>
                <p className="mb-1.5 text-[13.5px] font-medium text-ink-2">Has founded before</p>
                <Segmented label="Has founded before" value={triOf(f.repeat_founder)} onChange={(v) => setFilter({ repeat_founder: boolOf(v) })} options={[{ value: "any", label: "Any" }, { value: "yes", label: "Repeat" }, { value: "no", label: "First-time" }]} />
              </div>
              <div>
                <label htmlFor="bar-sectors" className="mb-1.5 block text-[13px] text-muted">
                  Sectors (comma separated)
                </label>
                <input
                  id="bar-sectors"
                  defaultValue={(f.sectors ?? []).join(", ")}
                  onBlur={(e) => {
                    const sectors = e.target.value.split(",").map((s) => s.trim()).filter(Boolean);
                    setFilter({ sectors: sectors.length ? sectors : null });
                  }}
                  placeholder="e.g. fintech, climate"
                  className="h-12 w-full rounded-[12px] border border-line-strong bg-surface px-3.5 outline-none transition-colors placeholder:text-faint focus:border-ink"
                />
              </div>
              <p className="text-[12.5px] text-muted">A founder whose value is unknown fails an active filter.</p>
            </div>
          )}
        </div>
      </div>
    </Sheet>
  );
}
