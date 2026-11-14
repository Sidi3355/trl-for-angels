// The client-side controls must give exactly the backend's verdicts (policy.py). These fixtures were
// produced by the backend's own pipeline (app/contract/tools/build_mocks.py), so they are the reference.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { DEFAULT_POLICY, RISKS, TARGETS, TIMELINES, pct, round, score, verdict } from "./policy";
import type { FieldValues, Memo, Thresholds, WhatIfResponse } from "./types";

const contract = (p: string) =>
  JSON.parse(readFileSync(fileURLToPath(new URL(`../../../contract/${p}`, import.meta.url)), "utf8"));

const memos: Memo[] = contract("mocks/mock_memo.json");
const thresholds: Thresholds = contract("mocks/thresholds.json");
const whatIf: WhatIfResponse = contract("examples/what_if_response.json");

const plain = (m: Memo) =>
  Object.fromEntries(Object.entries(m.fields).map(([k, f]) => [k, f.value])) as unknown as FieldValues;

describe("policy port", () => {
  it.each(memos.map((m) => [m.memo_id, m] as const))("reproduces the verdict of %s", (_, memo) => {
    expect(verdict(memo.distributions, thresholds, memo.verdict.policy, plain(memo))).toEqual(memo.verdict);
  });

  it.each(memos.map((m) => [m.memo_id, m] as const))("reproduces every driver delta of %s", (_, memo) => {
    const { target, timeline_years } = memo.verdict.policy;
    const base = score(memo.distributions, target, timeline_years);
    for (const d of memo.drivers) {
      expect(round(score(d.distributions, target, timeline_years) - base, 4)).toBe(d.delta);
    }
  });

  it("reproduces the what-if example's verdict", () => {
    const memo = memos.find((m) => m.memo_id === whatIf.memo_id)!;
    expect(verdict(whatIf.distributions, thresholds, whatIf.verdict.policy, plain(memo))).toEqual(whatIf.verdict);
  });

  it("resolves every control combination without error", () => {
    for (const target of TARGETS)
      for (const timeline_years of TIMELINES)
        for (const risk of RISKS) {
          const v = verdict(memos[0].distributions, thresholds, { ...DEFAULT_POLICY, target, timeline_years, risk }, plain(memos[0]));
          expect(["advance", "escalate", "pass"]).toContain(v.decision);
          expect(v.probability_is_estimate).toBe(timeline_years !== null);
        }
  });

  it("filters: an unknown value fails an active filter", () => {
    const memo = memos[0];
    const fields = { ...plain(memo), cofounders: "unknown" as const };
    const v = verdict(memo.distributions, thresholds, { filters: { team: "team" } }, fields);
    expect(v.filters_failed).toEqual(["team"]);
  });

  it("rounds half to even, like Python", () => {
    expect(round(0.125, 2)).toBe(0.12);
    expect(round(0.375, 2)).toBe(0.38);
    expect(pct(0.125)).toBe("12%");
    expect(pct(0.135)).toBe("14%");
  });
});
