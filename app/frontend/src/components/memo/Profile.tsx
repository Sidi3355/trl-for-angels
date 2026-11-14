"use client";

// The founder on the day the company was founded: key facts first, then education and career.
// Every value says where it came from: you, a numbered source, or not found.
import { Card, SectionTitle, Tag, cx } from "@/components/ui";
import { FIELD_LABELS, fieldSummary, jobLine } from "@/lib/format";
import type { EducationEntry, FieldKey, JobEntry, Memo, MemoFields } from "@/lib/types";

function Origin({ f }: { f: MemoFields[FieldKey] }) {
  if (f.provenance === "investor" || f.provenance === "investor_voice") return <Tag tone="good">{f.provenance === "investor" ? "You" : "You (voice)"}</Tag>;
  if (f.provenance === "unknown") return <Tag tone="warn">Not found</Tag>;
  return (
    <span className="inline-flex gap-1" title={f.confidence !== null ? `Found by the agent, ${Math.round(f.confidence * 100)}% confident` : "Found by the agent"}>
      {f.source_ids.map((id) => (
        <a key={id} href={`#source-${id}`} className="rounded-md bg-accent-soft px-1.5 py-[1px] text-[11.5px] font-semibold text-accent hover:opacity-80">
          {id.replace(/^s/, "")}
        </a>
      ))}
    </span>
  );
}

function Fact({ k, f }: { k: FieldKey; f: MemoFields[FieldKey] }) {
  const v = fieldSummary(k, f.value as never);
  const text = Array.isArray(v) ? v.join(", ") : v;
  return (
    <div className="bg-surface p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[12.5px] font-medium text-muted">{FIELD_LABELS[k]}</p>
        <Origin f={f} />
      </div>
      <p className={cx("mt-1 text-[16px] font-semibold leading-snug", text === "Unknown" && "font-normal text-faint")}>{text === "Unknown" ? "Not found" : text}</p>
    </div>
  );
}

export function Profile({ memo }: { memo: Memo }) {
  const F = memo.fields;
  const edu = F.education.value;
  const jobs = F.jobs.value;
  const startups = fieldSummary("prior_startups", F.prior_startups.value);
  const exits = fieldSummary("prior_exits", F.prior_exits.value);

  return (
    <section aria-labelledby="profile">
      <SectionTitle id="profile">At founding</SectionTitle>
      <Card className="overflow-hidden">
        <div className="grid grid-cols-2 gap-px bg-line">
          <Fact k="background" f={F.background} />
          <Fact k="work_experience" f={F.work_experience} />
          <Fact k="cofounders" f={F.cofounders} />
          <Fact k="industry_experience" f={F.industry_experience} />
        </div>

        <div className="border-t border-line p-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-[13px] font-semibold uppercase tracking-[0.05em] text-muted">Education</h3>
            <Origin f={F.education} />
          </div>
          {edu === "unknown" ? (
            <p className="text-[15px] text-faint">Not found</p>
          ) : (
            <ul className="space-y-1.5">
              {(edu as EducationEntry[]).map((e, i) => (
                <li key={i} className="text-[15px] leading-snug">
                  <span className="font-medium">{e.degree === "no degree" ? `${e.field} (no degree)` : `${e.degree} in ${e.field}`}</span>
                  <span className="text-muted"> · {e.qs_rank === "unknown" ? "QS rank unknown" : e.qs_rank === "unranked" ? "not QS-ranked" : `QS ${e.qs_rank}`}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="border-t border-line p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-[13px] font-semibold uppercase tracking-[0.05em] text-muted">Career before founding</h3>
            <Origin f={F.jobs} />
          </div>
          {jobs === "unknown" ? (
            <p className="text-[15px] text-faint">Not found</p>
          ) : (
            <ol className="relative space-y-4 pl-5 before:absolute before:bottom-2 before:left-[5px] before:top-2 before:w-px before:bg-line-strong">
              {(jobs as JobEntry[]).map((j, i) => {
                const { detail } = jobLine(j);
                return (
                  <li key={i} className="relative">
                    <span className="absolute -left-5 top-[6px] h-[11px] w-[11px] rounded-full border-2 border-surface bg-faint" aria-hidden />
                    <p className="text-[15px] font-semibold leading-snug">{j.role}</p>
                    <p className="text-[14px] leading-snug text-ink-2">{j.company.charAt(0).toUpperCase() + j.company.slice(1)}</p>
                    <p className="mt-0.5 text-[13px] text-muted">{detail}</p>
                  </li>
                );
              })}
            </ol>
          )}
        </div>

        <div className="grid grid-cols-2 gap-px border-t border-line bg-line">
          <div className="bg-surface p-4">
            <div className="flex items-center justify-between gap-2">
              <p className="text-[12.5px] font-medium text-muted">Earlier startups</p>
              <Origin f={F.prior_startups} />
            </div>
            <p className={cx("mt-1 text-[15px] font-semibold leading-snug", startups === "Unknown" && "font-normal text-faint")}>{Array.isArray(startups) ? startups.join(", ") : startups === "Unknown" ? "Not found" : startups}</p>
          </div>
          <div className="bg-surface p-4">
            <div className="flex items-center justify-between gap-2">
              <p className="text-[12.5px] font-medium text-muted">Earlier exits</p>
              <Origin f={F.prior_exits} />
            </div>
            <p className={cx("mt-1 text-[15px] font-semibold leading-snug", exits === "Unknown" && "font-normal text-faint")}>{Array.isArray(exits) ? exits.join(", ") : exits === "Unknown" ? "Not found" : exits}</p>
          </div>
        </div>
      </Card>
      <p className="mt-2 px-1 text-[12.5px] text-faint">
        Numbers link to sources. <span className="font-medium text-advance">You</span> marks your input, which always wins.
      </p>
    </section>
  );
}
