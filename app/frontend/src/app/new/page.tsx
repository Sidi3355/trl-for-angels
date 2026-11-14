"use client";

// New screening: who, plus anything the investor already knows. Everything but the founder is optional.
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Examples } from "@/components/Examples";
import { IconChevronDown } from "@/components/icons";
import { Button, Card, ChipPicker, Disclaimer, Notice, Page, PageHeader, Spinner, Switch, cx } from "@/components/ui";
import type { FieldValues } from "@/lib/types";
import { parseFounder, useStartScreening } from "@/lib/useScreening";

const INDUSTRIES = [
  "fintech", "healthtech", "biotech", "B2B SaaS", "developer tools", "e-commerce", "logistics", "edtech", "climate",
  "cybersecurity", "marketplaces", "media", "hardware", "insurtech", "agtech", "gaming", "proptech", "HR tech", "travel", "food",
];
const DATE_RE = /^[0-9]{4}(-(0[1-9]|1[0-2]))?$/;

type Known = {
  industry: string;
  cofounders: "" | "solo" | "1" | "2" | "3+";
  background: "" | "technical" | "business" | "mixed" | "domain specialist";
  work_experience: "" | "<5" | "5-10" | "10-15" | "15+";
  industry_experience: "" | "none" | "some" | "deep";
  prior_startups: "" | "none";
  prior_exits: "" | "none";
};
const EMPTY: Known = { industry: "", cofounders: "", background: "", work_experience: "", industry_experience: "", prior_startups: "", prior_exits: "" };

function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="px-4 py-3">
      <label htmlFor={id} className="block text-[13px] font-medium text-muted">
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-[12.5px] text-faint">{hint}</p>}
    </div>
  );
}

const input = "mt-1 w-full bg-transparent text-[16px] outline-none placeholder:text-faint";

