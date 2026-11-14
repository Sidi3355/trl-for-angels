"use client";

// Deals: the founders screened this session, at the investor's bar, with one box to screen the next.
import Link from "next/link";
import { useMemo, useState } from "react";

import { useApp } from "@/components/AppState";
import { BarSummary } from "@/components/BarSheet";
import { Examples } from "@/components/Examples";
import { IconArrowRight, IconSearch } from "@/components/icons";
import { Avatar, Disclaimer, Notice, Page, PageHeader, Spinner, VerdictBadge, cx } from "@/components/ui";
import { API_URL } from "@/lib/api";
import { quickVerdict } from "@/lib/bar";
import { percent, relativeTime, sectorLabel } from "@/lib/format";
import type { Decision } from "@/lib/types";
import { parseFounder, useStartScreening } from "@/lib/useScreening";

function QuickScreen() {
  const [q, setQ] = useState("");
  const { start, busy, error, setError } = useStartScreening();
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const founder = parseFounder(q);
        if (!founder) return setError("Type a founder's name, or paste a LinkedIn or website link.");
        start({ founder, options: { research: true } });
      }}
    >
      <label htmlFor="quick" className="sr-only">
        Founder name, LinkedIn or website
      </label>
      <div className="flex h-14 items-center gap-2 rounded-full border border-line bg-surface pl-5 pr-1.5 shadow-card transition-colors focus-within:border-accent">
        <IconSearch size={20} className="shrink-0 text-faint" />
        <input
          id="quick"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Name, LinkedIn or website"
          autoComplete="off"
          autoCapitalize="words"
          enterKeyHint="go"
          className="min-w-0 flex-1 bg-transparent text-[16px] outline-none placeholder:text-faint"
        />
        <button type="submit" disabled={busy !== null || !q.trim()} aria-label="Screen founder" className="flex h-11 shrink-0 items-center gap-1.5 rounded-full bg-accent px-4 text-[15px] font-semibold text-accent-ink transition-opacity hover:bg-accent-hover disabled:opacity-40">
          {busy ? <Spinner /> : <IconArrowRight size={18} strokeWidth={2.2} />}
          <span className="hidden sm:inline">Screen</span>
        </button>
      </div>
      <div className="mt-2 flex items-center justify-between px-5 text-[13px]">
        <span className="text-muted">Researches only what was public before the company was founded.</span>
        <Link href={q.trim() ? `/new?q=${encodeURIComponent(q.trim())}` : "/new"} className="shrink-0 pl-3 font-medium text-accent hover:text-accent-hover">
          Add details
        </Link>
      </div>
      {error && (
        <div className="mt-3">
          <Notice tone="danger">{error}</Notice>
        </div>
      )}
    </form>
  );
}

const FILTERS: { key: Decision | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "advance", label: "Advance" },
  { key: "escalate", label: "Escalate" },
  { key: "pass", label: "Pass" },
];

