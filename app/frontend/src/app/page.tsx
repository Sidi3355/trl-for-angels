"use client";

// Founders: one box to screen the next founder, then everyone screened this session at the investor's bar.
import Link from "next/link";
import { useMemo, useState } from "react";

import { useApp } from "@/components/AppState";
import { BarSummary } from "@/components/BarSheet";
import { Examples } from "@/components/Examples";
import { IconArrowRight, IconSliders } from "@/components/icons";
import { Disclaimer, Notice, Page, Spinner, VerdictIcon, VerdictTile, cx, linkClass } from "@/components/ui";
import { API_URL } from "@/lib/api";
import { quickVerdict } from "@/lib/bar";
import { DECISION_LABELS, percent, relativeTime, sectorLabel } from "@/lib/format";
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
      <label htmlFor="quick" className="block text-[40px] font-extrabold leading-[0.98] tracking-[-0.04em] sm:text-[52px] lg:text-[60px]">
        Who&apos;s the founder?
      </label>
      <div className="mt-5 flex h-[64px] items-center gap-2 rounded-[20px] border-2 border-ink bg-surface pl-5 pr-2 transition-shadow focus-within:shadow-[0_0_0_4px_var(--surface-3)] lg:h-[72px] lg:pl-6 lg:pr-2.5">
        <input
          id="quick"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Name, LinkedIn or website"
          autoComplete="off"
          autoCapitalize="words"
          enterKeyHint="go"
          className="min-w-0 flex-1 bg-transparent text-[18px] font-medium outline-none placeholder:font-normal placeholder:text-faint lg:text-[20px]"
        />
        <button
          type="submit"
          disabled={busy !== null || !q.trim()}
          aria-label="Screen founder"
          className="flex h-12 shrink-0 items-center gap-2 rounded-[14px] bg-accent px-4 text-[15.5px] font-bold text-accent-ink transition-[background,opacity,transform] hover:bg-accent-hover active:scale-95 disabled:opacity-30 lg:h-[52px] lg:px-5"
        >
          <span className="hidden sm:inline">Screen</span>
          {busy ? <Spinner /> : <IconArrowRight size={20} strokeWidth={2.4} />}
        </button>
      </div>
      <p className="mt-3 text-[13.5px] leading-snug text-muted">
        Reads only what was public before they started the company.{" "}
        <Link href={q.trim() ? `/new?q=${encodeURIComponent(q.trim())}` : "/new"} className={cx(linkClass, "whitespace-nowrap")}>
          Add what you know
        </Link>{" "}
        or{" "}
        <Link href="/batch" className={cx(linkClass, "whitespace-nowrap")}>
          screen a list
        </Link>
      </p>
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
  { key: "advance", label: "Meet" },
  { key: "escalate", label: "Look closer" },
  { key: "pass", label: "Pass" },
];
const VERDICT_TEXT: Record<Decision, string> = { advance: "text-advance", escalate: "text-escalate", pass: "text-pass" };

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
  const has = deals.length > 0;

  return (
    <Page wide>
      <div className="grid gap-x-16 gap-y-10 pt-4 lg:grid-cols-[minmax(0,1fr)_300px] lg:pt-2">
        <div className="min-w-0">
          {healthError && (
            <div className="mb-5">
              <Notice tone="danger" title="Can't reach the screening service">
                {healthError} <span className="break-all font-mono text-[12px] opacity-80">({API_URL})</span>
              </Notice>
            </div>
          )}

          <QuickScreen />

          <button type="button" onClick={openBarSheet} className="group mt-6 flex w-full items-center gap-3 rounded-[16px] border border-line-strong px-4 py-3 text-left transition-colors hover:border-ink lg:hidden">
            <IconSliders size={18} className="shrink-0 text-muted" />
            <span className="min-w-0 flex-1">
              <span className="eyebrow block text-muted">Your bar</span>
              <span className="mt-0.5 block truncate text-[15px] font-semibold">
                <BarSummary bar={bar} />
              </span>
            </span>
            <span className={linkClass + " text-[14px]"}>Change</span>
          </button>

          {has && (
            <section className="mt-10 lg:mt-14" aria-labelledby="deals-title">
              <div className="flex items-end justify-between gap-4 border-t-2 border-ink pt-3">
                <h2 id="deals-title" className="text-[21px] font-bold tracking-[-0.025em]">
                  This session
                </h2>
                <p className="hidden text-[13px] text-muted sm:block">Judged against your bar</p>
              </div>
              <div className="no-scrollbar -mx-5 mt-3 flex gap-1.5 overflow-x-auto px-5 sm:mx-0 sm:px-0">
                {FILTERS.map((f) => (
                  <button
                    key={f.key}
                    type="button"
                    onClick={() => setShow(f.key)}
                    aria-pressed={show === f.key}
                    className={cx(
                      "flex h-9 shrink-0 items-center gap-1.5 rounded-full px-3 text-[14px] sm:px-3.5 font-semibold transition-colors duration-150",
                      show === f.key ? "bg-ink text-bg" : "text-ink-2 ring-1 ring-inset ring-line-strong hover:ring-ink",
                    )}
                  >
                    {f.key !== "all" && <span className="hidden sm:inline-flex"><VerdictIcon decision={f.key} size={13} /></span>}
                    {f.label}
                    <span className={cx("tabular", show === f.key ? "opacity-60" : "text-muted")}>{counts[f.key]}</span>
                  </button>
                ))}
              </div>
              <ul className="stagger mt-3">
                {visible.map(({ d, v }) => (
                  <li key={d.memo_id} className="border-b border-line">
                    <Link href={`/memos/${d.memo_id}`} className="group -mx-2 flex items-center gap-3.5 rounded-[14px] px-2 py-3.5 transition-colors hover:bg-surface active:bg-surface">
                      <VerdictTile decision={v ? v.decision : null} size={46} />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[17px] font-bold tracking-[-0.015em]">{d.name}</span>
                        <span className="block truncate text-[13.5px] text-muted">{[d.company, sectorLabel(d.sector), relativeTime(d.at)].filter(Boolean).join(" · ")}</span>
                      </span>
                      {v ? (
                        <span className="flex shrink-0 flex-col items-end">
                          <span className="cond text-[34px] font-extrabold leading-[0.9]">
                            {v.estimate && <span className="text-[0.6em] font-semibold text-muted">≈</span>}
                            {percent(v.probability)}
                          </span>
                          <span className={cx("mt-1 text-[12.5px] font-bold", VERDICT_TEXT[v.decision])}>
                            {DECISION_LABELS[v.decision]}
                            {v.filtersFailed.length > 0 && <span className="font-medium text-muted"> · filtered</span>}
                          </span>
                        </span>
                      ) : (
                        <span className="skeleton h-8 w-14 rounded-lg" />
                      )}
                    </Link>
                  </li>
                ))}
                {visible.length === 0 && <li className="border-b border-line py-8 text-[14.5px] text-muted">No founders in this group at your bar.</li>}
              </ul>
              <p className="mt-3 text-[12.5px] leading-snug text-faint">
                Kept only until you close the app.{deals.some((d) => d.mock) && " Scores come from a placeholder model for now, so treat them as examples."}
              </p>
            </section>
          )}
        </div>

        <aside aria-labelledby="examples-title" className="lg:pt-3">
          <h2 id="examples-title" className="eyebrow mb-3 text-muted">
            {has ? "Examples" : "Or try an example"}
          </h2>
          <Examples onPick={(input, key) => start(input, key)} busy={busy} />
          <p className="mt-3 text-[12.5px] leading-snug text-faint">Made-up founders with canned research, so they finish in seconds.</p>

          <div className="mt-8 hidden border-t border-line pt-5 lg:block">
            <h2 className="eyebrow mb-3 text-muted">What you get</h2>
            <ol className="space-y-3 text-[13.5px] leading-snug text-ink-2">
              {["A verdict against your bar: meet, look closer or pass.", "The chance of a large outcome, and what moves it.", "Every fact linked to its public source."].map((t, i) => (
                <li key={t} className="flex gap-3">
                  <span className="cond w-3 shrink-0 text-[20px] font-extrabold leading-[1]">{i + 1}</span>
                  <span>{t}</span>
                </li>
              ))}
            </ol>
          </div>
        </aside>
      </div>

      <Disclaimer className="mt-14" />
    </Page>
  );
}
