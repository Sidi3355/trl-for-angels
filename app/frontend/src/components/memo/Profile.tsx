"use client";

// The founder on the day the company was founded: key facts first, then education and career.
// Every value says where it came from: you, a numbered source, or not found.
import { SectionTitle, SourceRef, Tag, cx } from "@/components/ui";
import { FIELD_LABELS, fieldSummary, jobLine } from "@/lib/format";
import type { EducationEntry, FieldKey, JobEntry, Memo, MemoFields } from "@/lib/types";

function Origin({ f }: { f: MemoFields[FieldKey] }) {
  if (f.provenance === "investor" || f.provenance === "investor_voice") return <Tag tone="good">{f.provenance === "investor" ? "You" : "You (voice)"}</Tag>;
  if (f.provenance === "unknown") return <Tag tone="warn">Not found</Tag>;
  return (
    <span className="inline-flex gap-1" title={f.confidence !== null ? `Found by the agent, ${Math.round(f.confidence * 100)}% confident` : "Found by the agent"}>
      {f.source_ids.map((id) => (
        <SourceRef key={id} id={id} />
      ))}
    </span>
  );
}

function Fact({ label, text, f }: { label: string; text: string; f: MemoFields[FieldKey] }) {
  const missing = text === "Unknown";
  return (
    <div className="border-b border-line py-3.5">
      <div className="flex items-center justify-between gap-2">
        <p className="eyebrow text-muted">{label}</p>
        <Origin f={f} />
      </div>
      <p className={cx("mt-1.5 text-[19px] leading-tight tracking-[-0.02em]", missing ? "text-faint" : "font-bold")}>{missing ? "Not found" : text}</p>
    </div>
  );
}

const flat = (v: string | string[]) => (Array.isArray(v) ? v.join(", ") : v);

export function Profile({ memo }: { memo: Memo }) {
  const F = memo.fields;
  const edu = F.education.value;
  const jobs = F.jobs.value;
  const fact = (k: FieldKey, label = FIELD_LABELS[k]) => <Fact label={label} text={flat(fieldSummary(k, F[k].value as never))} f={F[k]} />;

  return (
    <section aria-labelledby="profile">
      <SectionTitle id="profile" note="What was true on the day the company was founded. Numbers link to sources; your own input always wins.">
        At founding
      </SectionTitle>
      <div className="grid grid-cols-2 gap-x-6 sm:gap-x-10">
        {fact("background")}
        {fact("work_experience", "Experience")}
        {fact("cofounders", "Team")}
        {fact("industry_experience", "In this industry")}
        {fact("prior_startups")}
        {fact("prior_exits")}
      </div>

      <div className="grid gap-x-12 sm:grid-cols-2">
        <div className="pt-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="eyebrow text-muted">Career before founding</h3>
            <Origin f={F.jobs} />
          </div>
          {jobs === "unknown" ? (
            <p className="text-[15px] text-faint">Not found</p>
          ) : (
            <ol className="relative space-y-4 pl-5 before:absolute before:bottom-2 before:left-[4px] before:top-2 before:w-[2px] before:bg-line-strong">
              {(jobs as JobEntry[]).map((j, i) => {
                const { detail } = jobLine(j);
                return (
                  <li key={i} className="relative">
                    <span className="absolute -left-5 top-[6px] h-[10px] w-[10px] rounded-full bg-ink ring-[3px] ring-bg" aria-hidden />
                    <p className="text-[15.5px] font-bold leading-snug tracking-[-0.01em]">{j.role}</p>
                    <p className="text-[14px] leading-snug text-ink-2">{j.company.charAt(0).toUpperCase() + j.company.slice(1)}</p>
                    <p className="mt-0.5 text-[13px] text-muted">{detail}</p>
                  </li>
                );
              })}
            </ol>
          )}
        </div>

        <div className="pt-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="eyebrow text-muted">Education</h3>
            <Origin f={F.education} />
          </div>
          {edu === "unknown" ? (
            <p className="text-[15px] text-faint">Not found</p>
          ) : (
            <ul className="space-y-3">
              {(edu as EducationEntry[]).map((e, i) => (
                <li key={i} className="leading-snug">
                  <p className="text-[15.5px] font-bold tracking-[-0.01em]">{e.degree === "no degree" ? `${e.field} (no degree)` : `${e.degree} in ${e.field}`}</p>
                  <p className="text-[13px] text-muted">{e.qs_rank === "unknown" ? "QS rank unknown" : e.qs_rank === "unranked" ? "Not QS-ranked" : `University ranked QS ${e.qs_rank}`}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
