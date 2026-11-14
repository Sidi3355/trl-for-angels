// The evidence behind the verdict: distributions, profile fields with provenance, conflicts,
// unknowns, notes, sources and the exact text the model read.
import { useState } from "react";

import { Chip, ChevronDown, Row, cx } from "@/components/ui";
import { FIELD_LABELS, fieldSummary, jobLine, percent, provenanceLabel, unknownPathLabel } from "@/lib/format";
import type { Policy } from "@/lib/policy";
import { FIELD_KEYS, OUTCOME_BANDS, YEARS_BANDS, type Conflict, type Distributions, type JobEntry, type Memo, type Source } from "@/lib/types";

const TARGET_START = { "$50M": 2, "$500M": 3, "$1B": 4 } as const;
const TIMELINE_END = { null: 3, 8: 2, 5: 1 } as const;

function Bars({ rows }: { rows: { label: string; p: number; on: boolean }[] }) {
  const max = Math.max(...rows.map((r) => r.p), 0.01);
  return (
    <ul className="space-y-2">
      {rows.map((r) => (
        <li key={r.label} className="grid grid-cols-[92px_1fr_44px] items-center gap-2 text-[13px]">
          <span className={cx("truncate", r.on ? "font-medium text-ink" : "text-muted")}>{r.label}</span>
          <span className="h-2 overflow-hidden rounded-full bg-card-2">
            <span className={cx("block h-full rounded-full", r.on ? "bg-accent" : "bg-muted/40")} style={{ width: `${(r.p / max) * 100}%` }} />
          </span>
          <span className={cx("text-right tabular-nums", r.on ? "text-ink" : "text-muted")}>{percent(r.p)}</span>
        </li>
      ))}
    </ul>
  );
}

export function DistributionsView({ d, policy }: { d: Distributions; policy: Policy }) {
  const start = TARGET_START[policy.target];
  const end = TIMELINE_END[String(policy.timeline_years) as "null" | "8" | "5"];
  return (
    <div className="space-y-5 p-4">
      <div>
        <h3 className="mb-2 text-[15px] font-medium">Outcome</h3>
        <Bars rows={OUTCOME_BANDS.map((b, i) => ({ label: b === "shut down" ? "Shut down" : b, p: d.outcome[b], on: i >= start }))} />
      </div>
      <div>
        <h3 className="mb-2 text-[15px] font-medium">Years to that outcome</h3>
        <Bars rows={YEARS_BANDS.map((b, i) => ({ label: b === "under 5" ? "Under 5" : b === "over 8" ? "Over 8" : "5–8", p: d.years[b], on: i < end }))} />
      </div>
      <p className="text-[13px] text-muted">Highlighted bands count towards your target and timeline.</p>
    </div>
  );
}

function SourceRefs({ ids }: { ids: string[] }) {
  if (!ids.length) return null;
  return (
    <span className="ml-1 inline-flex gap-1">
      {ids.map((id) => (
        <a key={id} href={`#source-${id}`} className="rounded bg-accent-soft px-1 text-[11px] font-medium text-accent">
          {id}
        </a>
      ))}
    </span>
  );
}

export function ProfileFields({ memo }: { memo: Memo }) {
  return (
    <>
      {FIELD_KEYS.map((key) => {
        const f = memo.fields[key];
        const summary = fieldSummary(key, f.value as never);
        const tone = f.provenance === "unknown" ? "warn" : f.provenance === "agent" ? "accent" : "good";
        return (
          <Row key={key}>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[13px] text-muted">{FIELD_LABELS[key]}</span>
              <span className="flex items-center">
                <Chip tone={tone}>{provenanceLabel(f.provenance, f.confidence)}</Chip>
                <SourceRefs ids={f.source_ids} />
              </span>
            </div>
            {key === "jobs" && Array.isArray(f.value) ? (
              <ol className="mt-1 space-y-2">
                {(f.value as JobEntry[]).map((j, i) => {
                  const { title, detail } = jobLine(j);
                  return (
                    <li key={i} className="leading-snug">
                      <span className="block text-[15px]">{title}</span>
                      <span className="block text-[13px] text-muted">{detail}</span>
                    </li>
                  );
                })}
              </ol>
            ) : Array.isArray(summary) ? (
              <ul className="mt-1 space-y-1">
                {summary.map((line, i) => (
                  <li key={i} className="text-[15px] leading-snug">
                    {line}
                  </li>
                ))}
              </ul>
            ) : (
              <p className={cx("mt-0.5 text-[17px]", summary === "Unknown" && "text-muted")}>{summary}</p>
            )}
            {f.note && <p className="mt-1 text-[13px] leading-snug text-muted">{f.note}</p>}
          </Row>
        );
      })}
    </>
  );
}

