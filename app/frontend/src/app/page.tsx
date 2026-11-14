"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Chip, DecisionPill, Disclaimer, Mark, Notice, Page, Row, Section, Spinner, Switch, ChevronDown, cx } from "@/components/ui";
import { ApiError, api, API_URL } from "@/lib/api";
import { percent, relativeTime } from "@/lib/format";
import { recentScreenings, type RecentScreening } from "@/lib/session";
import { SCHEMA_VERSION, type FieldValues, type Health, type InvestorInput } from "@/lib/types";

const INDUSTRIES = [
  "fintech", "healthtech", "biotech", "B2B SaaS", "developer tools", "e-commerce", "logistics", "edtech", "climate",
  "cybersecurity", "marketplaces", "media", "hardware", "insurtech", "agtech", "gaming", "proptech", "HR tech", "travel", "food",
];

type Known = {
  industry: string;
  cofounders: string;
  background: string;
  work_experience: string;
  industry_experience: string;
  prior_startups: string;
  prior_exits: string;
};
const EMPTY_KNOWN: Known = { industry: "", cofounders: "", background: "", work_experience: "", industry_experience: "", prior_startups: "", prior_exits: "" };

const KNOWN_OPTIONS: { key: Exclude<keyof Known, "industry">; label: string; options: [string, string][] }[] = [
  { key: "cofounders", label: "Founding team", options: [["solo", "Solo founder"], ["1", "1 co-founder"], ["2", "2 co-founders"], ["3+", "3+ co-founders"]] },
  { key: "background", label: "Background", options: [["technical", "Technical"], ["business", "Business"], ["mixed", "Mixed"], ["domain specialist", "Domain specialist"]] },
  { key: "work_experience", label: "Work experience", options: [["<5", "Under 5 years"], ["5-10", "5–10 years"], ["10-15", "10–15 years"], ["15+", "15+ years"]] },
  { key: "industry_experience", label: "Experience in this industry", options: [["none", "None"], ["some", "Some"], ["deep", "Deep"]] },
  { key: "prior_startups", label: "Earlier startups", options: [["none", "None"]] },
  { key: "prior_exits", label: "Earlier exits", options: [["none", "None"]] },
];

const DATE_RE = /^[0-9]{4}(-(0[1-9]|1[0-2])(-(0[1-9]|[12][0-9]|3[01]))?)?$/;

function toUrl(raw: string): string | null {
  const s = raw.trim();
  if (!s) return null;
  const withScheme = /^https?:\/\//i.test(s) ? s : `https://${s}`;
  try {
    const u = new URL(withScheme);
    return u.hostname.includes(".") ? u.toString() : null;
  } catch {
    return null;
  }
}

