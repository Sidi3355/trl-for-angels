"use client";

// Screen a list: upload a CSV of founders, then watch them sort into Meet / Look closer / Pass at your
// bar as each one finishes. Each finished founder also joins this session's Founders list.
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";

import { useApp } from "@/components/AppState";
import { IconAlert, IconArrowRight, IconUpload } from "@/components/icons";
import { NotifyButton } from "@/components/NotifyButton";
import { Button, Disclaimer, Notice, Page, PageHeader, SectionTitle, Spinner, VerdictTile, cx, linkClass } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { quickVerdict } from "@/lib/bar";
import { DECISION_LABELS, percent, sectorLabel } from "@/lib/format";
import { rememberDeal } from "@/lib/session";
import type { BatchItem, BatchResponse, Decision } from "@/lib/types";

const COLUMNS = "client_ref,name,company_name,linkedin_url,website_url,founding_date,notes,industry,cofounders,background,work_experience,industry_experience";
const TEMPLATE = `${COLUMNS}
row-1,Ada Moreno,Tallyframe,,https://example.com/tallyframe,2024-03,Met at demo day,developer tools,2,technical,10-15,deep
row-2,,,https://www.linkedin.com/in/example-founder,,,,,,,,
`;
const MAX_ROWS = 200;

function countRows(csv: string): number {
  const lines = csv.split(/\r?\n/).filter((l) => l.trim());
  return Math.max(0, lines.length - 1);
}

function Upload() {
  const router = useRouter();
  const { health } = useApp();
  const [csv, setCsv] = useState("");
  const [file, setFile] = useState<string | null>(null);
  const [paste, setPaste] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ message: string; details: string[] } | null>(null);
  const rows = countRows(csv);
  const realResearch = health && health.components.agent !== "mock";

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const b = await api.startBatchCsv(csv);
      router.replace(`/batch?id=${encodeURIComponent(b.batch_id)}`);
    } catch (e) {
      const err = e as ApiError;
      setBusy(false);
      if (err.status !== 401) setError({ message: err.status === 422 ? "Some rows don't fit. Fix them and upload again." : err.message, details: (err.details ?? []).map(String).slice(0, 8) });
    }
  }

  const templateHref = `data:text/csv;charset=utf-8,${encodeURIComponent(TEMPLATE)}`;

  return (
    <Page>
      <PageHeader eyebrow="Screen a list" title="Screen a list" subtitle="Upload a spreadsheet of founders. Each one is researched and sorted into Meet, Look closer and Pass at your bar." />

      <label
        htmlFor="csv-file"
        className={cx(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-[22px] border-2 border-dashed px-6 py-10 text-center transition-colors",
          file ? "border-ink bg-surface" : "border-line-strong hover:border-ink",
        )}
      >
        <IconUpload size={28} />
        <span className="text-[17px] font-bold">{file ?? "Choose a CSV file"}</span>
        <span className="text-[13.5px] text-muted">{file ? `${rows} founder${rows === 1 ? "" : "s"} found` : "From Google Sheets, Excel or Numbers: File, Download, CSV"}</span>
        <input
          id="csv-file"
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          onChange={async (e) => {
            const f = e.target.files?.[0];
            if (!f) return;
            setFile(f.name);
            setCsv(await f.text());
            setError(null);
          }}
        />
      </label>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 text-[13.5px]">
        <a href={templateHref} download="halomark-founders.csv" className={linkClass}>
          Download the template
        </a>
        <button type="button" onClick={() => setPaste((v) => !v)} className={linkClass}>
          {paste ? "Hide the paste box" : "Or paste rows"}
        </button>
      </div>

      {paste && (
        <div className="mt-4">
          <label htmlFor="csv-text" className="eyebrow mb-1.5 block text-muted">
            CSV rows, with the header line first
          </label>
          <textarea
            id="csv-text"
            value={csv}
            onChange={(e) => {
              setCsv(e.target.value);
              setFile(null);
            }}
            rows={6}
            placeholder={COLUMNS}
            className="w-full resize-y rounded-[14px] border-[1.5px] border-line-strong bg-surface p-3 font-mono text-[12.5px] leading-relaxed outline-none focus:border-ink"
          />
        </div>
      )}

      <p className="mt-5 text-[13.5px] leading-relaxed text-muted">
        Each row needs a name, a LinkedIn link or a website; every other column is optional. Up to {MAX_ROWS} founders.
        {realResearch && " Real web research runs for every founder, at about $0.25 each."}
      </p>

      {error && (
        <div className="mt-4">
          <Notice tone="danger" title={error.message}>
            {error.details.length > 0 && (
              <ul className="mt-1 list-disc pl-5 text-[13px]">
                {error.details.map((d) => (
                  <li key={d}>{d}</li>
                ))}
              </ul>
            )}
          </Notice>
        </div>
      )}

      <div className="mt-6">
        <Button size="lg" full disabled={busy || rows === 0 || rows > MAX_ROWS} onClick={submit}>
          {busy && <Spinner />}
          {rows > MAX_ROWS ? `Too many founders (${rows}); the limit is ${MAX_ROWS}` : rows ? `Screen ${rows} founder${rows === 1 ? "" : "s"}` : "Screen the list"}
        </Button>
      </div>
      <Disclaimer className="mt-12" />
    </Page>
  );
}