function NewScreening() {
  const params = useSearchParams();
  const [who, setWho] = useState(params.get("q") ?? "");
  const [company, setCompany] = useState("");
  const [founded, setFounded] = useState("");
  const [notes, setNotes] = useState("");
  const [research, setResearch] = useState(true);
  const [known, setKnown] = useState<Known>(EMPTY);
  const [open, setOpen] = useState(false);
  const { start, busy, error, setError } = useStartScreening();
  const knownCount = Object.values(known).filter(Boolean).length;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const founder = parseFounder(who);
    if (!founder) return setError("Add the founder's name, or a LinkedIn or website link.");
    if (founded.trim() && !DATE_RE.test(founded.trim())) return setError("Write the founding date as a year, or year and month: 2021 or 2021-06.");
    const fields: Partial<FieldValues> = {};
    if (known.industry.trim()) fields.industry = known.industry.trim().toLowerCase() === "b2b saas" ? "B2B SaaS" : known.industry.trim().toLowerCase();
    for (const k of ["cofounders", "background", "work_experience", "industry_experience", "prior_startups", "prior_exits"] as const) {
      if (known[k]) (fields as Record<string, string>)[k] = known[k];
    }
    start({
      founder: { ...founder, ...(company.trim() && { company_name: company.trim() }) },
      ...(founded.trim() && { founding_date: founded.trim() }),
      ...(Object.keys(fields).length && { fields }),
      ...(notes.trim() && { notes: notes.trim() }),
      options: { research },
    });
  }

  return (
    <Page>
      <PageHeader title="Screen a founder" subtitle="Tell us who. Anything else you know makes the result sharper, and your answers always win over the agent's." />

      <form onSubmit={submit} noValidate className="space-y-4">
        <Card className="divide-y divide-line overflow-hidden">
          <Field id="who" label="Founder" hint="Name, LinkedIn profile or company website.">
            <input id="who" value={who} onChange={(e) => setWho(e.target.value)} placeholder="e.g. Ada Moreno or linkedin.com/in/…" autoComplete="off" autoFocus={!who} className={input} />
          </Field>
          <Field id="company" label="Company">
            <input id="company" value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Optional" autoComplete="off" className={input} />
          </Field>
          <Field id="founded" label="Founded" hint="Only facts from before this date are used. Leave blank and the agent finds it.">
            <input id="founded" value={founded} onChange={(e) => setFounded(e.target.value)} placeholder="e.g. 2021 or 2021-06" inputMode="numeric" autoComplete="off" className={input} />
          </Field>
        </Card>

        <Card className="overflow-hidden">
          <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left">
            <span>
              <span className="block text-[16px] font-semibold">
                What you already know
                {knownCount > 0 && <span className="ml-2 rounded-full bg-accent px-1.5 py-[1px] text-[11.5px] text-accent-ink">{knownCount}</span>}
              </span>
              <span className="block text-[13px] text-muted">Optional. From a meeting, their deck or a call.</span>
            </span>
            <IconChevronDown size={20} className={cx("shrink-0 text-muted transition-transform", open && "rotate-180")} />
          </button>
          {open && (
            <div className="space-y-5 border-t border-line px-4 py-5">
              <div>
                <label htmlFor="industry" className="mb-2 block text-[14px] font-semibold">
                  Industry
                </label>
                <input id="industry" list="industries" value={known.industry} onChange={(e) => setKnown({ ...known, industry: e.target.value })} placeholder="e.g. fintech" autoComplete="off" className="h-11 w-full rounded-xl border border-line bg-surface px-3.5 outline-none placeholder:text-faint focus:border-accent" />
                <datalist id="industries">
                  {INDUSTRIES.map((i) => (
                    <option key={i} value={i} />
                  ))}
                </datalist>
              </div>
              {(
                [
                  ["cofounders", "Founding team", [["solo", "Solo"], ["1", "1 co-founder"], ["2", "2 co-founders"], ["3+", "3+"]]],
                  ["background", "Background", [["technical", "Technical"], ["business", "Business"], ["mixed", "Mixed"], ["domain specialist", "Domain specialist"]]],
                  ["work_experience", "Work experience", [["<5", "Under 5 yrs"], ["5-10", "5–10 yrs"], ["10-15", "10–15 yrs"], ["15+", "15+ yrs"]]],
                  ["industry_experience", "Experience in this industry", [["none", "None"], ["some", "Some"], ["deep", "Deep"]]],
                  ["prior_startups", "Founded a company before?", [["none", "No, first time"]]],
                  ["prior_exits", "Sold a company before?", [["none", "No"]]],
                ] as const
              ).map(([key, label, opts]) => (
                <div key={key}>
                  <p className="mb-2 text-[14px] font-semibold">{label}</p>
                  <ChipPicker label={label} value={known[key]} onChange={(v) => setKnown({ ...known, [key]: v })} options={opts.map(([value, l]) => ({ value, label: l }))} />
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="overflow-hidden">
          <Field id="notes" label="Your notes" hint="Shown in the memo only. Never used for the score.">
            <textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} placeholder="Traction, the meeting, your gut feel…" className={cx(input, "resize-none")} />
          </Field>
        </Card>

        <Card className="flex items-center justify-between gap-4 px-4 py-3.5">
          <label htmlFor="research" className="min-w-0">
            <span className="block text-[15px] font-semibold">Web research</span>
            <span className="block text-[13px] text-muted">{research ? "The agent fills in what you leave blank, with sources." : "Use only what you entered."}</span>
          </label>
          <Switch id="research" label="Web research" checked={research} onChange={setResearch} />
        </Card>

        {error && <Notice tone="danger">{error}</Notice>}

        <div className="sticky bottom-[calc(env(safe-area-inset-bottom)+68px)] z-10 -mx-1 rounded-full bg-bg/80 p-1 backdrop-blur lg:static lg:bg-transparent lg:p-0 lg:backdrop-blur-none">
          <Button type="submit" size="lg" full disabled={busy !== null}>
            {busy === "main" && <Spinner />} Screen founder
          </Button>
        </div>
      </form>

      <section className="mt-10" aria-labelledby="ex">
        <h2 id="ex" className="mb-3 text-[13px] font-semibold uppercase tracking-[0.06em] text-muted">
          Or try an example
        </h2>
        <Examples onPick={(i, key) => start(i, key)} busy={busy} />
      </section>
      <Disclaimer className="mt-12" />
    </Page>
  );
}

export default function NewPage() {
  return (
    <Suspense>
      <NewScreening />
    </Suspense>
  );
}
