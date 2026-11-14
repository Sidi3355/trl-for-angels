"use client";

// Dashboard (home): the next founder to screen, this session at your bar (tiles open the Founders list
// filtered by verdict), the latest founders, your bar, and how honest the odds are.
import Link from "next/link";
import { useMemo } from "react";

import { useApp } from "@/components/AppState";
import { BarSummary } from "@/components/BarSheet";
import { Examples } from "@/components/Examples";
import { IconArrowRight, IconMic, IconSliders, IconUpload } from "@/components/icons";
import { QuickScreen } from "@/components/QuickScreen";
import { Card, Disclaimer, Notice, Page, SectionTitle, Tag, VerdictTile, cx, linkClass } from "@/components/ui";
import calibration from "@/data/calibration.json";
import { API_URL } from "@/lib/api";
import { quickVerdict } from "@/lib/bar";
import { DECISION_LABELS, percent, relativeTime, sectorLabel } from "@/lib/format";
import type { Decision } from "@/lib/types";
import { useStartScreening } from "@/lib/useScreening";

const VERDICT_TEXT: Record<Decision, string> = { advance: "text-advance", escalate: "text-escalate", pass: "text-pass" };

const TILE_TINT: Record<Decision | "all", string> = {
  all: "bg-accent-soft",
  advance: "bg-advance-soft",
  escalate: "bg-escalate-soft",
  pass: "bg-pass-soft",
};

function Tile({ href, label, value, decision }: { href: string; label: string; value: number | null; decision?: Decision }) {
  return (
    <Link href={href} className={cx("group flex flex-col justify-between gap-3 rounded-[18px] border border-transparent p-4 transition-colors hover:border-ink", TILE_TINT[decision ?? "all"])}>
      <span className="flex items-center justify-between gap-2">
        <span className="text-[14px] font-semibold text-ink-2">{label}</span>
        {decision ? <VerdictTile decision={decision} size={26} /> : <IconArrowRight size={16} className="text-accent transition-transform group-hover:translate-x-0.5" />}
      </span>
      <span className="cond text-[48px] font-black leading-[0.85] tabular">{value ?? "–"}</span>
    </Link>
  );
}

