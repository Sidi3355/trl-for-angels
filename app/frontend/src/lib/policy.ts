// Investor controls, computed client-side: a line-for-line port of app/backend/screener/policy.py.
// Any change there must be mirrored here; policy.test.ts checks this port reproduces every mock verdict.
//
//   P(outcome >= target) = sum of outcome bands at or above the target
//   P(within timeline)   = P('under 5') for 5 years, + P('5-8') for 8, 1 for any timeline
//   score                = their product (an estimate when a timeline is set: assumes independence)
//   advance if score >= advance threshold; pass if score < pass threshold; escalate otherwise.

import {
  OUTCOME_BANDS,
  type Decision,
  type Distributions,
  type Facets,
  type FieldValues,
  type Filters,
  type PolicyRequest,
  type PolicyUsed,
  type Risk,
  type Target,
  type ThresholdRow,
  type ThresholdTable,
  type Thresholds,
  type Timeline,
  type Verdict,
  type YearsBand,
} from "./types";

export const TARGETS: Target[] = ["$50M", "$500M", "$1B"];
export const TIMELINES: Timeline[] = [null, 8, 5];
export const RISKS: Risk[] = ["cautious", "balanced", "bold"];

const TARGET_FIRST_BAND = { "$50M": "$50M-$500M", "$500M": "$500M-$1B", "$1B": "over $1B" } as const;
const TIMELINE_BANDS: Record<string, YearsBand[]> = {
  null: ["under 5", "5-8", "over 8"],
  8: ["under 5", "5-8"],
  5: ["under 5"],
};

export const ADVANCE_RECALL: Record<Risk, number> = { cautious: 0.25, balanced: 0.5, bold: 0.75 };
export const PASS_RECALL = 0.9;
export const SPARSE_POSITIVES = 20;

export interface Policy {
  target: Target;
  timeline_years: Timeline;
  risk: Risk;
  filters: Filters;
}
export const DEFAULT_POLICY: Policy = { target: "$500M", timeline_years: null, risk: "balanced", filters: {} };

export function pAtLeast(outcome: Distributions["outcome"], target: Target): number {
  const start = OUTCOME_BANDS.indexOf(TARGET_FIRST_BAND[target]);
  return OUTCOME_BANDS.slice(start).reduce((sum, b) => sum + outcome[b], 0);
}

export function pWithin(years: Distributions["years"], timeline: Timeline): number {
  return TIMELINE_BANDS[String(timeline)].reduce((sum, b) => sum + years[b], 0);
}

export function score(d: Distributions, target: Target, timeline: Timeline): number {
  return pAtLeast(d.outcome, target) * pWithin(d.years, timeline);
}

export function withDefaults(policy?: PolicyRequest | PolicyUsed | null): Policy {
  return {
    target: policy?.target ?? DEFAULT_POLICY.target,
    timeline_years: policy?.timeline_years === undefined ? DEFAULT_POLICY.timeline_years : policy.timeline_years,
    risk: policy?.risk ?? DEFAULT_POLICY.risk,
    filters: { ...(policy?.filters ?? {}) },
  };
}

export function tableFor(thresholds: Thresholds, target: Target, timeline: Timeline): ThresholdTable {
  const t = thresholds.tables.find((t) => t.target === target && t.timeline_years === timeline);
  if (!t) throw new Error(`thresholds.json has no table for ${target}, timeline ${timeline}`);
  return t;
}

function highestThresholdWithRecall(rows: ThresholdRow[], minRecall: number): ThresholdRow | null {
  const sorted = [...rows].sort((a, b) => b.threshold - a.threshold);
  return sorted.find((r) => r.recall !== null && r.recall >= minRecall) ?? null;
}

export interface Resolved {
  policy: PolicyUsed & { filters: Filters };
  expected_precision: number | null;
  expected_recall: number | null;
  missed_winners_if_pass: number | null;
  sparse: boolean;
  n_positive: number;
}

export function resolve(thresholds: Thresholds, policy?: PolicyRequest | PolicyUsed | null): Resolved {
  const p = withDefaults(policy);
  const table = tableFor(thresholds, p.target, p.timeline_years);
  const adv = highestThresholdWithRecall(table.rows, ADVANCE_RECALL[p.risk]);
  const pas = highestThresholdWithRecall(table.rows, PASS_RECALL);
  return {
    policy: {
      target: p.target,
      timeline_years: p.timeline_years,
      risk: p.risk,
      filters: p.filters,
      advance_threshold: adv ? adv.threshold : null,
      pass_threshold: pas ? pas.threshold : null,
    },
    expected_precision: adv ? adv.precision : null,
    expected_recall: adv ? adv.recall : null,
    missed_winners_if_pass: pas && pas.recall !== null ? round(1 - pas.recall, 4) : null,
    sparse: table.n_positive < SPARSE_POSITIVES,
    n_positive: table.n_positive,
  };
}

