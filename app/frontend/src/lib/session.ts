// Screenings from this session, for the home screen's list. sessionStorage only: closed tab, gone
// (MASTER_PLAN guardrail: nothing stored after the session). The backend deletes memos on its own schedule.

import type { Decision } from "./types";

export interface RecentScreening {
  memo_id: string;
  name: string;
  company: string | null;
  decision: Decision;
  probability: number;
  at: string;
}

const KEY = "screener.recent";

export function recentScreenings(): RecentScreening[] {
  try {
    return JSON.parse(window.sessionStorage.getItem(KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function rememberScreening(r: RecentScreening) {
  try {
    const list = recentScreenings().filter((x) => x.memo_id !== r.memo_id);
    window.sessionStorage.setItem(KEY, JSON.stringify([r, ...list].slice(0, 20)));
  } catch {
    // storage blocked: the list just stays empty
  }
}