const show = (v: unknown) => (typeof v === "string" ? v : Array.isArray(v) ? `${v.length} entries` : JSON.stringify(v));

export function Conflicts({ conflicts }: { conflicts: Conflict[] }) {
  return (
    <>
      {conflicts.map((c, i) => (
        <Row key={i}>
          <p className="text-[13px] text-muted">{unknownPathLabel(c.field)}</p>
          <p className="mt-0.5 text-[15px] leading-snug">
            You said <strong className="font-semibold">{show(c.investor_value)}</strong>; the agent found{" "}
            <strong className="font-semibold">{show(c.agent_value)}</strong>
            <SourceRefs ids={c.agent_source_ids} />. Your value is used.
          </p>
          {c.note && <p className="mt-1 text-[13px] text-muted">{c.note}</p>}
        </Row>
      ))}
    </>
  );
}

export function Unknowns({ paths }: { paths: string[] }) {
  return (
    <Row>
      <div className="flex flex-wrap gap-1.5">
        {paths.map((p) => (
          <Chip key={p} tone="warn">
            {unknownPathLabel(p)}
          </Chip>
        ))}
      </div>
    </Row>
  );
}

export function Notes({ memo }: { memo: Memo }) {
  const { investor, post_founding } = memo.notes;
  return (
    <>
      {investor && (
        <Row>
          <p className="text-[13px] text-muted">Your notes</p>
          <p className="mt-0.5 whitespace-pre-wrap text-[15px] leading-snug">{investor}</p>
        </Row>
      )}
      {post_founding.map((n, i) => (
        <Row key={i}>
          <p className="text-[13px] text-muted">After founding</p>
          <p className="mt-0.5 text-[15px] leading-snug">
            {n.text}
            <SourceRefs ids={n.source_ids} />
          </p>
        </Row>
      ))}
    </>
  );
}

export function Sources({ sources }: { sources: Source[] }) {
  return (
    <>
      {sources.map((s) => (
        <Row key={s.id}>
          <div id={`source-${s.id}`} className="scroll-mt-6">
            <div className="flex items-start gap-2">
              <span className="mt-0.5 rounded bg-accent-soft px-1 text-[11px] font-medium text-accent">{s.id}</span>
              <a href={s.url} target="_blank" rel="noopener noreferrer" className="min-w-0 flex-1 text-[15px] leading-snug text-accent">
                {s.title}
              </a>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-1.5 pl-7 text-[12px] text-muted">
              <span className="truncate">{s.publisher ?? new URL(s.url).hostname}</span>
              {s.published_date && <span>· {s.published_date}</span>}
              {s.before_founding === false ? <Chip tone="warn">After founding: notes only</Chip> : s.before_founding === null ? <Chip>Date unverified</Chip> : null}
            </div>
            {s.used_for.length > 0 && (
              <p className="mt-1 pl-7 text-[12px] text-muted">Used for {s.used_for.map((u) => (u === "notes" ? "notes" : unknownPathLabel(u).toLowerCase())).join(", ")}</p>
            )}
          </div>
        </Row>
      ))}
    </>
  );
}

export function ModelInput({ memo }: { memo: Memo }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex w-full items-center justify-between px-4 py-3.5 text-left active:opacity-60">
        <span>
          <span className="block text-[17px]">What the model read</span>
          <span className="block text-[13px] text-muted">The anonymised profile: no names, nothing after founding.</span>
        </span>
        <ChevronDown open={open} />
      </button>
      {open && (
        <div className="border-t border-line px-4 py-3">
          <pre className="whitespace-pre-wrap break-words font-mono text-[12px] leading-relaxed text-ink-2">{memo.rendered_profile}</pre>
          {memo.answers && (
            <p className="mt-3 text-[12px] text-muted">
              Then {memo.answers.length} yes/no screening questions were answered from it, and the decision model ({memo.decider.model_id}) read those answers.
            </p>
          )}
        </div>
      )}
    </>
  );
}
