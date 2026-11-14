"use client";

// The memo: verdict at the investor's bar, what drives it, what-ifs, then the evidence.
// Desktop: verdict pinned on the left, detail on the right. Phone: one column.
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useApp } from "@/components/AppState";
import { IconChevronLeft, IconGlobe, IconLink } from "@/components/icons";
import { Notes, Sources, UnderTheHood, WorthKnowing } from "@/components/memo/Evidence";
import { Factors } from "@/components/memo/Factors";
import { Outcome } from "@/components/memo/Outcome";
import { Profile } from "@/components/memo/Profile";
import { VerdictCard } from "@/components/memo/Verdict";
import { Disclaimer, Notice, Page, PageHeader, SLAB, Spinner, Tag, VerdictIcon, cx } from "@/components/ui";
import { api, type ApiError } from "@/lib/api";
import { DECISION_LABELS, foundedLabel, foundedSource, percent, sectorLabel } from "@/lib/format";
import { verdict as computeVerdict } from "@/lib/policy";
import { rememberDeal } from "@/lib/session";
import { SCHEMA_VERSION, type Driver, type FieldValues, type Memo, type Thresholds, type WhatIfChange, type WhatIfResponse } from "@/lib/types";

const chip = "inline-flex h-8 items-center gap-1.5 rounded-full border border-line-strong px-3.5 text-[13.5px] font-semibold text-ink-2 transition-colors hover:border-ink hover:text-ink";

function plainFields(memo: Memo): FieldValues {
  return Object.fromEntries(Object.entries(memo.fields).map(([k, f]) => [k, f.value])) as unknown as FieldValues;
}

function changeFor(d: Driver): WhatIfChange {
  return d.kind === "answer" ? { kind: "answer", rule_id: d.id, value: d.flipped as "yes" | "no" } : { kind: "field", key: d.id as keyof FieldValues, value: d.flipped };
}

