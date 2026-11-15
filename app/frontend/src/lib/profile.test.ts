import { describe, expect, it } from "vitest";

import { DEFAULT_POLICY } from "@/lib/policy";
import { barFromProfile, initials, newProfile, ownKeys } from "@/lib/profile";

function fakeStorage(keys: string[]): Storage {
  const m = new Map(keys.map((k) => [k, "x"]));
  return {
    get length() {
      return m.size;
    },
    key: (i: number) => [...m.keys()][i] ?? null,
    getItem: (k: string) => m.get(k) ?? null,
    setItem: (k: string, v: string) => void m.set(k, v),
    removeItem: (k: string) => void m.delete(k),
    clear: () => m.clear(),
  };
}

describe("barFromProfile", () => {
  it("prefills target, timeline and risk, and keeps other filters", () => {
    const p = { ...newProfile("Sam Rivera", ""), defaults: { target: "$1B" as const, timeline_years: 8 as const, risk: "bold" as const } };
    const bar = barFromProfile(p, { ...DEFAULT_POLICY, filters: { team: "team" } });
    expect(bar).toEqual({ target: "$1B", timeline_years: 8, risk: "bold", filters: { team: "team", sectors: null } });
  });

  it("turns sectors into a filter only when asked", () => {
    const p = { ...newProfile("Sam", ""), sectors: ["fintech", "B2B SaaS"] };
    expect(barFromProfile(p).filters.sectors).toBeNull();
    expect(barFromProfile({ ...p, only_my_sectors: true }).filters.sectors).toEqual(["fintech", "b2b saas"]);
  });
});

describe("delete-all-data scope", () => {
  it("finds Halomark's keys and nothing else", () => {
    const s = fakeStorage(["screener.bar", "screener.profile", "screener.onboarded", "halomark.x", "other-app.token", "theme"]);
    expect(ownKeys(s).sort()).toEqual(["halomark.x", "screener.bar", "screener.onboarded", "screener.profile"]);
  });
});

describe("initials", () => {
  it("uses first and last names", () => {
    expect(initials("Sam Rivera")).toBe("SR");
    expect(initials("ada")).toBe("AD");
    expect(initials("Mary Ann de Vries")).toBe("MV");
  });
});
