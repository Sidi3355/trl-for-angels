// Founders screened this session, for the Deals list. sessionStorage only: closed app, gone
// (MASTER_PLAN guardrail: nothing stored after the session). The backend deletes memos on its own schedule.
// Each entry keeps the distributions and facets, so the list can show verdicts at the investor's bar.

import type { Distributions, Facets } from "./types";

export interface Deal {
  memo_id: string;
  name: string;
  company: string | null;
  sector: string | null;
  distributions: Distributions;
  facets: Facets;
  at: string;
  mock: boolean;
}

const KEY = "screener.deals";
const EVENT = "screener:deals";

function valid(d: unknown): d is Deal {
  const x = d as Deal;
  return Boolean(x && typeof x.memo_id === "string" && x.distributions?.outcome && x.distributions?.years && x.facets);
}

export function listDeals(): Deal[] {
  try {
    const raw = JSON.parse(window.sessionStorage.getItem(KEY) ?? "[]");
    return Array.isArray(raw) ? raw.filter(valid) : [];
  } catch {
    return [];
  }
}

export function rememberDeal(d: Deal) {
  try {
    const list = listDeals().filter((x) => x.memo_id !== d.memo_id);
    window.sessionStorage.setItem(KEY, JSON.stringify([d, ...list].slice(0, 50)));
    window.dispatchEvent(new Event(EVENT));
  } catch {
    // storage blocked: the list just stays empty
  }
}

export function clearDeals() {
  try {
    window.sessionStorage.removeItem(KEY);
    window.dispatchEvent(new Event(EVENT));
  } catch {
    // nothing to clear
  }
}

export function onDealsChange(listener: () => void): () => void {
  window.addEventListener(EVENT, listener);
  return () => window.removeEventListener(EVENT, listener);
}
