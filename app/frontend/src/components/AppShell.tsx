"use client";

// Navigation: a sidebar on desktop, a floating dock on phones.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { useApp } from "@/components/AppState";
import { BarSheet, BarSummary } from "@/components/BarSheet";
import { IconDeals, IconDoc, IconInfo, IconPlus, IconSliders, IconUpload, IconUser } from "@/components/icons";
import { Onboarding } from "@/components/Onboarding";
import { ThemeToggle } from "@/components/ThemeToggle";
import { VerdictIcon, Wordmark, cx } from "@/components/ui";
import { quickVerdict } from "@/lib/bar";
import { percent } from "@/lib/format";
import { initials } from "@/lib/profile";

const LEARN = ["/about", "/model-card", "/calibration"];
const ACCOUNT = ["/account", "/plans", "/terms", "/privacy"];

function StatusPill() {
  const { health, healthError } = useApp();
  if (healthError)
    return (
      <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-danger">
        <span className="h-1.5 w-1.5 rounded-full bg-danger" />
        Service offline
      </span>
    );
  if (!health) return null;
  const live = !health.mock;
  return (
    <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-muted">
      <span className={cx("h-1.5 w-1.5 rounded-full", live ? "bg-advance-fill" : "bg-escalate-fill")} />
      {live ? "Live model" : "Prototype · example scores"}
    </span>
  );
}

const VERDICT_TEXT = { advance: "text-advance", escalate: "text-escalate", pass: "text-pass" } as const;

