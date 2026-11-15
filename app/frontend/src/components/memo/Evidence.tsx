"use client";

// The evidence behind the memo: what to watch out for, notes, sources and what the model read.
import { useEffect, useState } from "react";

import { IconAlert, IconChevronDown, IconFlip } from "@/components/icons";
import { SectionTitle, SourceRef, Tag, cx } from "@/components/ui";
import { api } from "@/lib/api";
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
      <ul className="space-y-2">
        {items.map((it) => (
          <li key={it.key} className="flex gap-3 rounded-[14px] bg-warn-soft px-4 py-3.5 text-warn">
            <span className="mt-[1px] shrink-0">{it.icon}</span>
            <div className="min-w-0">
              <p className="text-[15px] font-bold leading-snug">{it.title}</p>
              {it.body && <p className="mt-1 text-[14px] leading-snug text-ink-2">{it.body}</p>}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Notes({ memo }: { memo: Memo }) {
  const { investor, post_founding } = memo.notes;
  if (!investor && !post_founding.length) return null;
  return (
    <section aria-labelledby="notes">
      <SectionTitle id="notes" note="Notes are for you. They never reach the model.">
        Notes
      </SectionTitle>
      <div className="space-y-5">
        {investor && (
          <div>
            <p className="eyebrow text-muted">Yours</p>
            <p className="mt-2 whitespace-pre-wrap border-l-[3px] border-ink pl-4 text-[16px] leading-relaxed">{investor}</p>
          </div>
        )}
        {post_founding.length > 0 && (
          <div>
            <p className="eyebrow text-muted">After founding · found by the agent</p>
            <ul className="mt-2 space-y-2">
              {post_founding.map((n, i) => (
                <li key={i} className="text-[15px] leading-relaxed">
                  {n.text}{" "}
                  {n.source_ids.map((id) => (
                    <SourceRef key={id} id={id} />
                  ))}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

export function Sources({ memo }: { memo: Memo }) {
  if (!memo.sources.length) return null;
  return (
    <section aria-labelledby="sources">
      <SectionTitle id="sources">Sources</SectionTitle>
      <ol>
        {memo.sources.map((s) => (
          <li key={s.id} id={`source-${s.id}`} className="-mx-3 flex scroll-mt-24 gap-3.5 rounded-[12px] border-b border-line px-3 py-3.5 target:bg-surface target:shadow-[inset_0_0_0_2px_var(--ink)]">
            <span className="cond w-5 shrink-0 text-[24px] font-extrabold leading-[1]">{s.id.replace(/^s/, "")}</span>
            <div className="min-w-0">
              <a href={s.url} target="_blank" rel="noopener noreferrer" className="block break-words text-[15px] font-semibold leading-snug text-ink underline decoration-line-strong decoration-[1.5px] underline-offset-[3px] hover:decoration-ink">
                {s.title}
              </a>
              <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px] text-muted">
                <span>{s.publisher ?? hostOf(s.url)}</span>
                {s.published_date && <span>· {s.published_date}</span>}
                {s.before_founding === false && <Tag tone="warn">After founding · notes only</Tag>}
                {s.before_founding === null && <Tag>Date unverified</Tag>}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function UnderTheHood({ memo }: { memo: Memo }) {
  const [open, setOpen] = useState(false);
  // The questions come from rules.json: the drivers carry them too, but they may still be filling in.
  const [questions, setQuestions] = useState<Map<string, string> | null>(null);
  useEffect(() => {
    if (!open || questions || !memo.answers) return;
    api.rules().then((r) => setQuestions(new Map(r.rules.map((q) => [q.id, q.question]))), () => undefined);
  }, [open, questions, memo.answers]);
  const labels = new Map([...memo.drivers.map((d) => [d.id, d.label] as const), ...(questions ?? [])]);
  return (
    <section>
      <div className="overflow-hidden rounded-[18px] border border-line-strong">
        <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left transition-colors hover:bg-surface">
          <span>
            <span className="block text-[16px] font-bold tracking-[-0.01em]">Under the hood</span>
            <span className="block text-[13px] text-muted">The anonymised profile the model read, and its answers.</span>
          </span>
          <IconChevronDown size={20} className={cx("shrink-0 text-muted transition-transform", open && "rotate-180")} />
        </button>
        {open && (
          <div className="space-y-5 border-t border-line px-4 py-4">
            <div>
              <p className="eyebrow mb-2 text-muted">What the model read</p>
              <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-[12px] bg-surface p-3.5 font-mono text-[12.5px] leading-relaxed text-ink-2">{memo.rendered_profile}</pre>
              <p className="mt-2 text-[12.5px] text-muted">No names, nothing from after the founding date. This is the only founder information the model sees.</p>
            </div>
            {memo.answers && (
              <div>
                <p className="eyebrow mb-2 text-muted">Screening questions ({memo.answers.length})</p>
                <ul className="divide-y divide-line rounded-[12px] bg-surface">
                  {memo.answers.map((a) => (
                    <li key={a.rule_id} className="flex items-center gap-3 px-3 py-2.5">
                      <span className="min-w-0 flex-1 text-[13.5px] leading-snug">{labels.get(a.rule_id) ?? a.rule_id}</span>
                      <span className="text-[12px] tabular text-muted">{a.p_yes === null ? "–" : `${Math.round(a.p_yes * 100)}%`}</span>
                      <span className={cx("min-w-10 rounded-full px-2 py-0.5 text-center text-[12px] font-bold", a.answer === "yes" ? "bg-ink text-bg" : "bg-surface-3 text-ink-2")}>{answerLabel(a.answer)}</span>
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-[12.5px] text-muted">The percentage is the answerer&apos;s confidence that the answer is yes. Unknown means it gave no answer, and the decision model reads it as unknown.</p>
              </div>
            )}
            <p className="text-[12.5px] text-muted">
              Decision model: <span className="font-mono">{memo.decider.model_id}</span>, reading {memo.decider.input_type === "answers" ? "the answers above" : "the profile above"}.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