export default function DealsPage() {
  const { deals, thresholds, bar, openBarSheet, healthError } = useApp();
  const [show, setShow] = useState<Decision | "all">("all");
  const { start, busy } = useStartScreening();

  const rows = useMemo(
    () => deals.map((d) => ({ d, v: thresholds ? quickVerdict(d.distributions, d.facets, thresholds, bar) : null })),
    [deals, thresholds, bar],
  );
  const counts = useMemo(() => {
    const c: Record<string, number> = { all: rows.length, advance: 0, escalate: 0, pass: 0 };
    rows.forEach(({ v }) => v && c[v.decision]++);
    return c;
  }, [rows]);
  const visible = rows.filter(({ v }) => show === "all" || v?.decision === show);

  return (
    <Page>
      <PageHeader
        title="Deals"
        subtitle={deals.length ? "Founders you've screened this session, at your bar." : "Screen a founder in about a minute."}
      />

      {healthError && (
        <div className="mb-4">
          <Notice tone="danger" title="Can't reach the screening service">
            {healthError} <span className="break-all font-mono text-[12px] opacity-80">({API_URL})</span>
          </Notice>
        </div>
      )}

      <QuickScreen />

      <button type="button" onClick={openBarSheet} className="mt-5 flex w-full items-center justify-between rounded-2xl bg-surface-2 px-4 py-3 text-left transition-colors hover:bg-surface-3 lg:hidden">
        <span className="min-w-0">
          <span className="block text-[12px] font-semibold uppercase tracking-[0.06em] text-muted">Your bar</span>
          <span className="block truncate text-[15px] font-medium">
            <BarSummary bar={bar} />
          </span>
        </span>
        <span className="pl-3 text-[14px] font-medium text-accent">Change</span>
      </button>

      {deals.length > 0 ? (
        <section className="mt-8" aria-labelledby="deals-title">
          <h2 id="deals-title" className="sr-only">
            Your deals
          </h2>
          <div className="no-scrollbar -mx-1 mb-3 flex gap-2 overflow-x-auto px-1">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setShow(f.key)}
                aria-pressed={show === f.key}
                className={cx("h-9 shrink-0 rounded-full px-3.5 text-[14px] font-medium transition-colors", show === f.key ? "bg-ink text-bg" : "bg-surface text-ink-2 ring-1 ring-inset ring-line hover:bg-surface-2")}
              >
                {f.label} <span className={cx("tabular", show === f.key ? "opacity-70" : "text-faint")}>{counts[f.key]}</span>
              </button>
            ))}
          </div>
          <ul className="overflow-hidden rounded-[20px] border border-line bg-surface shadow-card">
            {visible.map(({ d, v }) => (
              <li key={d.memo_id} className="border-t border-line first:border-t-0">
                <Link href={`/memos/${d.memo_id}`} className="flex items-center gap-3.5 px-4 py-3.5 transition-colors hover:bg-surface-2 active:bg-surface-2">
                  <Avatar name={d.name} size={42} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[16px] font-semibold">{d.name}</span>
                    <span className="block truncate text-[13px] text-muted">{[d.company, sectorLabel(d.sector), relativeTime(d.at)].filter(Boolean).join(" · ")}</span>
                  </span>
                  {v ? (
                    <span className="flex shrink-0 flex-col items-end gap-1">
                      <VerdictBadge decision={v.decision} size="sm" />
                      <span className="text-[12px] tabular text-muted">
                        {v.estimate ? "≈" : ""}
                        {percent(v.probability)}
                        {v.filtersFailed.length > 0 && " · filtered"}
                      </span>
                    </span>
                  ) : (
                    <span className="skeleton h-5 w-16 rounded-full" />
                  )}
                </Link>
              </li>
            ))}
            {visible.length === 0 && <li className="px-4 py-6 text-center text-[14px] text-muted">No founders in this group at your bar.</li>}
          </ul>
          <p className="mt-2 px-1 text-[12.5px] text-faint">
            Kept only until you close the app.{deals.some((d) => d.mock) && " Scores come from a placeholder model for now, so treat them as examples."}
          </p>

          <div className="mt-10">
            <h2 className="mb-3 text-[13px] font-semibold uppercase tracking-[0.06em] text-muted">Examples</h2>
            <Examples onPick={(input, key) => start(input, key)} busy={busy} compact />
          </div>
        </section>
      ) : (
        <section className="mt-8" aria-labelledby="examples-title">
          <div className="rounded-[24px] border border-dashed border-line-strong px-5 py-6 text-center sm:px-8">
            <p className="font-display text-[19px] font-semibold">No deals yet</p>
            <p className="mx-auto mt-1.5 max-w-sm text-[14px] leading-relaxed text-muted">
              Search a founder above. The agent reads public sources from before they founded the company, then tells you whether they clear your bar, and why.
            </p>
          </div>
          <h2 id="examples-title" className="mb-3 mt-8 text-[13px] font-semibold uppercase tracking-[0.06em] text-muted">
            Or try an example
          </h2>
          <Examples onPick={(input, key) => start(input, key)} busy={busy} />
        </section>
      )}

      <Disclaimer className="mt-12" />
    </Page>
  );
}