export default function Home() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [link, setLink] = useState("");
  const [founded, setFounded] = useState("");
  const [notes, setNotes] = useState("");
  const [research, setResearch] = useState(true);
  const [known, setKnown] = useState<Known>(EMPTY_KNOWN);
  const [showKnown, setShowKnown] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [demos, setDemos] = useState<InvestorInput[]>([]);
  const [recent, setRecent] = useState<RecentScreening[]>([]);

  useEffect(() => {
    setRecent(recentScreenings());
    api.health().then(setHealth, (e: ApiError) => setHealthError(e.message));
    api.demoFounders().then(setDemos, () => setDemos([]));
  }, []);

  async function start(input: InvestorInput, label: string) {
    setError(null);
    setBusy(label);
    try {
      const job = await api.startScreening(input);
      router.push(`/screenings/${job.job_id}`);
    } catch (e) {
      setBusy(null);
      const err = e as ApiError;
      if (err.status !== 401) setError(err.details?.length ? `${err.message} (${String(err.details[0])})` : err.message);
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const url = toUrl(link);
    if (link.trim() && !url) return setError("That link doesn't look like a web address.");
    if (!name.trim() && !url) return setError("Add the founder's name or a link to their LinkedIn or website.");
    if (founded.trim() && !DATE_RE.test(founded.trim())) return setError("Write the founding date as YYYY or YYYY-MM, for example 2021-06.");

    const fields: Partial<FieldValues> = {};
    if (known.industry.trim()) fields.industry = known.industry.trim().toLowerCase() === "b2b saas" ? "B2B SaaS" : known.industry.trim().toLowerCase();
    for (const { key } of KNOWN_OPTIONS) if (known[key]) (fields as Record<string, string>)[key] = known[key];

    const isLinkedIn = url ? new URL(url).hostname.endsWith("linkedin.com") : false;
    const input: InvestorInput = {
      schema_version: SCHEMA_VERSION,
      founder: {
        ...(name.trim() && { name: name.trim() }),
        ...(company.trim() && { company_name: company.trim() }),
        ...(url && (isLinkedIn ? { linkedin_url: url } : { website_url: url })),
      },
      ...(founded.trim() && { founding_date: founded.trim() }),
      ...(Object.keys(fields).length && { fields }),
      ...(notes.trim() && { notes: notes.trim() }),
      options: { research },
    };
    start(input, "form");
  }

  const mockResearch = health?.components.agent === "mock";

  return (
    <Page>
      <header className="flex items-center gap-3 pt-4">
        <Mark />
        <div>
          <h1 className="text-[28px] font-bold leading-tight tracking-tight">Screener</h1>
          <p className="text-[15px] text-muted">Research a founder. Get a calibrated first call.</p>
        </div>
      </header>

      <div className="mt-5 space-y-2">
        {healthError && (
          <Notice tone="danger">
            Can&apos;t reach the screening service at <span className="break-all font-mono text-[13px]">{API_URL}</span>. {healthError}
          </Notice>
        )}
        {health?.status === "degraded" && (
          <Notice tone="warn">Part of the service isn&apos;t set up: {Object.values(health.errors).join(" ")}</Notice>
        )}
        {health?.mock && (
          <Notice tone="info">
            <strong className="font-semibold">Prototype.</strong>{" "}
            {mockResearch ? "Web research is simulated, and" : "Web research is real, but"} the scores come from a placeholder
            model, so every number is illustrative.
          </Notice>
        )}
      </div>

      <form onSubmit={submit} noValidate>
        <Section title="Founder" footer="A name and a link work best. Research uses only what was public before the founding date.">
          <Row>
            <label className="block text-[13px] text-muted" htmlFor="name">Name</label>
            <input id="name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="off" placeholder="e.g. Ada Moreno" className="mt-0.5 w-full bg-transparent outline-none placeholder:text-muted/60" />
          </Row>
          <Row>
            <label className="block text-[13px] text-muted" htmlFor="company">Company</label>
            <input id="company" value={company} onChange={(e) => setCompany(e.target.value)} autoComplete="off" placeholder="Optional" className="mt-0.5 w-full bg-transparent outline-none placeholder:text-muted/60" />
          </Row>
          <Row>
            <label className="block text-[13px] text-muted" htmlFor="link">LinkedIn or website</label>
            <input id="link" value={link} onChange={(e) => setLink(e.target.value)} type="url" inputMode="url" autoCapitalize="none" autoCorrect="off" placeholder="linkedin.com/in/… or company.com" className="mt-0.5 w-full bg-transparent outline-none placeholder:text-muted/60" />
          </Row>
          <Row>
            <label className="block text-[13px] text-muted" htmlFor="founded">Founded</label>
            <input id="founded" value={founded} onChange={(e) => setFounded(e.target.value)} inputMode="numeric" autoComplete="off" placeholder="YYYY or YYYY-MM (optional)" className="mt-0.5 w-full bg-transparent outline-none placeholder:text-muted/60" />
          </Row>
        </Section>

        <section className="mt-7">
          <button type="button" onClick={() => setShowKnown((v) => !v)} aria-expanded={showKnown} className="flex w-full items-center justify-between rounded-2xl bg-card px-4 py-3.5 text-left active:opacity-70">
            <span>
              <span className="block text-[17px]">What you already know</span>
              <span className="block text-[13px] text-muted">Optional. Your answers override the agent&apos;s.</span>
            </span>
            <ChevronDown open={showKnown} />
          </button>
          {showKnown && (
            <div className="mt-2 overflow-hidden rounded-2xl bg-card">
              <Row>
                <label className="block text-[13px] text-muted" htmlFor="industry">Industry</label>
                <input id="industry" list="industries" value={known.industry} onChange={(e) => setKnown({ ...known, industry: e.target.value })} placeholder="Not sure" autoComplete="off" className="mt-0.5 w-full bg-transparent outline-none placeholder:text-muted/60" />
                <datalist id="industries">{INDUSTRIES.map((i) => <option key={i} value={i} />)}</datalist>
              </Row>
              {KNOWN_OPTIONS.map(({ key, label, options }) => (
                <Row key={key} className="flex items-center justify-between gap-3">
                  <label htmlFor={key} className="text-[15px]">{label}</label>
                  <select id={key} value={known[key]} onChange={(e) => setKnown({ ...known, [key]: e.target.value })} className="max-w-[55%] appearance-none bg-transparent text-right text-muted outline-none">
                    <option value="">Not sure</option>
                    {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </Row>
              ))}
            </div>
          )}
        </section>

        <Section title="Your notes" footer="Shown in the memo only. Never sent to the model.">
          <Row>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} placeholder="Meeting notes, traction, gut feel…" aria-label="Your notes" className="w-full resize-none bg-transparent outline-none placeholder:text-muted/60" />
          </Row>
        </Section>

        <div className="mt-4 overflow-hidden rounded-2xl bg-card">
          <Row className="flex items-center justify-between">
            <label htmlFor="research" className="pr-3 text-[15px]">
              Web research
              <span className="block text-[13px] text-muted">{research ? "The agent fills in what you leave blank." : "Use only what you entered."}</span>
            </label>
            <Switch id="research" checked={research} onChange={setResearch} />
          </Row>
        </div>

        {error && <div className="mt-4"><Notice tone="danger">{error}</Notice></div>}

        <button type="submit" disabled={busy !== null} className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-accent py-4 text-[17px] font-semibold text-accent-ink active:opacity-80 disabled:opacity-60">
          {busy === "form" && <Spinner />} Screen founder
        </button>
      </form>

      {demos.length > 0 && (
        <Section title="Try a demo founder" footer="Fictional founders with canned research, to see the whole flow.">
          {demos.map((d, i) => {
            const label = d.founder.name ?? d.founder.website_url ?? `Demo ${i + 1}`;
            return (
              <Row key={label}>
                <button type="button" disabled={busy !== null} onClick={() => start({ ...d, schema_version: SCHEMA_VERSION }, label)} className="flex w-full items-center justify-between gap-3 text-left active:opacity-60 disabled:opacity-60">
                  <span className="min-w-0">
                    <span className="block truncate text-[17px]">{label}</span>
                    <span className="block truncate text-[13px] text-muted">{d.founder.company_name ?? (d.founder.website_url ? new URL(d.founder.website_url).hostname : "Demo")}{d.fields?.industry ? ` · ${d.fields.industry}` : ""}</span>
                  </span>
                  {busy === label ? <Spinner className="text-muted" /> : <span className="text-[15px] text-accent">Screen</span>}
                </button>
              </Row>
            );
          })}
        </Section>
      )}

      {recent.length > 0 && (
        <Section title="This session">
          {recent.map((r) => (
            <Row key={r.memo_id}>
              <Link href={`/memos/${r.memo_id}`} className="flex items-center justify-between gap-3 active:opacity-60">
                <span className="min-w-0">
                  <span className="block truncate text-[17px]">{r.name}</span>
                  <span className="block truncate text-[13px] text-muted">{[r.company, relativeTime(r.at)].filter(Boolean).join(" · ")}</span>
                </span>
                <span className="flex items-center gap-2">
                  <span className={cx("text-[15px] tabular-nums text-muted")}>{percent(r.probability)}</span>
                  <DecisionPill decision={r.decision} size="sm" />
                </span>
              </Link>
            </Row>
          ))}
        </Section>
      )}

      <div className="mt-6 flex flex-wrap justify-center gap-1.5">
        <Chip>Public information only</Chip>
        <Chip>Nothing kept after the session</Chip>
      </div>
      <Disclaimer />
    </Page>
  );
}
