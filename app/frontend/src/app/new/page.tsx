"use client";

// New screening: who, plus anything the investor already knows. Everything but the founder is optional.
// Notes can be spoken (a voice note) or typed; either can fill the form, and the investor checks every
// value before screening. The notes themselves go to the memo only, never to the model.
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { useApp } from "@/components/AppState";
import { Examples } from "@/components/Examples";
import { IconChevronDown } from "@/components/icons";
import { Button, Card, ChipPicker, Disclaimer, Notice, Page, PageHeader, Spinner, Switch, Tag, cx, linkClass } from "@/components/ui";
import { VoiceNote, type VoicePhase } from "@/components/VoiceNote";
import { ApiError, api } from "@/lib/api";
import { applyNoteSort, formFields, valueSummary, type NoteField, type NoteForm, type NoteSource, type NoteValues } from "@/lib/notes";
import type { NoteTranscript } from "@/lib/types";
import { parseFounder, useStartScreening } from "@/lib/useScreening";

const INDUSTRIES = [
  "fintech", "healthtech", "biotech", "B2B SaaS", "developer tools", "e-commerce", "logistics", "edtech", "climate",
  "cybersecurity", "marketplaces", "media", "hardware", "insurtech", "agtech", "gaming", "proptech", "HR tech", "travel", "food",
];
const DATE_RE = /^[0-9]{4}(-(0[1-9]|1[0-2]))?$/;

const CHIP_FIELDS = [
  ["cofounders", "Founding team", [["solo", "Solo"], ["1", "1 co-founder"], ["2", "2 co-founders"], ["3+", "3+"]]],
  ["background", "Background", [["technical", "Technical"], ["business", "Business"], ["mixed", "Mixed"], ["domain specialist", "Domain specialist"]]],
  ["work_experience", "Work experience", [["<5", "Under 5 yrs"], ["5-10", "5–10 yrs"], ["10-15", "10–15 yrs"], ["15+", "15+ yrs"]]],
  ["industry_experience", "Experience in this industry", [["none", "None"], ["some", "Some"], ["deep", "Deep"]]],
  ["prior_startups", "Founded a company before?", [["none", "No, first time"]]],
  ["prior_exits", "Sold a company before?", [["none", "No"]]],
] as const;

type NoteMessage = { tone: "info" | "danger" | "done"; title: string; lines?: string[] };

function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="px-4 py-3.5 transition-colors focus-within:bg-surface-2">
      <label htmlFor={id} className="eyebrow block text-muted">
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-[12.5px] text-faint">{hint}</p>}
    </div>
  );
}

function FromNote({ source }: { source?: NoteSource }) {
  if (!source) return null;
  return <Tag tone="good">{source === "voice" ? "From your voice note" : "From your notes"}</Tag>;
}

const input = "mt-1.5 w-full bg-transparent text-[17px] font-medium outline-none placeholder:font-normal placeholder:text-faint";

