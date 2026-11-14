// TypeScript mirror of the app contract (app/contract/schemas, version 0.1.0).
// The schemas are the source of truth; change them first, then this file.

export const SCHEMA_VERSION = "0.1.0";

export const OUTCOME_BANDS = ["shut down", "under $50M", "$50M-$500M", "$500M-$1B", "over $1B"] as const;
export const YEARS_BANDS = ["under 5", "5-8", "over 8"] as const;
export type OutcomeBand = (typeof OUTCOME_BANDS)[number];
export type YearsBand = (typeof YEARS_BANDS)[number];

export type Target = "$50M" | "$500M" | "$1B";
export type Timeline = null | 5 | 8;
export type Risk = "cautious" | "balanced" | "bold";
export type Decision = "advance" | "escalate" | "pass";
export type Provenance = "investor" | "investor_voice" | "agent" | "unknown";

export interface Distributions {
  outcome: Record<OutcomeBand, number>;
  years: Record<YearsBand, number>;
}

export interface Filters {
  sectors?: string[] | null;
  team?: "solo" | "team" | null;
  technical?: boolean | null;
  repeat_founder?: boolean | null;
}

export interface PolicyRequest {
  target?: Target;
  timeline_years?: Timeline;
  risk?: Risk;
  filters?: Filters;
}

export interface PolicyUsed {
  target: Target;
  timeline_years: Timeline;
  risk: Risk;
  filters?: Filters;
  advance_threshold: number | null;
  pass_threshold: number | null;
}

export interface Verdict {
  decision: Decision;
  probability: number;
  probability_is_estimate: boolean;
  policy: PolicyUsed;
  expected_precision: number | null;
  expected_recall: number | null;
  missed_winners_if_pass: number | null;
  filters_failed: string[];
  summary: string;
}

export interface Facets {
  sector: string | null;
  team: "solo" | "team" | null;
  technical: boolean | null;
  repeat_founder: boolean | null;
}

// ---- template fields ----------------------------------------------------------------------

export type Unknown = "unknown";
export type Cofounders = "solo" | "1" | "2" | "3+" | Unknown;
export type Background = "technical" | "business" | "mixed" | "domain specialist" | Unknown;
export type WorkExperience = "<5" | "5-10" | "10-15" | "15+" | Unknown;
export type IndustryExperience = "none" | "some" | "deep" | Unknown;
export type QsRank = "top 50" | "51-100" | "101-300" | "300+" | "unranked" | Unknown;
export type CompanySize = "1-10" | "11-50" | "51-200" | "201-1,000" | "1,001-5,000" | "5,000+" | Unknown;
export type JobDuration = "<1" | "1-2" | "2-3" | "3-5" | "5+" | Unknown;
export type ValueBand = "under $50M" | "$50M-$500M" | "$500M-$1B" | "over $1B";

export interface EducationEntry {
  degree: string;
  field: string;
  qs_rank: QsRank;
}
export interface JobEntry {
  role: string;
  company: string;
  company_size: CompanySize;
  industry: string;
  duration: JobDuration;
}
export interface PriorStartup {
  outcome: "shut down" | "acquired" | "IPO" | "still operating";
  value_band: ValueBand | null;
}
export interface PriorExit {
  kind: "acquisition" | "IPO";
  value_band: ValueBand;
}

export interface FieldValues {
  industry: string;
  cofounders: Cofounders;
  background: Background;
  work_experience: WorkExperience;
  industry_experience: IndustryExperience;
  education: EducationEntry[] | Unknown;
  jobs: JobEntry[] | Unknown;
  prior_startups: PriorStartup[] | "none" | Unknown;
  prior_exits: PriorExit[] | "none" | Unknown;
}
export type FieldKey = keyof FieldValues;
export const FIELD_KEYS: FieldKey[] = [
  "industry", "cofounders", "background", "work_experience", "industry_experience",
  "education", "jobs", "prior_startups", "prior_exits",
];

export interface FieldMeta<V> {
  value: V;
  provenance: Provenance;
  source_ids: string[];
  confidence: number | null;
  note?: string | null;
}
export type MemoFields = { [K in FieldKey]: FieldMeta<FieldValues[K]> };

// ---- requests -----------------------------------------------------------------------------

export interface FounderIdentifier {
  name?: string;
  company_name?: string;
  linkedin_url?: string;
  linkedin_text?: string;
  website_url?: string;
  deck_text?: string;
  other_urls?: string[];
}

export interface InvestorInput {
  schema_version: typeof SCHEMA_VERSION;
  client_ref?: string;
  founder: FounderIdentifier;
  founding_date?: string;
  fields?: Partial<FieldValues>;
  voice_fields?: FieldKey[];
  notes?: string | null;
  policy?: PolicyRequest;
  options?: { research?: boolean; max_searches?: number; use_demo_cache?: boolean };
}

