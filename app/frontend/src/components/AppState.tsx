"use client";

// App-wide state: the investor's bar, the val thresholds behind it, service health and this
// session's deals. One provider so the sidebar, the Deals list and every memo agree.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api } from "@/lib/api";
import { loadBar, saveBar } from "@/lib/bar";
import { DEFAULT_POLICY, type Policy } from "@/lib/policy";
import { listDeals, onDealsChange, type Deal } from "@/lib/session";
import type { Health, Thresholds } from "@/lib/types";

interface AppState {
  bar: Policy;
  setBar: (p: Policy) => void;
  thresholds: Thresholds | null;
  health: Health | null;
  healthError: string | null;
  deals: Deal[];
  barSheetOpen: boolean;
  openBarSheet: () => void;
  closeBarSheet: () => void;
}

const Ctx = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [bar, setBarState] = useState<Policy>(DEFAULT_POLICY);
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [barSheetOpen, setBarSheetOpen] = useState(false);

  useEffect(() => {
    setBarState(loadBar());
    setDeals(listDeals());
    const off = onDealsChange(() => setDeals(listDeals()));
    api.health().then(setHealth, (e: Error) => setHealthError(e.message));
    api.thresholds().then(setThresholds, () => setThresholds(null));
    return off;
  }, []);

  const setBar = useCallback((p: Policy) => {
    setBarState(p);
    saveBar(p);
  }, []);

  const value = useMemo<AppState>(
    () => ({
      bar,
      setBar,
      thresholds,
      health,
      healthError,
      deals,
      barSheetOpen,
      openBarSheet: () => setBarSheetOpen(true),
      closeBarSheet: () => setBarSheetOpen(false),
    }),
    [bar, setBar, thresholds, health, healthError, deals, barSheetOpen],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useApp outside AppStateProvider");
  return v;
}
