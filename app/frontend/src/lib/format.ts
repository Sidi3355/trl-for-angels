// Plain-English labels for template values, controls and provenance.

import type {
  Decision,
  EducationEntry,
  FieldKey,
  FieldValues,
  JobEntry,
  PriorExit,
  PriorStartup,
  Provenance,
  Risk,
  Target,
  Timeline,
} from "./types";

export const FIELD_LABELS: Record<FieldKey, string> = {
  industry: "Industry",
  cofounders: "Founding team",
  background: "Background",
  work_experience: "Work experience",
  industry_experience: "Experience in this industry",
  education: "Education",
  jobs: "Jobs before founding",
  prior_startups: "Earlier startups",
  prior_exits: "Earlier exits",
};

export const DECISION_LABELS: Record<Decision, string> = { advance: "Advance", escalate: "Escalate", pass: "Pass" };
export const DECISION_HINTS: Record<Decision, string> = {
  advance: "Worth a meeting.",
  escalate: "Look closer before deciding.",
  pass: "Below your bar.",
};

export const TARGET_LABELS: Record<Target, string> = { "$50M": "$50M+", "$500M": "$500M+", "$1B": "$1B+" };
export const TIMELINE_LABELS: Record<string, string> = { null: "Any time", 8: "8 years", 5: "5 years" };
export const RISK_LABELS: Record<Risk, string> = { cautious: "Cautious", balanced: "Balanced", bold: "Bold" };
export const RISK_HINTS: Record<Risk, string> = {
  cautious: "Advances fewer founders, more of whom succeed.",
  balanced: "Advances about half of the founders who go on to succeed.",
  bold: "Advances more founders, catching more winners but more misses too.",
};

export function timelineLabel(t: Timeline): string {
  return TIMELINE_LABELS[String(t)];
}

export function percent(x: number | null | undefined, digits = 0): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "–";
  return `${(x * 100).toFixed(digits)}%`;
}

export function points(delta: number): string {
  const v = Math.round(delta * 100);
  return `${v > 0 ? "+" : v < 0 ? "−" : "±"}${Math.abs(v)} pts`;
}

export function foundedSource(p: Provenance | "assumed"): string {
  return p === "agent" ? "found by research" : p === "assumed" ? "assumed: today" : p === "unknown" ? "unknown" : "from you";
}

export function provenanceLabel(p: Provenance | "assumed", confidence?: number | null): string {
  switch (p) {
    case "investor":
      return "You";
    case "investor_voice":
      return "You (voice)";
    case "agent":
      return confidence !== null && confidence !== undefined ? `Agent · ${percent(confidence)}` : "Agent";
    case "assumed":
      return "Assumed";
    default:
      return "Unknown";
  }
}

const COFOUNDERS: Record<string, string> = {
  solo: "Solo founder",
  "1": "1 co-founder",
  "2": "2 co-founders",
  "3+": "3+ co-founders",
};
const WORK: Record<string, string> = {
  "<5": "Under 5 years",
  "5-10": "5–10 years",
  "10-15": "10–15 years",
  "15+": "15+ years",
};
const INDUSTRY_EXP: Record<string, string> = { none: "None", some: "Some", deep: "Deep" };

