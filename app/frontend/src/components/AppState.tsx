"use client";

// App-wide state: the investor's bar, the val thresholds behind it, service health, this session's
// deals and the on-device profile. One provider so the sidebar, the Founders list and every memo agree.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api } from "@/lib/api";
import { loadBar, saveBar } from "@/lib/bar";
import { registerServiceWorker } from "@/lib/push";
import { DEFAULT_POLICY, type Policy } from "@/lib/policy";
import { barFromProfile, loadProfile, storeProfile, type Profile } from "@/lib/profile";
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
  /** True once this device's storage has been read (so pages don't flash the signed-out state). */
  ready: boolean;
  /** The investor's profile, from this device's storage; null until they "sign in". */
  profile: Profile | null;
  /** Save the profile on this device and prefill the bar from it. */
  saveProfile: (p: Profile) => boolean;
  /** The bar "Reset" returns to: the profile's defaults, or the app's. */
  defaultBar: Policy;
}

const Ctx = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [bar, setBarState] = useState<Policy>(DEFAULT_POLICY);
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [barSheetOpen, setBarSheetOpen] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setBarState(loadBar());
    setProfile(loadProfile());
    setReady(true);
    setDeals(listDeals());
    registerServiceWorker();
    const off = onDealsChange(() => setDeals(listDeals()));
    api.health().then(setHealth, (e: Error) => setHealthError(e.message));
    api.thresholds().then(setThresholds, () => setThresholds(null));
    return off;
  }, []);

  const setBar = useCallback((p: Policy) => {
    setBarState(p);
    saveBar(p);
  }, []);

  const saveProfile = useCallback(
    (p: Profile) => {
      const saved = storeProfile(p);
      setProfile(p);
      setBar(barFromProfile(p, bar));
      return saved;
    },
    [bar, setBar],
  );

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
      ready,
      profile,
      saveProfile,
      defaultBar: profile ? barFromProfile(profile, DEFAULT_POLICY) : DEFAULT_POLICY,
    }),
    [bar, setBar, thresholds, health, healthError, deals, barSheetOpen, ready, profile, saveProfile],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useApp outside AppStateProvider");
  return v;
}