export function MemoView({ memoId }: { memoId: string }) {
  const { bar } = useApp();
  const [memo, setMemo] = useState<Memo | null>(null);
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [flipped, setFlipped] = useState<Map<string, Driver>>(new Map());
  const [whatIf, setWhatIf] = useState<WhatIfResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [whatIfError, setWhatIfError] = useState<string | null>(null);
  const requestNo = useRef(0);

  useEffect(() => {
    Promise.all([api.memo(memoId), api.thresholds()]).then(
      ([m, t]) => {
        setMemo(m);
        setThresholds(t);
        rememberDeal({
          memo_id: m.memo_id,
          name: m.founder.display_name,
          company: m.founder.company_name,
          sector: m.facets.sector,
          distributions: m.distributions,
          facets: m.facets,
          at: m.created_at,
          mock: m.mock,
        });
      },
      (e: ApiError) => {
        if (e.status !== 401) setError(e.message);
      },
    );
  }, [memoId]);

  const fields = useMemo(() => (memo ? plainFields(memo) : null), [memo]);

  const runWhatIf = useCallback(
    async (next: Map<string, Driver>) => {
      const n = ++requestNo.current;
      setWhatIfError(null);
      if (!next.size) {
        setWhatIf(null);
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const res = await api.whatIf(memoId, { schema_version: SCHEMA_VERSION, changes: [...next.values()].map(changeFor) });
        if (n === requestNo.current) setWhatIf(res);
      } catch (e) {
        if (n === requestNo.current) setWhatIfError((e as ApiError).message);
      } finally {
        if (n === requestNo.current) setLoading(false);
      }
    },
    [memoId],
  );

  const toggle = (d: Driver) => {
    const next = new Map(flipped);
    if (next.has(d.id)) next.delete(d.id);
    else next.set(d.id, d);
    setFlipped(next);
    runWhatIf(next);
  };
  const reset = () => {
    setFlipped(new Map());
    runWhatIf(new Map());
  };

  if (error) {
    return (
      <Page>
        <PageHeader title="Memo unavailable" back={{ href: "/", label: "Founders" }} />
        <Notice tone="danger">{error}</Notice>
      </Page>
    );
  }
  if (!memo || !thresholds || !fields) {
    return (
      <Page wide>
        <div className="pt-12">
          <div className="skeleton h-9 w-64 rounded-xl" />
          <div className="skeleton mt-3 h-4 w-48 rounded" />
          <div className="mt-8 grid gap-x-14 gap-y-8 lg:grid-cols-[420px_minmax(0,1fr)]">
            <div className="skeleton h-[480px] rounded-[30px]" />
            <div className="space-y-4">
              <div className="skeleton h-40 rounded-[20px]" />
              <div className="skeleton h-40 rounded-[20px]" />
            </div>
          </div>
          <span className="sr-only">
            <Spinner /> Loading the memo
          </span>
        </div>
      </Page>
    );
  }

  const baseline = computeVerdict(memo.distributions, thresholds, bar, fields);
  const current = whatIf ? computeVerdict(whatIf.distributions, thresholds, bar, fields) : baseline;
  const fd = memo.founder.founding_date;
  const sector = sectorLabel(memo.facets.sector);
  const ids = memo.founder.identifier;
  const fieldsWhatIf = memo.what_if.field_changes !== "unsupported";
  const enabled = memo.drivers.every((d) => (d.kind === "answer" ? memo.what_if.answer_changes === "supported" : fieldsWhatIf));
  const whatIfOn = flipped.size > 0;

  return (
    <Page wide>
      <header className="pb-5 pt-1 lg:pb-6 lg:pt-0">
        <Link href="/" className="-ml-1.5 mb-1.5 lg:mb-3 inline-flex items-center gap-0.5 rounded-lg py-1 pr-2 text-[14px] font-medium text-muted transition-colors hover:text-ink active:opacity-60">
          <IconChevronLeft size={18} /> Founders
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
          <div className="min-w-0">
            <h1 className="text-[36px] font-extrabold leading-[0.98] tracking-[-0.04em] lg:text-[54px]">{memo.founder.display_name}</h1>
            <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1.5 text-[15px] text-muted">
              <span>{[memo.founder.company_name, sector, `Founded ${foundedLabel(fd.value)}`].filter(Boolean).join(" · ")}</span>
              {fd.provenance === "assumed" && <Tag tone="warn">Date assumed</Tag>}
              {fd.provenance === "agent" && <Tag>Date {foundedSource(fd.provenance)}</Tag>}
              {memo.mock && <Tag>Example data</Tag>}
            </p>
          </div>
          {(ids.linkedin_url || ids.website_url) && (
            <div className="flex flex-wrap gap-2">
              {ids.linkedin_url && (
                <a href={ids.linkedin_url} target="_blank" rel="noopener noreferrer" className={chip}>
                  <IconLink size={15} /> LinkedIn
                </a>
              )}
              {ids.website_url && (
                <a href={ids.website_url} target="_blank" rel="noopener noreferrer" className={chip}>
                  <IconGlobe size={15} /> Website
                </a>
              )}
            </div>
          )}
        </div>
      </header>

      <div className="grid items-start gap-x-14 gap-y-10 lg:grid-cols-[420px_minmax(0,1fr)]">
        <div className="anim-fade-up space-y-3 lg:sticky lg:top-8">
          <VerdictCard verdict={current} baseline={baseline} whatIf={whatIfOn} loading={loading} onReset={reset} />
          {memo.mock && (
            <p className="px-1 text-[12.5px] leading-snug text-faint">
              Prototype: the score comes from a placeholder model until the real one is trained, so treat every number as an example.
            </p>
          )}
        </div>

        <div className="stagger min-w-0 space-y-12">
          <Factors drivers={memo.drivers} base={memo.distributions} bar={bar} flipped={new Set(flipped.keys())} onToggle={toggle} loading={loading} enabled={enabled} error={whatIfError} />
          <Outcome d={whatIf ? whatIf.distributions : memo.distributions} bar={bar} />
          <Profile memo={memo} />
          <WorthKnowing memo={memo} />
          <Notes memo={memo} />
          <Sources memo={memo} />
          <UnderTheHood memo={memo} />
          <Disclaimer text={memo.disclaimer} />
        </div>
      </div>

      {whatIfOn && <div className="h-20 lg:hidden" aria-hidden />}
      {whatIfOn && (
        <div className="anim-fade-up fixed inset-x-0 bottom-[calc(var(--dock-clear)-4px)] z-20 px-4 lg:hidden">
          <div
            className={cx("mx-auto flex max-w-md items-center gap-2.5 rounded-full py-2 pl-4 pr-2 shadow-float ring-[3px] ring-bg transition-colors duration-500", SLAB[current.decision])}
          >
            <VerdictIcon decision={current.decision} size={16} />
            <span className="min-w-0 flex-1 truncate text-[14.5px] font-semibold">
              What-if: {DECISION_LABELS[current.decision]} <span className="tabular">{percent(current.probability)}</span>
              <span className="font-medium opacity-70"> (was {percent(baseline.probability)})</span>
            </span>
            <button type="button" onClick={reset} className="rounded-full border-[1.5px] border-current px-3 py-1 text-[13px] font-bold">
              Reset
            </button>
          </div>
        </div>
      )}
    </Page>
  );
}