function cap(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

export function educationLine(e: EducationEntry): string {
  const degree = e.degree === "no degree" ? "Studied" : e.degree;
  const field = e.field === "unknown" ? "unknown field" : e.field;
  const qs = e.qs_rank === "unknown" ? "QS rank unknown" : e.qs_rank === "unranked" ? "not QS-ranked" : `QS ${e.qs_rank}`;
  return `${degree} ${e.degree === "no degree" ? field + " (no degree)" : "in " + field} · ${qs}`;
}

export function jobLine(j: JobEntry): { title: string; detail: string } {
  const size = j.company_size === "unknown" ? "size unknown" : `${j.company_size} employees`;
  const dur = j.duration === "unknown" ? "duration unknown" : `${j.duration} years`;
  return { title: `${j.role}, ${j.company}`, detail: `${j.industry} · ${size} · ${dur}`.replace(/(\d)-(\d)/g, "$1–$2") };
}

function startupLine(s: PriorStartup): string {
  if (s.outcome === "acquired" || s.outcome === "IPO") return `${s.outcome === "IPO" ? "IPO" : "Acquired"}, ${s.value_band}`;
  return cap(s.outcome);
}

function exitLine(x: PriorExit): string {
  return `${x.kind === "IPO" ? "IPO" : "Acquisition"}, ${x.value_band}`;
}

/** A short summary of a field value, or a list of lines for list fields. */
export function fieldSummary<K extends FieldKey>(key: K, value: FieldValues[K]): string | string[] {
  if (value === "unknown") return "Unknown";
  switch (key) {
    case "industry":
      return cap(value as string);
    case "cofounders":
      return COFOUNDERS[value as string] ?? String(value);
    case "background":
      return cap(value as string);
    case "work_experience":
      return WORK[value as string] ?? String(value);
    case "industry_experience":
      return INDUSTRY_EXP[value as string] ?? String(value);
    case "education":
      return (value as EducationEntry[]).map(educationLine);
    case "jobs":
      return (value as JobEntry[]).map((j) => {
        const { title, detail } = jobLine(j);
        return `${title} — ${detail}`;
      });
    case "prior_startups":
      return value === "none" ? "None" : (value as PriorStartup[]).map(startupLine);
    case "prior_exits":
      return value === "none" ? "None" : (value as PriorExit[]).map(exitLine);
  }
  return String(value);
}

/** 'jobs[2].company_size' -> 'Job 3: company size' */
export function unknownPathLabel(path: string): string {
  if (path === "founding_date") return "Founding date";
  const m = path.match(/^(\w+)(?:\[(\d+)\])?(?:\.(\w+))?$/);
  if (!m) return path;
  const [, key, idx, sub] = m;
  const base = FIELD_LABELS[key as FieldKey] ?? key;
  if (idx === undefined) return base;
  const item = key === "jobs" ? `Job ${Number(idx) + 1}` : key === "education" ? `Education ${Number(idx) + 1}` : `${base} ${Number(idx) + 1}`;
  return sub ? `${item}: ${sub.replace(/_/g, " ").replace("qs rank", "QS rank")}` : item;
}

export function foundedLabel(value: string): string {
  const [y, m] = value.split("-");
  if (!m) return y;
  const month = new Date(Number(y), Number(m) - 1, 1).toLocaleString("en", { month: "short" });
  return `${month} ${y}`;
}

export function relativeTime(iso: string): string {
  const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  return `${Math.round(s / 3600)} h ago`;
}

// ---- plain-language copy for the redesigned screens ----------------------------------------

export const DECISION_COPY: Record<Decision, { title: string; line: string }> = {
  advance: { title: "Advance", line: "Clears your bar. Worth a meeting." },
  escalate: { title: "Escalate", line: "Close to your bar. Take a closer look before you decide." },
  pass: { title: "Pass", line: "Below your bar." },
};

export function targetShort(t: Target): string {
  return TARGET_LABELS[t];
}

/** "a $500M+ outcome" or "$500M+ within 8 years" */
export function chanceOf(target: Target, timeline: Timeline): string {
  return timeline ? `${TARGET_LABELS[target]} within ${timeline} years` : `a ${TARGET_LABELS[target]} outcome`;
}

export function answerLabel(v: unknown): string {
  if (typeof v !== "string") return JSON.stringify(v);
  return v.length ? v.charAt(0).toUpperCase() + v.slice(1) : v;
}

export function sectorLabel(s: string | null | undefined): string | null {
  if (!s || s === "unknown") return null;
  return s === "B2B SaaS" ? s : s.charAt(0).toUpperCase() + s.slice(1);
}

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