function Sidebar() {
  const pathname = usePathname();
  const { bar, deals, thresholds, openBarSheet, profile, ready } = useApp();
  const nav = [
    { href: "/", label: "Founders", icon: IconDeals, on: pathname === "/" },
    { href: "/batch", label: "Screen a list", icon: IconUpload, on: pathname === "/batch" },
    { href: "/about", label: "How it works", icon: IconInfo, on: LEARN.includes(pathname) },
    { href: "/plans", label: "Plans", icon: IconDoc, on: pathname === "/plans" },
  ];
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[280px] flex-col border-r border-line px-5 pb-5 pt-7 lg:flex">
      <Link href="/" className="px-1">
        <Wordmark size={21} />
      </Link>
      <Link href="/new" className="mt-7 flex h-12 items-center justify-center gap-2 rounded-full bg-accent text-[15px] font-semibold text-accent-ink transition-[background,transform] hover:bg-accent-hover active:scale-[0.98]">
        <IconPlus size={18} strokeWidth={2.4} /> Screen a founder
      </Link>
      <nav className="mt-6 space-y-0.5" aria-label="Main">
        {nav.map(({ href, label, icon: Icon, on }) => (
          <Link key={href} href={href} aria-current={on ? "page" : undefined} className={cx("flex h-10 items-center gap-3 rounded-[10px] px-3 text-[15px] transition-colors", on ? "bg-surface font-semibold text-ink shadow-[0_0_0_1px_var(--line)]" : "font-medium text-muted hover:text-ink")}>
            <Icon size={18} /> {label}
          </Link>
        ))}
      </nav>

      <button type="button" onClick={openBarSheet} className="group mt-6 rounded-[16px] border border-line-strong p-3.5 text-left transition-colors hover:border-ink">
        <span className="flex items-center justify-between text-muted">
          <span className="eyebrow">Your bar</span>
          <IconSliders size={16} className="transition-colors group-hover:text-ink" />
        </span>
        <span className="mt-1.5 block text-[14.5px] font-semibold leading-snug text-ink">
          <BarSummary bar={bar} />
        </span>
      </button>

      <div className="mt-7 min-h-0 flex-1 overflow-y-auto">
        {deals.length > 0 && (
          <>
            <p className="eyebrow px-1 pb-2 text-muted">This session</p>
            <ul>
              {deals.slice(0, 12).map((d) => {
                const v = thresholds ? quickVerdict(d.distributions, d.facets, thresholds, bar) : null;
                const on = pathname === `/memos/${d.memo_id}`;
                return (
                  <li key={d.memo_id}>
                    <Link href={`/memos/${d.memo_id}`} aria-current={on ? "page" : undefined} className={cx("flex h-10 items-center gap-2.5 rounded-[10px] px-2 text-[14px] transition-colors", on ? "bg-surface font-semibold text-ink shadow-[0_0_0_1px_var(--line)]" : "text-ink-2 hover:text-ink")}>
                      <span className={cx("flex w-4 shrink-0 justify-center", v ? VERDICT_TEXT[v.decision] : "text-faint")}>{v ? <VerdictIcon decision={v.decision} size={14} /> : null}</span>
                      <span className="min-w-0 flex-1 truncate">{d.name}</span>
                      {v && <span className="cond text-[17px] font-bold text-ink">{percent(v.probability)}</span>}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </div>

      <div className="space-y-3 border-t border-line pt-4">
        <Link
          href="/account"
          aria-current={pathname === "/account" ? "page" : undefined}
          className={cx("flex items-center gap-3 rounded-[12px] p-1.5 transition-colors", pathname === "/account" ? "bg-surface shadow-[0_0_0_1px_var(--line)]" : "hover:bg-surface-2")}
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink text-[13px] font-bold text-bg" aria-hidden>
            {profile ? initials(profile.name) : <IconUser size={17} />}
          </span>
          <span className="min-w-0">
            <span className="block truncate text-[14.5px] font-semibold">{ready && profile ? profile.name : "Sign in"}</span>
            <span className="block text-[12px] text-muted">{ready && profile ? "Profile on this device" : "Your profile and settings"}</span>
          </span>
        </Link>
        <div className="space-y-1.5 px-1">
          <div className="flex items-center justify-between gap-2 pb-1">
            <span className="text-[12.5px] font-medium text-muted">Appearance</span>
            <ThemeToggle compact />
          </div>
          <StatusPill />
          <p className="text-[11.5px] leading-snug text-faint">
            Screening aid, not investment advice. <Link href="/terms" className="underline underline-offset-2 hover:text-ink">Terms</Link> ·{" "}
            <Link href="/privacy" className="underline underline-offset-2 hover:text-ink">Privacy</Link>
          </p>
        </div>
      </div>
    </aside>
  );
}

/** Phones: the wordmark and the service status, above every page. */
function TopBar() {
  return (
    <div className="flex items-center justify-between pl-[max(20px,env(safe-area-inset-left))] pr-[max(20px,env(safe-area-inset-right))] pt-[env(safe-area-inset-top)] sm:px-8 lg:hidden" style={{ height: "calc(48px + env(safe-area-inset-top))" }}>
      <Link href="/" aria-label="Halomark home">
        <Wordmark size={17} />
      </Link>
      <StatusPill />
    </div>
  );
}

/** True while the page is being scrolled down, so the dock can step aside (iOS-style); false on the way up. */
function useScrollingDown(): boolean {
  const [down, setDown] = useState(false);
  useEffect(() => {
    let last = window.scrollY;
    const onScroll = () => {
      const y = window.scrollY;
      const nearBottom = window.innerHeight + y >= document.documentElement.scrollHeight - 40;
      if (y < 80 || nearBottom) setDown(false);
      else if (y > last + 6) setDown(true);
      else if (y < last - 6) setDown(false);
      last = y;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return down;
}

function Dock() {
  const pathname = usePathname();
  const hidden = useScrollingDown();
  useEffect(() => {
    document.documentElement.toggleAttribute("data-dock-hidden", hidden);
  }, [hidden]);
  const tabs = [
    { href: "/", label: "Founders", icon: IconDeals, on: pathname === "/" || pathname.startsWith("/memos") },
    { href: "/new", label: "Screen", icon: IconPlus, on: pathname === "/new" || pathname === "/batch" || pathname === "/share" || pathname.startsWith("/screenings"), primary: true },
    { href: "/account", label: "You", icon: IconUser, on: ACCOUNT.includes(pathname) || LEARN.includes(pathname) },
  ];
  return (
    <nav aria-label="Main" className={cx("pointer-events-none fixed inset-x-0 bottom-0 z-30 flex justify-center pb-[max(env(safe-area-inset-bottom),12px)] transition-transform duration-300 ease-out motion-reduce:transition-none lg:hidden", hidden && "translate-y-[150%]")}>
      <div className="pointer-events-auto flex h-[60px] items-center gap-1 rounded-full bg-dock p-1.5 text-dock-ink shadow-float ring-1 ring-white/10">
        {tabs.map(({ href, label, icon: Icon, on, primary }) =>
          primary ? (
            <Link key={href} href={href} aria-current={on ? "page" : undefined} className="flex h-12 items-center gap-1.5 rounded-full bg-dock-ink pl-4 pr-5 text-[15px] font-bold text-dock transition-transform active:scale-95">
              <IconPlus size={20} strokeWidth={2.6} />
              {label}
            </Link>
          ) : (
            <Link key={href} href={href} aria-current={on ? "page" : undefined} className={cx("flex h-12 w-[92px] items-center justify-center gap-1.5 rounded-full text-[13.5px] font-semibold transition-[background,opacity]", on ? "bg-white/14" : "opacity-65 active:opacity-100")}>
              <Icon size={18} strokeWidth={2} />
              {label}
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
      <main className="min-h-dvh pb-[var(--dock-clear)] lg:pb-0 lg:pl-[280px]">
        <TopBar />
        {children}
      </main>
      <Dock />
      <BarSheet />
      <Onboarding />
    </>
  );
}
