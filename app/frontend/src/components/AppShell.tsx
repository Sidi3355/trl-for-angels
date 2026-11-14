"use client";

// Navigation: a sidebar on desktop, a bottom tab bar on phones.
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useApp } from "@/components/AppState";
import { BarSheet, BarSummary } from "@/components/BarSheet";
import { IconDeals, IconInfo, IconPlus, IconSliders } from "@/components/icons";
import { Logo, cx, verdictDot } from "@/components/ui";
import { quickVerdict } from "@/lib/bar";
import { percent } from "@/lib/format";

function Wordmark() {
  return (
    <Link href="/" className="flex items-center gap-2.5">
      <Logo size={30} />
      <span className="font-display text-[19px] font-semibold tracking-[-0.02em]">Screener</span>
    </Link>
  );
}

function StatusPill() {
  const { health, healthError } = useApp();
  if (healthError) return <span className="inline-flex items-center gap-1.5 text-[12px] text-danger"><span className="h-1.5 w-1.5 rounded-full bg-danger" />Service offline</span>;
  if (!health) return null;
  const live = !health.mock;
  return (
    <span className="inline-flex items-center gap-1.5 text-[12px] text-muted">
      <span className={cx("h-1.5 w-1.5 rounded-full", live ? "bg-advance-fill" : "bg-escalate-fill")} />
      {live ? "Live model" : "Prototype · example scores"}
    </span>
  );
}

function Sidebar() {
  const pathname = usePathname();
  const { bar, deals, thresholds, openBarSheet } = useApp();
  const nav = [
    { href: "/", label: "Founders", icon: IconDeals, on: pathname === "/" },
    { href: "/about", label: "How it works", icon: IconInfo, on: pathname === "/about" },
  ];
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[272px] flex-col border-r border-line bg-surface px-4 pb-5 pt-6 lg:flex">
      <div className="px-2">
        <Wordmark />
      </div>
      <Link href="/new" className="mt-6 flex h-11 items-center justify-center gap-2 rounded-full bg-accent text-[15px] font-semibold text-accent-ink transition-colors hover:bg-accent-hover">
        <IconPlus size={18} strokeWidth={2.2} /> Screen a founder
      </Link>
      <nav className="mt-5 space-y-0.5" aria-label="Main">
        {nav.map(({ href, label, icon: Icon, on }) => (
          <Link key={href} href={href} aria-current={on ? "page" : undefined} className={cx("flex h-10 items-center gap-3 rounded-xl px-3 text-[15px] font-medium transition-colors", on ? "bg-surface-2 text-ink" : "text-muted hover:bg-surface-2 hover:text-ink")}>
            <Icon size={19} /> {label}
          </Link>
        ))}
      </nav>

      <button type="button" onClick={openBarSheet} className="mt-5 rounded-2xl border border-line p-3 text-left transition-colors hover:bg-surface-2">
        <span className="flex items-center justify-between text-[12px] font-semibold uppercase tracking-[0.06em] text-muted">
          Your bar <IconSliders size={16} />
        </span>
        <span className="mt-1 block text-[14px] font-medium text-ink">
          <BarSummary bar={bar} />
        </span>
      </button>

      <div className="mt-6 min-h-0 flex-1 overflow-y-auto">
        {deals.length > 0 && (
          <>
            <p className="px-3 pb-1.5 text-[12px] font-semibold uppercase tracking-[0.06em] text-muted">This session</p>
            <ul className="space-y-0.5">
              {deals.slice(0, 12).map((d) => {
                const v = thresholds ? quickVerdict(d.distributions, d.facets, thresholds, bar) : null;
                const on = pathname === `/memos/${d.memo_id}`;
                return (
                  <li key={d.memo_id}>
                    <Link href={`/memos/${d.memo_id}`} className={cx("flex h-10 items-center gap-2.5 rounded-xl px-3 text-[14px] transition-colors", on ? "bg-surface-2 text-ink" : "text-ink-2 hover:bg-surface-2")}>
                      <span className={cx("h-2 w-2 shrink-0 rounded-full", v ? verdictDot(v.decision) : "bg-surface-3")} aria-hidden />
                      <span className="min-w-0 flex-1 truncate">{d.name}</span>
                      {v && <span className="text-[12px] tabular text-muted">{percent(v.probability)}</span>}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </div>

      <div className="space-y-2 border-t border-line px-2 pt-4">
        <StatusPill />
        <p className="text-[11.5px] leading-snug text-faint">Screening aid, not investment advice.</p>
      </div>
    </aside>
  );
}

function TabBar() {
  const pathname = usePathname();
  const tabs = [
    { href: "/", label: "Founders", icon: IconDeals, on: pathname === "/" || pathname.startsWith("/memos") },
    { href: "/new", label: "Screen", icon: IconPlus, on: pathname === "/new" || pathname.startsWith("/screenings"), primary: true },
    { href: "/about", label: "About", icon: IconInfo, on: pathname === "/about" },
  ];
  return (
    <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl backdrop-saturate-150 lg:hidden">
      <div className="mx-auto flex h-[58px] max-w-md items-center justify-around px-4">
        {tabs.map(({ href, label, icon: Icon, on, primary }) =>
          primary ? (
            <Link key={href} href={href} aria-current={on ? "page" : undefined} className="flex flex-col items-center gap-0.5">
              <span className="flex h-9 w-14 items-center justify-center rounded-full bg-accent text-accent-ink shadow-[0_4px_12px_-4px_var(--accent)] active:scale-95">
                <IconPlus size={22} strokeWidth={2.4} />
              </span>
              <span className={cx("text-[10.5px] font-medium", on ? "text-accent" : "text-muted")}>{label}</span>
            </Link>
          ) : (
            <Link key={href} href={href} aria-current={on ? "page" : undefined} className={cx("flex w-16 flex-col items-center gap-1 pt-1", on ? "text-ink" : "text-faint")}>
              <Icon size={23} strokeWidth={on ? 2.1 : 1.8} />
              <span className="text-[10.5px] font-medium">{label}</span>
            </Link>
          ),
        )}
      </div>
    </nav>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <>
      <Sidebar />
      <main className="min-h-dvh pb-[calc(env(safe-area-inset-bottom)+76px)] lg:pb-0 lg:pl-[272px]">{children}</main>
      <TabBar />
      <BarSheet />
    </>
  );
}