export function decide(prob: number, advance: number | null, pass: number | null): Decision {
  if (advance !== null && prob >= advance) return "advance";
  if (pass !== null && prob < pass) return "pass";
  return "escalate";
}

/** Filter values from merged template field values (plain values, no provenance). */
export function facets(fields: Partial<FieldValues>): Facets {
  const cof = fields.cofounders ?? "unknown";
  const bg = fields.background ?? "unknown";
  const ps = fields.prior_startups ?? "unknown";
  const industry = fields.industry ?? "unknown";
  return {
    sector: industry === "unknown" ? null : industry,
    team: cof === "unknown" ? null : cof === "solo" ? "solo" : "team",
    technical: bg === "unknown" ? null : bg === "technical" || bg === "mixed",
    repeat_founder: ps === "unknown" ? null : Array.isArray(ps),
  };
}

/** Filters the founder fails. An unknown value fails an active filter (it can't be confirmed). */
export function filtersFailed(f: Facets, filters?: Filters | null): string[] {
  const failed: string[] = [];
  const fl = filters ?? {};
  if (fl.sectors && fl.sectors.length) {
    const wanted = new Set(fl.sectors.map((s) => s.toLowerCase()));
    if (f.sector === null || !wanted.has(f.sector.toLowerCase())) failed.push("sectors");
  }
  for (const key of ["team", "technical", "repeat_founder"] as const) {
    if (fl[key] !== undefined && fl[key] !== null && f[key] !== fl[key]) failed.push(key);
  }
  return failed;
}

/** Python's round(): half to even, so the port matches the backend's numbers exactly. */
export function round(x: number, digits: number): number {
  const m = 10 ** digits;
  const v = x * m;
  const r = Math.round(v);
  const isHalf = Math.abs(v % 1) === 0.5;
  return (isHalf ? (r % 2 === 0 ? r : r - 1) : r) / m;
}

/** f"{x * 100:.0f}%" in Python (half to even). */
export function pct(x: number): string {
  return `${round(x * 100, 0)}%`;
}

export function verdict(
  distributions: Distributions,
  thresholds: Thresholds,
  policy: PolicyRequest | PolicyUsed | null | undefined,
  fields: Partial<FieldValues>,
): Verdict {
  const r = resolve(thresholds, policy);
  const pol = r.policy;
  const prob = score(distributions, pol.target, pol.timeline_years);
  const decision = decide(prob, pol.advance_threshold, pol.pass_threshold);
  const failed = filtersFailed(facets(fields), pol.filters);
  const horizon = pol.timeline_years === null ? "" : ` within ${pol.timeline_years} years`;
  const estimate = pol.timeline_years !== null ? "an estimated " : "";
  const cap = decision.charAt(0).toUpperCase() + decision.slice(1);
  let summary = `${cap}: ${estimate}${pct(prob)} chance of reaching ${pol.target} or more${horizon}.`;
  if (pol.advance_threshold !== null && pol.pass_threshold !== null) {
    summary += ` At ${pol.risk} risk, founders advance from ${pct(pol.advance_threshold)} and pass below ${pct(pol.pass_threshold)}.`;
  } else if (pol.advance_threshold === null && pol.pass_threshold === null) {
    summary += " Too few validation founders reached this target and timeline to set a bar.";
  }
  if (failed.length) summary += " Filtered out by: " + failed.join(", ") + ".";
  return {
    decision,
    probability: round(prob, 4),
    probability_is_estimate: pol.timeline_years !== null,
    policy: pol,
    expected_precision: r.expected_precision,
    expected_recall: r.expected_recall,
    missed_winners_if_pass: r.missed_winners_if_pass,
    filters_failed: failed,
    summary,
  };
}

/** Change in the score if one input were flipped, at a policy (negative: the current value helps). */
export function driverDelta(base: Distributions, flipped: Distributions, target: Target, timeline: Timeline): number {
  return score(flipped, target, timeline) - score(base, target, timeline);
}