const GROUPS: Decision[] = ["advance", "escalate", "pass"];

function Triage({ id }: { id: string }) {
  const { thresholds, bar } = useApp();
  const [b, setB] = useState<BatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const remembered = useRef(new Set<string>());

  useEffect(() => {
    let stop = false;
    let timer: number | undefined;
    const tick = async () => {
      try {
        const doc = await api.batch(id);
        if (stop) return;
        setB(doc);
        for (const it of doc.items) {
          if (it.status === "complete" && it.memo_id && it.distributions && it.facets && !remembered.current.has(it.memo_id)) {
            remembered.current.add(it.memo_id);
            rememberDeal({ memo_id: it.memo_id, name: it.label, company: null, sector: it.facets.sector, distributions: it.distributions, facets: it.facets, at: doc.created_at, mock: doc.mock });
          }
        }
        if (!["complete", "partial", "failed"].includes(doc.status)) timer = window.setTimeout(tick, 1200);
      } catch (e) {
        if (!stop && (e as ApiError).status !== 401) setError((e as ApiError).status === 404 ? "This list has expired. Lists are kept for a limited time." : (e as ApiError).message);
      }
    };
    tick();
    return () => {
      stop = true;
      window.clearTimeout(timer);
    };
  }, [id]);

  const groups = useMemo(() => {
    const out: Record<Decision, { it: BatchItem; p: number; filtered: boolean }[]> = { advance: [], escalate: [], pass: [] };
    if (!b || !thresholds) return out;
    for (const it of b.items) {
      if (it.status !== "complete" || !it.distributions || !it.facets) continue;
      const v = quickVerdict(it.distributions, it.facets, thresholds, bar);
      out[v.decision].push({ it, p: v.probability, filtered: v.filtersFailed.length > 0 });
    }
    for (const g of GROUPS) out[g].sort((x, y) => y.p - x.p);
    return out;
  }, [b, thresholds, bar]);

  if (error)
    return (
      <Page>
        <PageHeader eyebrow="Screen a list" title="List unavailable" />
        <Notice tone="danger">{error}</Notice>
        <Link href="/batch" className={cx(linkClass, "mt-5 inline-block")}>
          Screen another list
        </Link>
      </Page>
    );
  if (!b)
    return (
      <Page>
        <div className="space-y-4 pt-10">
          <div className="skeleton h-10 w-2/3 rounded-xl" />
          <div className="skeleton h-3 w-full rounded-full" />
        </div>
      </Page>
    );

  const total = b.progress.total;
  const done = b.progress.complete + b.progress.failed;
  const finished = ["complete", "partial", "failed"].includes(b.status);
  const working = b.items.filter((it) => it.status === "queued" || it.status === "running");
  const failed = b.items.filter((it) => it.status === "failed");

  return (
    <Page wide>
      <PageHeader
        eyebrow="Screen a list"
        title={finished ? "Your list is screened" : `Screening ${total} founders`}
        subtitle={finished ? `${b.progress.complete} screened at your bar${b.progress.failed ? `, ${b.progress.failed} couldn't be screened` : ""}. Tap a founder for the memo.` : "Founders sort themselves into the columns below as they finish."}
      />
      <div className="flex items-center gap-4">
        <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-line-strong" role="progressbar" aria-valuenow={done} aria-valuemin={0} aria-valuemax={total} aria-label="Founders screened">
          <div className="h-full rounded-full bg-ink transition-[width] duration-500" style={{ width: `${(done / Math.max(total, 1)) * 100}%` }} />
        </div>
        <p className="cond shrink-0 text-[28px] font-extrabold leading-none">
          {done}
          <span className="text-[0.6em] text-faint">/{total}</span>
        </p>
      </div>
      {!finished && <NotifyButton kind="batch" id={b.batch_id} className="mt-5" />}

      <div className="mt-10 grid gap-10 lg:grid-cols-3 lg:gap-8">
        {GROUPS.map((g) => (
          <section key={g} aria-labelledby={`g-${g}`}>
            <div className="flex items-center gap-3 border-t-2 border-ink pt-3">
              <VerdictTile decision={g} size={34} />
              <h2 id={`g-${g}`} className="flex-1 text-[21px] font-bold tracking-[-0.025em]">
                {DECISION_LABELS[g]}
              </h2>
              <span className="cond text-[28px] font-extrabold leading-none">{groups[g].length}</span>
            </div>
            {groups[g].length === 0 ? (
              <p className="py-4 text-[14px] text-faint">{finished ? "None at your bar." : "None yet."}</p>
            ) : (
              <ul>
                {groups[g].map(({ it, p, filtered }) => (
                  <li key={it.index} className="anim-fade-up border-b border-line">
                    <Link href={`/memos/${it.memo_id}`} className="group flex items-center gap-3 py-3">
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[16px] font-semibold group-hover:underline">{it.label}</span>
                        <span className="block truncate text-[13px] text-muted">
                          {[sectorLabel(it.facets?.sector), filtered ? "outside your filters" : null].filter(Boolean).join(" · ") || " "}
                        </span>
                      </span>
                      <span className="cond text-[24px] font-extrabold leading-none">{percent(p)}</span>
                      <IconArrowRight size={16} className="text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-ink" />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>

      {working.length > 0 && (
        <section className="mt-12">
          <SectionTitle>Still working</SectionTitle>
          <ul className="-mt-2 grid gap-x-8 sm:grid-cols-2 lg:grid-cols-3">
            {working.map((it) => (
              <li key={it.index} className="flex items-center gap-3 border-b border-line py-3 text-[15px] text-ink-2">
                {it.status === "running" ? <Spinner size={15} /> : <span className="h-[15px] w-[15px] rounded-full border-[1.5px] border-line-strong" aria-hidden />}
                <span className="min-w-0 flex-1 truncate">{it.label}</span>
                <span className="text-[12.5px] text-faint">{it.status === "running" ? "Researching" : "Queued"}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {failed.length > 0 && (
        <section className="mt-12">
          <SectionTitle>Couldn&apos;t be screened</SectionTitle>
          <ul className="-mt-2">
            {failed.map((it) => (
              <li key={it.index} className="flex items-start gap-3 border-b border-line py-3 text-[15px]">
                <IconAlert size={17} className="mt-0.5 shrink-0 text-danger" />
                <span className="min-w-0">
                  <span className="block font-semibold">{it.label}</span>
                  <span className="block text-[13px] text-muted">{it.error?.message ?? "The screening failed."}</span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="mt-10 text-[13px] text-muted">
        Verdicts follow your bar: change it and the columns re-sort instantly. Every founder here is also in your{" "}
        <Link href="/founders" className={linkClass}>
          Founders
        </Link>{" "}
        list. <Link href="/batch" className={linkClass}>Screen another list</Link>
      </p>
      {b.mock && <p className="mt-2 text-[12.5px] text-faint">Scores come from a placeholder model for now, so treat them as examples.</p>}
      <Disclaimer text={b.disclaimer} className="mt-10" />
    </Page>
  );
}

function BatchPage() {
  const id = useSearchParams().get("id");
  return id ? <Triage id={id} /> : <Upload />;
}

export default function Batch() {
  return (
    <Suspense>
      <BatchPage />
    </Suspense>
  );
}
