"use client";

// The evidence behind the memo: what to watch out for, notes, sources and what the model read.
import { useState } from "react";

import { IconAlert, IconChevronDown, IconFlip } from "@/components/icons";
import { Card, SectionTitle, Tag, cx } from "@/components/ui";
import { answerLabel, hostOf, unknownPathLabel } from "@/lib/format";
import type { Memo } from "@/lib/types";

const show = (v: unknown) => (typeof v === "string" ? v : Array.isArray(v) ? `${v.length} entries` : JSON.stringify(v));

export function WorthKnowing({ memo }: { memo: Memo }) {
  const warnings = memo.warnings.filter((w) => w.code !== "mock_artifacts" && w.code !== "conflicts_present");
  const items: { key: string; icon: React.ReactNode; title: string; body: React.ReactNode }[] = [];
  memo.conflicts.forEach((c, i) =>
    items.push({
      key: `c${i}`,
      icon: <IconFlip size={18} />,
      title: `${unknownPathLabel(c.field)}: you and the agent disagree`,
      body: (
        <>
          You said <strong className="font-semibold text-ink">{show(c.investor_value)}</strong>; the agent found <strong className="font-semibold text-ink">{show(c.agent_value)}</strong>. Your answer is used.
        </>
      ),
    }),
  );
  if (memo.unknowns.length)
    items.push({
      key: "unknowns",
      icon: <IconAlert size={18} />,
      title: `${memo.unknowns.length} detail${memo.unknowns.length > 1 ? "s" : ""} not found`,
      body: (
        <>
          {memo.unknowns.map(unknownPathLabel).join(", ")}. Unknowns make the score less certain; add what you know and screen again.
        </>
      ),
    });
  warnings
    .filter((w) => !(w.code === "many_unknowns" && memo.unknowns.length))
    .forEach((w) => items.push({ key: w.code, icon: <IconAlert size={18} />, title: w.message, body: null }));
  if (!items.length) return null;

  return (
    <section aria-labelledby="worth">
      <SectionTitle id="worth">Worth knowing</SectionTitle>
      <Card className="divide-y divide-line">
        {items.map((it) => (
          <div key={it.key} className="flex gap-3 px-4 py-3.5">
            <span className="mt-0.5 text-escalate">{it.icon}</span>
            <div className="min-w-0">
              <p className="text-[15px] font-medium leading-snug">{it.title}</p>
              {it.body && <p className="mt-1 text-[14px] leading-snug text-muted">{it.body}</p>}
            </div>
          </div>
        ))}
      </Card>
    </section>
  );
}

export function Notes({ memo }: { memo: Memo }) {
  const { investor, post_founding } = memo.notes;
  if (!investor && !post_founding.length) return null;
  return (
    <section aria-labelledby="notes">
      <SectionTitle id="notes">Notes</SectionTitle>
      <Card className="divide-y divide-line">
        {investor && (
          <div className="px-4 py-3.5">
            <p className="text-[12.5px] font-medium text-muted">Yours</p>
            <p className="mt-1 whitespace-pre-wrap text-[15px] leading-relaxed">{investor}</p>
          </div>
        )}
        {post_founding.length > 0 && (
          <div className="px-4 py-3.5">
            <p className="text-[12.5px] font-medium text-muted">After founding · found by the agent</p>
            <ul className="mt-1 space-y-2">
              {post_founding.map((n, i) => (
                <li key={i} className="text-[15px] leading-relaxed">
                  {n.text}{" "}
                  {n.source_ids.map((id) => (
                    <a key={id} href={`#source-${id}`} className="rounded-md bg-accent-soft px-1.5 py-[1px] align-[1px] text-[11.5px] font-semibold text-accent">
                      {id.replace(/^s/, "")}
                    </a>
                  ))}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>
      <p className="mt-2 px-1 text-[12.5px] text-faint">Notes are for you. They never reach the model.</p>
    </section>
  );
}

export function Sources({ memo }: { memo: Memo }) {
  if (!memo.sources.length) return null;
  return (
    <section aria-labelledby="sources">
      <SectionTitle id="sources">Sources</SectionTitle>
      <Card className="divide-y divide-line">
        {memo.sources.map((s) => (
          <div key={s.id} id={`source-${s.id}`} className="flex scroll-mt-24 gap-3 px-4 py-3.5 target:bg-accent-soft/50">
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-accent-soft text-[12px] font-semibold text-accent">{s.id.replace(/^s/, "")}</span>
            <div className="min-w-0">
              <a href={s.url} target="_blank" rel="noopener noreferrer" className="block break-words text-[15px] font-medium leading-snug text-ink hover:text-accent">
                {s.title}
              </a>
              <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px] text-muted">
                <span>{s.publisher ?? hostOf(s.url)}</span>
                {s.published_date && <span>· {s.published_date}</span>}
                {s.before_founding === false && <Tag tone="warn">After founding · notes only</Tag>}
                {s.before_founding === null && <Tag>Date unverified</Tag>}
              </p>
            </div>
          </div>
        ))}
      </Card>
    </section>
  );
}

export function UnderTheHood({ memo }: { memo: Memo }) {
  const [open, setOpen] = useState(false);
  const labels = new Map(memo.drivers.map((d) => [d.id, d.label]));
  return (
    <section>
      <Card className="overflow-hidden">
        <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left hover:bg-surface-2">
          <span>
            <span className="block text-[16px] font-semibold">Under the hood</span>
            <span className="block text-[13px] text-muted">The anonymised profile the model read, and its answers.</span>
          </span>
          <IconChevronDown size={20} className={cx("shrink-0 text-muted transition-transform", open && "rotate-180")} />
        </button>
        {open && (
          <div className="space-y-5 border-t border-line px-4 py-4">
            <div>
              <p className="mb-2 text-[13px] font-semibold uppercase tracking-[0.05em] text-muted">What the model read</p>
              <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-xl bg-surface-2 p-3.5 font-mono text-[12.5px] leading-relaxed text-ink-2">{memo.rendered_profile}</pre>
              <p className="mt-2 text-[12.5px] text-muted">No names, nothing from after the founding date. This is the only founder information the model sees.</p>
            </div>
            {memo.answers && (
              <div>
                <p className="mb-2 text-[13px] font-semibold uppercase tracking-[0.05em] text-muted">Screening questions ({memo.answers.length})</p>
                <ul className="divide-y divide-line rounded-xl border border-line">
                  {memo.answers.map((a) => (
                    <li key={a.rule_id} className="flex items-center gap-3 px-3 py-2.5">
                      <span className="min-w-0 flex-1 text-[13.5px] leading-snug">{labels.get(a.rule_id) ?? a.rule_id}</span>
                      <span className="text-[12px] tabular text-muted">{Math.round(a.p_yes * 100)}%</span>
                      <span className={cx("w-10 rounded-md py-0.5 text-center text-[12px] font-semibold", a.answer === "yes" ? "bg-accent-soft text-accent" : "bg-surface-2 text-muted")}>{answerLabel(a.answer)}</span>
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-[12.5px] text-muted">The percentage is the answerer&apos;s confidence that the answer is yes.</p>
              </div>
            )}
            <p className="text-[12.5px] text-muted">
              Decision model: <span className="font-mono">{memo.decider.model_id}</span>, reading {memo.decider.input_type === "answers" ? "the answers above" : "the profile above"}.
            </p>
          </div>
        )}
      </Card>
    </section>
  );
}