export default function Dashboard() {
  const { deals, thresholds, bar, openBarSheet, healthError, health, profile, ready } = useApp();
  const { start, busy } = useStartScreening();
  const rows = useMemo(
    () => deals.map((d) => ({ d, v: thresholds ? quickVerdict(d.distributions, d.facets, thresholds, bar) : null })),
    [deals, thresholds, bar],
  );
  const counts = useMemo(() => {
    const c: Record<Decision, number> = { advance: 0, escalate: 0, pass: 0 };
    rows.forEach(({ v }) => v && c[v.decision]++);
    return c;
  }, [rows]);
  const has = deals.length > 0;
  const first = profile?.name.trim().split(/\s+/)[0];
  const known = thresholds !== null || !has;

  return (
    <Page wide>
      {healthError && (
        <div className="mb-5 pt-3">
          <Notice tone="danger" title="Can't reach the screening service">
            {healthError} <span className="break-all font-mono text-[12px] opacity-80">({API_URL})</span>
          </Notice>
        </div>
      )}
      <p className="eyebrow pt-3 text-accent lg:pt-0">{ready && first ? `Hi, ${first}` : "Dashboard"}</p>
      <div className="mt-3">
        <QuickScreen />
      </div>

      <section className="mt-10" aria-labelledby="session">
        <SectionTitle id="session" note="Judged against your bar. Kept only until you close the app.">
          This session
        </SectionTitle>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Tile href="/founders" label="Screened" value={deals.length} />
          <Tile href="/founders?show=advance" label={DECISION_LABELS.advance} value={known ? counts.advance : null} decision="advance" />
          <Tile href="/founders?show=escalate" label={DECISION_LABELS.escalate} value={known ? counts.escalate : null} decision="escalate" />
          <Tile href="/founders?show=pass" label={DECISION_LABELS.pass} value={known ? counts.pass : null} decision="pass" />
        </div>
      </section>

      <div className="mt-10 grid gap-x-12 gap-y-10 lg:grid-cols-[minmax(0,1fr)_320px]">
        <section aria-labelledby="latest" className="min-w-0">
          <SectionTitle
            id="latest"
            action={
              has ? (
                <Link href="/founders" className={cx(linkClass, "text-[14px]")}>
                  See all
                </Link>
              ) : undefined
            }
          >
            Latest
          </SectionTitle>
          {has ? (
            <ul>
              {rows.slice(0, 5).map(({ d, v }) => (
                <li key={d.memo_id} className="border-b border-line">
                  <Link href={`/memos/${d.memo_id}`} className="-mx-2 flex items-center gap-3.5 rounded-[14px] px-2 py-3 transition-colors hover:bg-surface">
                    <VerdictTile decision={v ? v.decision : null} size={40} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[16px] font-bold tracking-[-0.015em]">{d.name}</span>
                      <span className="block truncate text-[13px] text-muted">{[d.company, sectorLabel(d.sector), relativeTime(d.at)].filter(Boolean).join(" · ")}</span>
                    </span>
                    {v && (
                      <span className="flex shrink-0 flex-col items-end">
                        <span className="cond text-[28px] font-extrabold leading-[0.9]">
                          {v.estimate && <span className="text-[0.6em] font-semibold text-muted">≈</span>}
                          {percent(v.probability)}
                        </span>
                        <span className={cx("mt-0.5 text-[12px] font-bold", VERDICT_TEXT[v.decision])}>{DECISION_LABELS[v.decision]}</span>
                      </span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <div>
              <p className="mb-4 text-[14.5px] text-muted">Nothing screened yet. Try one of these made-up founders: they finish in seconds.</p>
              <Examples onPick={(input, key) => start(input, key)} busy={busy} />
            </div>
          )}
        </section>

        <aside className="space-y-4" aria-label="Your bar and the odds">
          <Card className="p-4">
            <div className="flex items-center justify-between gap-3">
              <span className="eyebrow text-muted">Your bar</span>
              <IconSliders size={16} className="text-muted" />
            </div>
            <p className="mt-1.5 text-[16px] font-semibold leading-snug">
              <BarSummary bar={bar} />
            </p>
            <button type="button" onClick={openBarSheet} className={cx(linkClass, "mt-2 text-[14px]")}>
              Change
            </button>
          </Card>

          <Link href="/calibration" className="group block rounded-[18px] border border-line bg-surface p-4 transition-colors hover:border-ink">
            <span className="flex items-center justify-between gap-3">
              <span className="eyebrow text-muted">Odds check</span>
              {calibration.status !== "final" && <Tag tone="warn">Provisional</Tag>}
            </span>
            <span className="cond mt-2 block whitespace-nowrap text-[44px] font-black leading-none">{Math.round(calibration.ece * 100)} pts</span>
            <span className="mt-1 block text-[13.5px] leading-snug text-muted">Typical gap between the odds it gives and what happened.</span>
            <span className="mt-2 inline-flex items-center gap-1 text-[14px] font-semibold">
              See the check <IconArrowRight size={15} className="transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>

          <div className="grid grid-cols-2 gap-3">
            <Link href="/batch" className="flex flex-col gap-2 rounded-[18px] border border-line bg-surface p-4 transition-colors hover:border-ink">
              <IconUpload size={20} />
              <span className="text-[14.5px] font-semibold leading-snug">Screen a list</span>
            </Link>
            <Link href="/new" className="flex flex-col gap-2 rounded-[18px] border border-line bg-surface p-4 transition-colors hover:border-ink">
              <IconMic size={20} />
              <span className="text-[14.5px] font-semibold leading-snug">Voice note</span>
            </Link>
          </div>

          {health?.mock && (
            <p className="flex gap-2 text-[13px] leading-snug text-muted">
              <span className="mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full bg-escalate-fill" aria-hidden />
              Scores are examples from a placeholder model until the trained one is plugged in.
            </p>
          )}
        </aside>
      </div>

      <Disclaimer className="mt-14" />
    </Page>
  );
}
