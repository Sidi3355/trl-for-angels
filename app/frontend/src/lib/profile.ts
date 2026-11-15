// The investor's profile, kept ON THIS DEVICE ONLY (owner's decision, 2026-11-14): browser localStorage,
// no server database, no account on any server. The "sign-in" just creates this record. The profile's
// default target, timeline and risk prefill "Your bar"; sectors can optionally become a hard filter.
// Nothing here is sent anywhere: screenings send only the bar (target, timeline, risk, filters).

import { DEFAULT_POLICY, type Policy } from "./policy";
import type { Risk, Target, Timeline } from "./types";

export const PROFILE_KEY = "screener.profile";
export const INTRO_KEY = "screener.onboarded";
/** Every key Halomark keeps in the browser starts with one of these. */
const PREFIXES = ["screener.", "halomark."];

export type Stage = "pre-seed" | "seed" | "series-a" | "later";
export type Cheque = "<10k" | "10-25k" | "25-50k" | "50-100k" | "100k+";

export interface Profile {
  name: string;
  email: string;
  sectors: string[];
  stages: Stage[];
  cheque: Cheque | "";
  geographies: string[];
  defaults: { target: Target; timeline_years: Timeline; risk: Risk };
  /** Pass founders outside `sectors` (sets the bar's sector filter). */
  only_my_sectors: boolean;
  created_at: string;
}

export const STAGES: [Stage, string][] = [["pre-seed", "Pre-seed"], ["seed", "Seed"], ["series-a", "Series A"], ["later", "Later"]];
export const CHEQUES: [Cheque, string][] = [["<10k", "Under $10k"], ["10-25k", "$10–25k"], ["25-50k", "$25–50k"], ["50-100k", "$50–100k"], ["100k+", "$100k+"]];
export const GEOGRAPHIES = ["UK", "Europe", "US", "Canada", "Latin America", "Africa", "Middle East", "Asia", "Australia", "Anywhere"];
export const SECTORS = [
  "fintech", "healthtech", "biotech", "B2B SaaS", "developer tools", "e-commerce", "logistics", "edtech", "climate",
  "cybersecurity", "marketplaces", "media", "hardware", "insurtech", "agtech", "gaming", "proptech", "HR tech", "travel", "food",
];

export function newProfile(name: string, email: string): Profile {
  return {
    name: name.trim(),
    email: email.trim(),
    sectors: [],
    stages: [],
    cheque: "",
    geographies: [],
    defaults: { target: DEFAULT_POLICY.target, timeline_years: DEFAULT_POLICY.timeline_years, risk: DEFAULT_POLICY.risk },
    only_my_sectors: false,
    created_at: new Date().toISOString(),
  };
}

function isProfile(x: unknown): x is Profile {
  const p = x as Profile;
  return Boolean(p && typeof p.name === "string" && p.defaults && Array.isArray(p.sectors));
}

export function loadProfile(): Profile | null {
  try {
    const raw = JSON.parse(window.localStorage.getItem(PROFILE_KEY) ?? "null");
    return isProfile(raw) ? { ...newProfile("", ""), ...raw } : null;
  } catch {
    return null;
  }
}

export function storeProfile(p: Profile): boolean {
  try {
    window.localStorage.setItem(PROFILE_KEY, JSON.stringify(p));
    return true;
  } catch {
    return false; // storage blocked (e.g. private browsing): the profile lasts until the app closes
  }
}

/** The bar a profile implies: its defaults, and its sectors as a filter if asked. Other filters are kept. */
export function barFromProfile(p: Profile, current: Policy = DEFAULT_POLICY): Policy {
  const sectors = p.only_my_sectors && p.sectors.length ? p.sectors.map((s) => s.toLowerCase()) : null;
  return { ...current, ...p.defaults, filters: { ...current.filters, sectors } };
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : (parts[0] ?? "?").slice(0, 2)).toUpperCase();
}

export function introSeen(): boolean {
  try {
    return window.localStorage.getItem(INTRO_KEY) === "1";
  } catch {
    return true; // storage blocked: don't show the intro on every page load
  }
}

export function markIntroSeen() {
  try {
    window.localStorage.setItem(INTRO_KEY, "1");
  } catch {
    // nothing to remember it in
  }
}

/** Keys Halomark keeps in one browser storage area. */
export function ownKeys(store: Storage): string[] {
  const keys: string[] = [];
  for (let i = 0; i < store.length; i++) {
    const k = store.key(i);
    if (k && PREFIXES.some((p) => k.startsWith(p))) keys.push(k);
  }
  return keys;
}

/**
 * Delete everything Halomark keeps on this device: the profile, your bar, the intro flag, this session's
 * founders list, a saved passcode, and the push subscription. The servers keep nothing after the session
 * anyway (memos expire in memory within about two hours).
 */
export async function deleteAllMyData(): Promise<void> {
  for (const store of [window.localStorage, window.sessionStorage]) {
    try {
      ownKeys(store).forEach((k) => store.removeItem(k));
    } catch {
      // storage blocked: nothing was stored there
    }
  }
  try {
    const reg = await navigator.serviceWorker?.getRegistration();
    const sub = await reg?.pushManager?.getSubscription();
    await sub?.unsubscribe();
  } catch {
    // no push subscription to remove
  }
}
