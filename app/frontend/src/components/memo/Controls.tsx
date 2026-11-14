// Investor controls. Every change is computed on the phone from the memo's distributions and the val
// thresholds table: no network call, so it is instant.
import { useState } from "react";

import { ChevronDown, Segmented } from "@/components/ui";
import { RISK_HINTS, RISK_LABELS, TARGET_LABELS, timelineLabel } from "@/lib/format";
import { RISKS, TARGETS, TIMELINES, type Policy } from "@/lib/policy";
import type { Facets, Filters } from "@/lib/types";

type Tri = "any" | "yes" | "no";
const triOf = (v: boolean | null | undefined): Tri => (v === true ? "yes" : v === false ? "no" : "any");
const boolOf = (t: Tri): boolean | null => (t === "yes" ? true : t === "no" ? false : null);

export function Controls({ policy, onChange, facets }: { policy: Policy; onChange: (p: Policy) => void; facets: Facets }) {
  const [showFilters, setShowFilters] = useState(false);
  const f = policy.filters;
  const setFilter = (patch: Partial<Filters>) => onChange({ ...policy, filters: { ...f, ...patch } });
  const activeFilters = [f.sectors?.length, f.team, f.technical !== null && f.technical !== undefined, f.repeat_founder !== null && f.repeat_founder !== undefined].filter(Boolean).length;

  return (
    <div className="space-y-4 rounded-2xl bg-card p-4">
      <div>
        <div className="mb-1.5 text-[13px] text-muted">Target outcome</div>
        <Segmented label="Target outcome" value={policy.target} onChange={(target) => onChange({ ...policy, target })} options={TARGETS.map((t) => ({ value: t, label: TARGET_LABELS[t] }))} />
      </div>
      <div>
        <div className="mb-1.5 text-[13px] text-muted">Within</div>
        <Segmented label="Timeline" value={policy.timeline_years} onChange={(timeline_years) => onChange({ ...policy, timeline_years })} options={TIMELINES.map((t) => ({ value: t, label: timelineLabel(t) }))} />
      </div>
      <div>
        <div className="mb-1.5 text-[13px] text-muted">Risk appetite</div>
        <Segmented label="Risk appetite" value={policy.risk} onChange={(risk) => onChange({ ...policy, risk })} options={RISKS.map((r) => ({ value: r, label: RISK_LABELS[r] }))} />
        <p className="mt-1.5 text-[13px] text-muted">{RISK_HINTS[policy.risk]}</p>
      </div>

      <div className="border-t border-line pt-3">
        <button type="button" onClick={() => setShowFilters((v) => !v)} aria-expanded={showFilters} className="flex w-full items-center justify-between text-[15px] active:opacity-60">
          <span>
            Filters{activeFilters ? <span className="ml-1.5 rounded-full bg-accent px-1.5 text-[12px] font-semibold text-accent-ink">{activeFilters}</span> : null}
          </span>
          <ChevronDown open={showFilters} />
        </button>
        {showFilters && (
          <div className="mt-3 space-y-3">
            <div>
              <div className="mb-1.5 text-[13px] text-muted">Team</div>
              <Segmented label="Team" value={f.team ?? "any"} onChange={(v) => setFilter({ team: v === "any" ? null : (v as "solo" | "team") })} options={[{ value: "any", label: "Any" }, { value: "solo", label: "Solo" }, { value: "team", label: "Team" }]} />
            </div>
            <div>
              <div className="mb-1.5 text-[13px] text-muted">Technical founder</div>
              <Segmented label="Technical founder" value={triOf(f.technical)} onChange={(v) => setFilter({ technical: boolOf(v) })} options={[{ value: "any", label: "Any" }, { value: "yes", label: "Yes" }, { value: "no", label: "No" }]} />
            </div>
            <div>
              <div className="mb-1.5 text-[13px] text-muted">Repeat founder</div>
              <Segmented label="Repeat founder" value={triOf(f.repeat_founder)} onChange={(v) => setFilter({ repeat_founder: boolOf(v) })} options={[{ value: "any", label: "Any" }, { value: "yes", label: "Yes" }, { value: "no", label: "First-time" }]} />
            </div>
            <div>
              <label className="mb-1.5 block text-[13px] text-muted" htmlFor="sectors">Sectors (comma separated)</label>
              <input
                id="sectors"
                defaultValue={(f.sectors ?? []).join(", ")}
                onBlur={(e) => {
                  const sectors = e.target.value.split(",").map((s) => s.trim()).filter(Boolean);
                  setFilter({ sectors: sectors.length ? sectors : null });
                }}
                placeholder={facets.sector ? `e.g. ${facets.sector}` : "e.g. fintech, climate"}
                className="w-full rounded-[9px] bg-card-2 px-3 py-2 outline-none ring-accent focus:ring-2"
              />
            </div>
            <p className="text-[13px] text-muted">Filters are hard rules. A founder whose value is unknown fails an active filter.</p>
          </div>
        )}
      </div>
    </div>
  );
}
