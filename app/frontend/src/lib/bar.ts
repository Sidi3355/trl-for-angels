// "Your bar": the investor's target, timeline, risk appetite and filters, set once and applied to
// every memo and the Founders list. A preference, not founder data, so it lives in localStorage.

import { DEFAULT_POLICY, decide, filtersFailed, resolve, score, type Policy } from "./policy";
import type { Decision, Distributions, Facets, Thresholds } from "./types";

const KEY = "screener.bar";

export function loadBar(): Policy {
  try {
    const raw = JSON.parse(window.localStorage.getItem(KEY) ?? "null");
    if (!raw) return DEFAULT_POLICY;
    return {
      target: ["$50M", "$500M", "$1B"].includes(raw.target) ? raw.target : DEFAULT_POLICY.target,
      timeline_years: [null, 5, 8].includes(raw.timeline_years) ? raw.timeline_years : null,
      risk: ["cautious", "balanced", "bold"].includes(raw.risk) ? raw.risk : DEFAULT_POLICY.risk,
      filters: typeof raw.filters === "object" && raw.filters ? raw.filters : {},
    };
  } catch {
    return DEFAULT_POLICY;
  }
}

export function saveBar(p: Policy) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(p));
  } catch {
    // storage blocked: the bar resets next visit
  }
}

export interface QuickVerdict {
  decision: Decision;
  probability: number;
  estimate: boolean;
  filtersFailed: string[];
}

/** The verdict for one founder at a bar, from the same logic as policy.verdict (lib/policy.ts). */
export function quickVerdict(d: Distributions, facets: Facets, thresholds: Thresholds, bar: Policy): QuickVerdict {
  const r = resolve(thresholds, bar);
  const p = score(d, bar.target, bar.timeline_years);
  return {
    decision: decide(p, r.policy.advance_threshold, r.policy.pass_threshold),
    probability: p,
    estimate: bar.timeline_years !== null,
    filtersFailed: filtersFailed(facets, bar.filters),
  };
}

export function activeFilterCount(bar: Policy): number {
  const f = bar.filters;
  return [f.sectors?.length, f.team, f.technical !== null && f.technical !== undefined, f.repeat_founder !== null && f.repeat_founder !== undefined].filter(Boolean).length;
}