export interface ApiErrorBody {
  code: string;
  message: string;
  retryable: boolean;
}

export type Stage =
  | "queued" | "researching" | "merging" | "rendering" | "answering" | "deciding" | "writing_memo" | "done" | "failed";

export interface ScreeningJob {
  schema_version: string;
  job_id: string;
  client_ref?: string | null;
  status: "queued" | "running" | "complete" | "failed";
  stage?: Stage;
  created_at: string;
  events_url: string;
  memo_id: string | null;
  memo_url: string | null;
  error: ApiErrorBody | null;
}

export type EventType =
  | "stage" | "search" | "source" | "field" | "conflict" | "warning" | "error" | "memo_ready" | "batch_item" | "heartbeat";
export const EVENT_TYPES: EventType[] = [
  "stage", "search", "source", "field", "conflict", "warning", "error", "memo_ready", "batch_item", "heartbeat",
];

export interface ProgressEvent {
  schema_version: string;
  job_id: string;
  seq: number;
  ts: string;
  type: EventType;
  stage?: Stage;
  message: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data?: Record<string, any>;
}

// ---- memo ---------------------------------------------------------------------------------

export interface Source {
  id: string;
  url: string;
  title: string;
  publisher?: string | null;
  published_date?: string | null;
  accessed_at: string;
  before_founding: boolean | null;
  used_for: string[];
}

export interface Conflict {
  field: string;
  investor_value: unknown;
  agent_value: unknown;
  agent_source_ids: string[];
  resolution: "investor_value_used";
  note?: string | null;
}

export interface Answer {
  rule_id: string;
  p_yes: number;
  answer: string;
}

export interface Driver {
  id: string;
  kind: "answer" | "field";
  label: string;
  current: unknown;
  flipped: unknown;
  distributions: Distributions;
  delta: number;
}

export type WarningCode =
  | "mock_artifacts" | "many_unknowns" | "founding_date_assumed" | "conflicts_present" | "research_partial"
  | "thresholds_sparse" | "timeline_estimate" | "profile_inconsistent" | "redacted";

export interface MemoWarning {
  code: WarningCode;
  message: string;
}

export interface Memo {
  schema_version: string;
  memo_id: string;
  job_id?: string | null;
  client_ref?: string | null;
  created_at: string;
  mock: boolean;
  founder: {
    display_name: string;
    company_name: string | null;
    identifier: FounderIdentifier;
    founding_date: { value: string; provenance: "investor" | "investor_voice" | "agent" | "assumed"; source_ids: string[] };
  };
  verdict: Verdict;
  distributions: Distributions;
  fields: MemoFields;
  rendered_profile: string;
  decider: { input_type: "answers" | "profile"; model_id: string; artifacts_dir: string };
  answers: Answer[] | null;
  drivers: Driver[];
  what_if: { answer_changes: "supported" | "unsupported"; field_changes: "supported" | "needs_answerer" | "unsupported" };
  facets: Facets;
  sources: Source[];
  conflicts: Conflict[];
  unknowns: string[];
  notes: { investor: string | null; post_founding: { text: string; source_ids: string[] }[] };
  warnings: MemoWarning[];
  disclaimer: string;
}

// ---- what-if ------------------------------------------------------------------------------

export type WhatIfChange =
  | { kind: "answer"; rule_id: string; value: "yes" | "no" }
  | { kind: "field"; key: FieldKey; value: unknown };

export interface WhatIfRequest {
  schema_version: typeof SCHEMA_VERSION;
  changes: WhatIfChange[];
  policy?: PolicyRequest;
}

export interface WhatIfResponse {
  schema_version: string;
  memo_id: string;
  changes: WhatIfChange[];
  used_answerer: boolean;
  baseline: Distributions;
  distributions: Distributions;
  verdict: Verdict;
  rendered_profile: string | null;
  answers_changed: string[];
  mock: boolean;
}

// ---- artefacts ----------------------------------------------------------------------------

export interface ThresholdRow {
  threshold: number;
  n_flagged: number;
  tp: number;
  precision: number | null;
  recall: number | null;
}
export interface ThresholdTable {
  target: Target;
  timeline_years: Timeline;
  n: number;
  n_positive: number;
  base_rate: number;
  rows: ThresholdRow[];
}
export interface Thresholds {
  schema_version: string;
  mock: boolean;
  tables: ThresholdTable[];
}

export interface Health {
  status: "ok" | "degraded";
  env: string;
  components: { agent: string; answerer: string; decider: string };
  mock: boolean;
  errors: Record<string, string>;
}
