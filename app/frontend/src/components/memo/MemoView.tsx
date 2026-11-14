"use client";

// The memo: verdict at the investor's bar, what drives it, what-ifs, then the evidence.
// Desktop: verdict pinned on the left, detail on the right. Phone: one column.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useApp } from "@/components/AppState";
import { IconGlobe, IconLink } from "@/components/icons";
import { Notes, Sources, UnderTheHood, WorthKnowing } from "@/components/memo/Evidence";
import { Factors } from "@/components/memo/Factors";
import { Outcome } from "@/components/memo/Outcome";
import { Profile } from "@/components/memo/Profile";
import { VerdictCard } from "@/components/memo/Verdict";
import { Avatar, Disclaimer, Notice, Page, PageHeader, Spinner, Tag, VerdictBadge } from "@/components/ui";
import { api, type ApiError } from "@/lib/api";
import { foundedLabel, foundedSource, percent, sectorLabel } from "@/lib/format";
import { verdict as computeVerdict } from "@/lib/policy";
import { rememberDeal } from "@/lib/session";
import { SCHEMA_VERSION, type Driver, type FieldValues, type Memo, type Thresholds, type WhatIfChange, type WhatIfResponse } from "@/lib/types";

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
        <PageHeader title="Memo unavailable" back={{ href: "/", label: "Deals" }} />
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
          <div className="mt-8 grid gap-8 lg:grid-cols-[400px_minmax(0,1fr)]">
            <div className="skeleton h-[420px] rounded-[20px]" />
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
      <PageHeader
        back={{ href: "/", label: "Deals" }}
        title={
          <span className="flex items-center gap-3">
            <Avatar name={memo.founder.display_name} size={44} />
            <span className="min-w-0 truncate">{memo.founder.display_name}</span>
          </span>
        }
        subtitle={
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span>{[memo.founder.company_name, sector, `Founded ${foundedLabel(fd.value)}`].filter(Boolean).join(" · ")}</span>
            {fd.provenance === "assumed" && <Tag tone="warn">Date assumed</Tag>}
            {fd.provenance === "agent" && <Tag tone="accent">Date {foundedSource(fd.provenance)}</Tag>}
            {memo.mock && <Tag>Example data</Tag>}
          </span>
        }
      />
      {(ids.linkedin_url || ids.website_url) && (
        <div className="-mt-2 mb-5 flex flex-wrap gap-2">
          {ids.linkedin_url && (
            <a href={ids.linkedin_url} target="_blank" rel="noopener noreferrer" className="inline-flex h-8 items-center gap-1.5 rounded-full border border-line bg-surface px-3 text-[13px] font-medium text-ink-2 hover:bg-surface-2">
              <IconLink size={15} /> LinkedIn
            </a>
          )}
          {ids.website_url && (
            <a href={ids.website_url} target="_blank" rel="noopener noreferrer" className="inline-flex h-8 items-center gap-1.5 rounded-full border border-line bg-surface px-3 text-[13px] font-medium text-ink-2 hover:bg-surface-2">
              <IconGlobe size={15} /> Website
            </a>
          )}
        </div>
      )}

      <div className="grid items-start gap-8 lg:grid-cols-[400px_minmax(0,1fr)]">
        <div className="space-y-4 lg:sticky lg:top-8">
          <VerdictCard verdict={current} baseline={baseline} whatIf={whatIfOn} loading={loading} onReset={reset} />
          {memo.mock && (
            <p className="px-1 text-[12.5px] leading-snug text-faint">
              Prototype: the score comes from a placeholder model until the real one is trained, so treat every number as an example.
            </p>
          )}
        </div>

        <div className="min-w-0 space-y-10">
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
        <div className="anim-fade-up fixed inset-x-0 bottom-[calc(env(safe-area-inset-bottom)+66px)] z-20 px-4 lg:hidden">
          <div className="mx-auto flex max-w-md items-center gap-3 rounded-full bg-ink py-2 pl-4 pr-2 text-bg shadow-float">
            <span className="min-w-0 flex-1 truncate text-[14px]">
              What-if: <strong className="font-semibold tabular">{percent(current.probability)}</strong>
              <span className="opacity-60"> (was {percent(baseline.probability)})</span>
            </span>
            <VerdictBadge decision={current.decision} size="sm" />
            <button type="button" onClick={reset} className="rounded-full bg-bg/15 px-3 py-1.5 text-[13px] font-semibold hover:bg-bg/25">
              Reset
            </button>
          </div>
        </div>
      )}
    </Page>
  );
}
