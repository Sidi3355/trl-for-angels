// Notes -> the screening form. The backend sorts a voice note or typed notes into template fields
// (POST /v1/notes/sort); this decides what the form takes from them. Rules:
// - a value the investor picked by hand is never overwritten (the note's version is reported instead);
// - a value an earlier note filled can be replaced by a newer note;
// - name, company and founding date fill only empty boxes;
// - every value filled from a note is remembered, so the form can mark it and voice ones are sent as
//   `voice_fields` (provenance "investor (voice)" in the memo).

import { FIELD_LABELS, fieldSummary } from "@/lib/format";
import type { FieldValues, NoteSortResponse } from "@/lib/types";

export type NoteSource = "voice" | "typed";

/** The template fields the form shows, and a note can fill. Education and jobs come from research. */
export const NOTE_FIELDS = [
  "industry", "cofounders", "background", "work_experience", "industry_experience", "prior_startups", "prior_exits",
] as const;
export type NoteField = (typeof NOTE_FIELDS)[number];
export type NoteValues = Partial<Pick<FieldValues, NoteField>>;

export interface NoteForm {
  who: string;
  company: string;
  founded: string;
  values: NoteValues;
  /** Which of `values` came from a note, and from which kind. */
  fromNote: Partial<Record<NoteField, NoteSource>>;
}

export interface NoteApplied {
  form: NoteForm;
  /** Plain descriptions of what was filled, e.g. "1 co-founder". */
  filled: string[];
  /** Fields where the investor's own answer was kept over the note's. */
  keptYours: string[];
}

export function valueSummary(key: NoteField, value: NonNullable<NoteValues[NoteField]>): string {
  const s = fieldSummary(key, value as FieldValues[typeof key]);
  const text = Array.isArray(s) ? s.join("; ") : s;
  if (key === "prior_startups") return value === "none" ? "First-time founder" : `Founded before: ${text}`;
  if (key === "prior_exits") return value === "none" ? "No prior exits" : `Exits: ${text}`;
  if (key === "industry_experience") return `${text} industry experience`;
  return text;
}

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

export function applyNoteSort(form: NoteForm, res: NoteSortResponse, source: NoteSource): NoteApplied {
  const values: NoteValues = { ...form.values };
  const fromNote = { ...form.fromNote };
  const filled: string[] = [];
  const keptYours: string[] = [];
  for (const key of NOTE_FIELDS) {
    const v = res.fields[key];
    if (v === undefined || v === "unknown") continue;
    const current = values[key];
    if (current !== undefined && !fromNote[key]) {
      if (!same(current, v)) keptYours.push(`${FIELD_LABELS[key]} (your note says ${valueSummary(key, v).toLowerCase()})`);
      continue;
    }
    (values as Record<string, unknown>)[key] = v;
    fromNote[key] = source;
    filled.push(valueSummary(key, v));
  }
  const next: NoteForm = { ...form, values, fromNote };
  if (!form.who.trim() && res.founder.name) {
    next.who = res.founder.name;
    filled.unshift(res.founder.name);
  }
  if (!form.company.trim() && res.founder.company_name) {
    next.company = res.founder.company_name;
    filled.push(res.founder.company_name);
  }
  if (!form.founded.trim() && res.founding_date) {
    next.founded = res.founding_date;
    filled.push(`founded ${res.founding_date}`);
  }
  return { form: next, filled, keptYours };
}

/** Fields to send with the screening, and which of them came from a voice note. */
export function formFields(values: NoteValues, fromNote: NoteForm["fromNote"]): { fields: NoteValues; voice: NoteField[] } {
  const fields: NoteValues = {};
  for (const key of NOTE_FIELDS) {
    let v = values[key];
    if (v === undefined || v === "") continue;
    if (key === "industry") {
      const t = String(v).trim().toLowerCase();
      if (!t) continue;
      v = t === "b2b saas" ? "B2B SaaS" : t;
    }
    (fields as Record<string, unknown>)[key] = v;
  }
  const voice = NOTE_FIELDS.filter((k) => fields[k] !== undefined && fromNote[k] === "voice");
  return { fields, voice };
}

/** The recorder's best format: webm/opus on Chrome and Android, mp4/aac on iPhone Safari. */
export function pickAudioType(isSupported: (t: string) => boolean): string {
  for (const t of ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/aac"]) {
    if (isSupported(t)) return t;
  }
  return "";
}
