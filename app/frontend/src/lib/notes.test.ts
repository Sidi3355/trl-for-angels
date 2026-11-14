import { describe, expect, it } from "vitest";

import { applyNoteSort, formFields, pickAudioType, type NoteForm } from "@/lib/notes";
import type { NoteSortResponse } from "@/lib/types";

const res = (over: Partial<NoteSortResponse> = {}): NoteSortResponse => ({
  schema_version: "0.1.0",
  fields: { cofounders: "1", background: "technical", work_experience: "5-10", prior_startups: "none", prior_exits: "none" },
  founder: { name: "Ada Moreno", company_name: "Tallyframe" },
  founding_date: null,
  evidence: [],
  kept_out: ["raised a seed round (after founding)"],
  sorter: "claude",
  ...over,
});
const empty: NoteForm = { who: "", company: "", founded: "", values: {}, fromNote: {} };

describe("applyNoteSort", () => {
  it("fills empty fields and boxes, and remembers where each came from", () => {
    const { form, filled, keptYours } = applyNoteSort(empty, res(), "voice");
    expect(form.values).toEqual(res().fields);
    expect(form.fromNote).toEqual({ cofounders: "voice", background: "voice", work_experience: "voice", prior_startups: "voice", prior_exits: "voice" });
    expect(form.who).toBe("Ada Moreno");
    expect(form.company).toBe("Tallyframe");
    expect(filled[0]).toBe("Ada Moreno");
    expect(filled).toContain("First-time founder");
    expect(keptYours).toEqual([]);
  });

  it("never overwrites what the investor picked, but a newer note replaces an older note", () => {
    const start: NoteForm = { ...empty, who: "A. Moreno", values: { cofounders: "2", background: "business" }, fromNote: { background: "typed" } };
    const { form, keptYours } = applyNoteSort(start, res(), "voice");
    expect(form.values.cofounders).toBe("2");
    expect(form.fromNote.cofounders).toBeUndefined();
    expect(keptYours).toHaveLength(1);
    expect(keptYours[0]).toBe("Founding team (your note says 1 co-founder)");
    expect(form.values.background).toBe("technical");
    expect(form.fromNote.background).toBe("voice");
    expect(form.who).toBe("A. Moreno");
  });

  it("lists prior exits from a note", () => {
    const r = res({ fields: { prior_startups: [{ outcome: "acquired", value_band: "$50M-$500M" }], prior_exits: [{ kind: "acquisition", value_band: "$50M-$500M" }] } });
    const { form, filled } = applyNoteSort(empty, r, "typed");
    expect(form.fromNote.prior_exits).toBe("typed");
    expect(filled.some((f) => f.startsWith("Exits:"))).toBe(true);
  });
});

describe("formFields", () => {
  it("sends only set fields, normalises industry, and names the voice ones", () => {
    const { fields, voice } = formFields(
      { industry: " B2B SaaS ", cofounders: "1", background: "technical" },
      { cofounders: "voice", background: "typed", industry: "voice" },
    );
    expect(fields).toEqual({ industry: "B2B SaaS", cofounders: "1", background: "technical" });
    expect(voice).toEqual(["industry", "cofounders"]);
  });
});

describe("pickAudioType", () => {
  it("prefers webm, and falls back to mp4 on iPhone", () => {
    expect(pickAudioType(() => true)).toBe("audio/webm;codecs=opus");
    expect(pickAudioType((t) => t === "audio/mp4")).toBe("audio/mp4");
    expect(pickAudioType(() => false)).toBe("");
  });
});