function NewScreening() {
  const params = useSearchParams();
  const { health } = useApp();
  const [who, setWho] = useState(params.get("q") ?? "");
  const [company, setCompany] = useState("");
  const [founded, setFounded] = useState("");
  const [notes, setNotes] = useState("");
  const [research, setResearch] = useState(true);
  const [values, setValues] = useState<NoteValues>({});
  const [fromNote, setFromNote] = useState<NoteForm["fromNote"]>({});
  const [open, setOpen] = useState(false);
  const [voicePhase, setVoicePhase] = useState<VoicePhase>("idle");
  const [sorting, setSorting] = useState(false);
  const [sortedText, setSortedText] = useState("");
  const [noteMsg, setNoteMsg] = useState<NoteMessage | null>(null);
  const { start, busy, error, setError } = useStartScreening();
  const msgRef = useRef<HTMLDivElement>(null);
  const knownCount = Object.keys(values).length;
  // The result of a note lands under the notes box; bring it into view above the sticky button.
  useEffect(() => {
    if (!noteMsg) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    msgRef.current?.scrollIntoView({ block: "nearest", behavior: still ? "auto" : "smooth" });
  }, [noteMsg]);
  const sorterOff = health?.components.note_sorter === "off";
  const noteBusy = sorting || voicePhase !== "idle";

  function setField(key: NoteField, v: string) {
    setValues((prev) => {
      const next = { ...prev };
      if (v === "" || v === "listed") {
        if (v === "") delete next[key];
      } else (next as Record<string, unknown>)[key] = v;
      return next;
    });
    setFromNote((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }

  async function sortNotes(text: string, source: NoteSource, transcript?: NoteTranscript) {
    const added = source === "voice" ? "Added to your notes." : "";
    const example = transcript?.example ? ["This is an example transcript: speech-to-text isn't set up on this server yet."] : [];
    if (sorterOff) {
      setNoteMsg({
        tone: "info",
        title: added || "Can't fill the form from notes yet",
        lines: [...example, "Filling the form from notes isn't switched on for this server yet (it needs the Claude key)."],
      });
      return;
    }
    setSorting(true);
    try {
      const res = await api.sortNote({ schema_version: "0.1.0", text, ...(DATE_RE.test(founded.trim()) && { founding_date: founded.trim() }) });
      const applied = applyNoteSort({ who, company, founded, values, fromNote }, res, source);
      setWho(applied.form.who);
      setCompany(applied.form.company);
      setFounded(applied.form.founded);
      setValues(applied.form.values);
      setFromNote(applied.form.fromNote);
      if (Object.keys(res.fields).length) setOpen(true);
      const lines = [
        ...example,
        ...(applied.keptYours.length ? [`Kept your answers for: ${applied.keptYours.join("; ")}.`] : []),
        ...(res.kept_out.length ? [`Kept in your notes only: ${res.kept_out.join("; ")}.`] : []),
        ...(applied.filled.length ? ["Check them below before you screen."] : []),
      ];
      setNoteMsg(
        applied.filled.length
          ? { tone: "done", title: `${added ? added + " " : ""}Filled in: ${applied.filled.join(" · ")}`, lines }
          : { tone: "info", title: `${added ? added + " " : ""}Nothing in it fits the form, so it stays as notes.`, lines },
      );
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Couldn't fill the form from your notes. Try again.";
      setNoteMsg({ tone: e instanceof ApiError && e.status === 503 ? "info" : "danger", title: added || "Couldn't fill the form", lines: [...example, msg] });
    } finally {
      setSorting(false);
    }
  }

  function onVoiceText(t: NoteTranscript) {
    const text = t.text.trim();
    if (!text) {
      setNoteMsg({ tone: "danger", title: "Didn't catch any words. Try again a little closer to the phone." });
      return;
    }
    const next = notes.trim() ? `${notes.trim()}\n\n${text}` : text;
    setNotes(next);
    setSortedText(next);
    void sortNotes(text, "voice", t);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const founder = parseFounder(who);
    if (!founder) return setError("Add the founder's name, or a LinkedIn or website link.");
    if (founded.trim() && !DATE_RE.test(founded.trim())) return setError("Write the founding date as a year, or year and month: 2021 or 2021-06.");
    const { fields, voice } = formFields(values, fromNote);
    start({
      founder: { ...founder, ...(company.trim() && { company_name: company.trim() }) },
      ...(founded.trim() && { founding_date: founded.trim() }),
      ...(Object.keys(fields).length && { fields }),
      ...(voice.length && { voice_fields: voice }),
      ...(notes.trim() && { notes: notes.trim() }),
      options: { research },
    });
  }

  const showFillLink = !sorterOff && notes.trim().length >= 15 && notes !== sortedText && !noteBusy;

  return (
    <Page>
      <PageHeader title="Screen a founder" subtitle="Say who. Anything else you know sharpens the result, and your answers always win over the agent's." />

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
          <div className="px-4 py-3.5 transition-colors focus-within:bg-surface-2">
            <div className="flex items-center justify-between gap-3">
              <label htmlFor="notes" className="eyebrow block text-muted">
                Your notes
              </label>
              <VoiceNote onText={onVoiceText} onPhase={setVoicePhase} disabled={sorting} onError={(m) => setNoteMsg({ tone: "danger", title: m })} />
            </div>
            <textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Talk or type: the meeting, their background, traction, your gut feel…"
              className={cx(input, "mt-2 resize-none")}
            />
            <p className="mt-1 text-[12.5px] text-faint">Your notes go in the memo, never to the model. Facts in them can fill the form below, for you to check.</p>
            {showFillLink && (
              <button type="button" onClick={() => { setSortedText(notes); void sortNotes(notes, "typed"); }} className={cx(linkClass, "mt-2.5 text-[14.5px] font-semibold")}>
                Fill the form from my notes
              </button>
            )}
            {sorting && (
              <p className="mt-2.5 flex items-center gap-2 text-[14px] text-muted" role="status">
                <Spinner /> Filling the form from your notes…
              </p>
            )}
          </div>
          {noteMsg && !sorting && (
            <div ref={msgRef} className="border-t border-line px-4 py-3" aria-live="polite">
              {noteMsg.tone === "done" ? (
                <div className="text-[14px] leading-snug">
                  <p className="font-bold text-advance">{noteMsg.title}</p>
                  {noteMsg.lines?.map((l) => (
                    <p key={l} className="mt-1 text-muted">
                      {l}
                    </p>
                  ))}
                </div>
              ) : (
                <Notice tone={noteMsg.tone === "danger" ? "danger" : "info"} title={noteMsg.title}>
                  {noteMsg.lines?.map((l) => <p key={l}>{l}</p>)}
                </Notice>
              )}
            </div>
          )}
        </Card>

        <Card className="overflow-hidden">
          <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left">
            <span>
              <span className="block text-[17px] font-bold tracking-[-0.01em]">
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
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <label htmlFor="industry" className="text-[15px] font-bold tracking-[-0.01em]">
                    Industry
                  </label>
                  <FromNote source={fromNote.industry} />
                </div>
                <input
                  id="industry"
                  list="industries"
                  value={typeof values.industry === "string" ? values.industry : ""}
                  onChange={(e) => setField("industry", e.target.value)}
                  placeholder="e.g. fintech"
                  autoComplete="off"
                  className="h-12 w-full rounded-[12px] border border-line-strong bg-surface px-3.5 outline-none transition-colors placeholder:text-faint focus:border-ink"
                />
                <datalist id="industries">
                  {INDUSTRIES.map((i) => (
                    <option key={i} value={i} />
                  ))}
                </datalist>
              </div>
              {CHIP_FIELDS.map(([key, label, opts]) => {
                const v = values[key];
                const listed = Array.isArray(v);
                const options = [
                  ...opts.map(([value, l]) => ({ value: value as string, label: l as string })),
                  ...(listed ? [{ value: "listed", label: valueSummary(key, v) }] : []),
                ];
                return (
                  <div key={key}>
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <p className="text-[15px] font-bold tracking-[-0.01em]">{label}</p>
                      <FromNote source={fromNote[key]} />
                    </div>
                    <ChipPicker label={label} value={listed ? "listed" : typeof v === "string" ? v : ""} onChange={(nv) => setField(key, nv)} options={options} />
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card className="flex items-center justify-between gap-4 px-4 py-4">
          <label htmlFor="research" className="min-w-0">
            <span className="block text-[16px] font-bold tracking-[-0.01em]">Web research</span>
            <span className="block text-[13px] text-muted">{research ? "The agent fills in what you leave blank, with sources." : "Use only what you entered."}</span>
          </label>
          <Switch id="research" label="Web research" checked={research} onChange={setResearch} />
        </Card>

        {error && <Notice tone="danger">{error}</Notice>}

        <div className="sticky bottom-[calc(var(--dock-clear)-4px)] z-10 -mx-1 rounded-full bg-bg/85 p-1 backdrop-blur lg:static lg:mx-0 lg:bg-transparent lg:p-0 lg:backdrop-blur-none">
          <Button type="submit" size="lg" full disabled={busy !== null || noteBusy}>
            {busy === "main" && <Spinner />} Screen founder
          </Button>
        </div>
      </form>

      <p className="mt-6 text-[14px] text-muted">
        Got a list of founders?{" "}
        <Link href="/batch" className={linkClass}>
          Screen a whole list from a spreadsheet
        </Link>
      </p>

      <section className="mt-10" aria-labelledby="ex">
        <h2 id="ex" className="eyebrow mb-3 text-muted">
          Or try an example
        </h2>
        <Examples onPick={(i, key) => start(i, key)} busy={busy} columns />
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
