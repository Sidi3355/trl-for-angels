"use client";

// The memo: verdict at the investor's controls, what drives it, what-ifs, and the evidence.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Controls } from "@/components/memo/Controls";
import { Conflicts, DistributionsView, ModelInput, Notes, ProfileFields, Sources, Unknowns } from "@/components/memo/Details";
import { Drivers } from "@/components/memo/Drivers";
import { VerdictCard } from "@/components/memo/VerdictCard";
import { Disclaimer, Notice, Page, Section, Spinner, TopBar } from "@/components/ui";
import { api, type ApiError } from "@/lib/api";
import { foundedLabel, foundedSource } from "@/lib/format";
import { resolve, verdict as computeVerdict, withDefaults, type Policy } from "@/lib/policy";
import { rememberScreening } from "@/lib/session";
import { SCHEMA_VERSION, type Driver, type FieldValues, type Memo, type Thresholds, type WhatIfChange, type WhatIfResponse } from "@/lib/types";

function plainFields(memo: Memo): FieldValues {
  return Object.fromEntries(Object.entries(memo.fields).map(([k, f]) => [k, f.value])) as unknown as FieldValues;
}

function changeFor(d: Driver): WhatIfChange {
  return d.kind === "answer"
    ? { kind: "answer", rule_id: d.id, value: d.flipped as "yes" | "no" }
    : { kind: "field", key: d.id as keyof FieldValues, value: d.flipped };
}

export function MemoView({ memoId }: { memoId: string }) {
  const [memo, setMemo] = useState<Memo | null>(null);
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [policy, setPolicy] = useState<Policy | null>(null);

  const [flipped, setFlipped] = useState<Map<string, Driver>>(new Map());
  const [whatIf, setWhatIf] = useState<WhatIfResponse | null>(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);
  const [whatIfError, setWhatIfError] = useState<string | null>(null);
  const requestNo = useRef(0);

  useEffect(() => {
    Promise.all([api.memo(memoId), api.thresholds()]).then(
      ([m, t]) => {
        setMemo(m);
        setThresholds(t);
        setPolicy(withDefaults(m.verdict.policy));
        rememberScreening({
          memo_id: m.memo_id,
          name: m.founder.display_name,
          company: m.founder.company_name,
          decision: m.verdict.decision,
          probability: m.verdict.probability,
          at: m.created_at,
        });
      },
      (e: ApiError) => {
        if (e.status !== 401) setError(e.message);
      },
    );
  }, [memoId]);

  const fields = useMemo(() => (memo ? plainFields(memo) : null), [memo]);

  const runWhatIf = useCallback(
    async (next: Map<string, Driver>) => {
      const n = ++requestNo.current;
      setWhatIfError(null);
      if (!next.size) {
        setWhatIf(null);
        setWhatIfLoading(false);
        return;
      }
      setWhatIfLoading(true);
      try {
        const res = await api.whatIf(memoId, { schema_version: SCHEMA_VERSION, changes: [...next.values()].map(changeFor) });
        if (n === requestNo.current) setWhatIf(res);
      } catch (e) {
        if (n === requestNo.current) setWhatIfError((e as ApiError).message);
      } finally {
        if (n === requestNo.current) setWhatIfLoading(false);
      }
    },
    [memoId],
  );

  const toggle = (d: Driver) => {
    const next = new Map(flipped);
    if (next.has(d.id)) next.delete(d.id);
    else next.set(d.id, d);
    setFlipped(next);
    runWhatIf(next);
  };
  const reset = () => {
    setFlipped(new Map());
    runWhatIf(new Map());
  };

  if (error) {
    return (
      <Page>
        <TopBar back={{ href: "/", label: "New" }} />
        <div className="mt-6">
          <Notice tone="danger">{error}</Notice>
        </div>
      </Page>
    );
  }
  if (!memo || !thresholds || !policy || !fields) {
    return (
      <Page>
        <TopBar back={{ href: "/", label: "New" }} />
        <div className="mt-24 flex justify-center text-muted">
          <Spinner className="h-6 w-6" />
        </div>
      </Page>
    );
  }

  const resolved = resolve(thresholds, policy);
  const baseline = computeVerdict(memo.distributions, thresholds, policy, fields);
  const current = whatIf ? computeVerdict(whatIf.distributions, thresholds, policy, fields) : baseline;
  const fd = memo.founder.founding_date;
  const otherWarnings = memo.warnings.filter((w) => w.code !== "mock_artifacts");
  const mockWarning = memo.warnings.find((w) => w.code === "mock_artifacts");
  const links = [
    memo.founder.identifier.linkedin_url && { href: memo.founder.identifier.linkedin_url, label: "LinkedIn" },
    memo.founder.identifier.website_url && { href: memo.founder.identifier.website_url, label: "Website" },
  ].filter(Boolean) as { href: string; label: string }[];
  const fieldWhatIf = memo.what_if.field_changes;
  const driversSupported = memo.drivers.every((d) => (d.kind === "answer" ? memo.what_if.answer_changes === "supported" : fieldWhatIf !== "unsupported"));

  return (
    <Page>
      <TopBar back={{ href: "/", label: "New" }} />

      <header className="mt-1">
        <h1 className="text-[28px] font-bold leading-tight tracking-tight">{memo.founder.display_name}</h1>
        <p className="mt-0.5 text-[15px] text-muted">
          {[memo.founder.company_name, `Founded ${foundedLabel(fd.value)}, ${foundedSource(fd.provenance)}`].filter(Boolean).join(" · ")}
        </p>
        {links.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-x-3 text-[15px]">
            {links.map((l) => (
              <a key={l.label} href={l.href} target="_blank" rel="noopener noreferrer" className="text-accent">
                {l.label}
              </a>
            ))}
          </div>
        )}
      </header>

      {memo.mock && (
        <div className="mt-4">
          <Notice tone="info">
            <strong className="font-semibold">Prototype memo.</strong> {mockWarning?.message ?? "Parts of this memo are mocked."}
          </Notice>
        </div>
      )}

      <div className="mt-4">
        <VerdictCard verdict={current} resolved={resolved} baseline={whatIf ? baseline : null} whatIfActive={flipped.size > 0} whatIfLoading={whatIfLoading} onResetWhatIf={reset} />
      </div>

      {otherWarnings.length > 0 && (
        <div className="mt-3 space-y-2">
          {otherWarnings.map((w) => (
            <Notice key={w.code} tone="warn">
              {w.message}
            </Notice>
          ))}
        </div>
      )}

      <Section title="Your controls" footer="Changes apply instantly, on your phone. No new research or scoring.">
        <Controls policy={policy} onChange={setPolicy} facets={memo.facets} />
      </Section>

      <Section
        title="What moves this score"
        footer={
          whatIfError ? (
            <span className="text-danger">{whatIfError}</span>
          ) : memo.decider.input_type === "answers" ? (
            "Each line is one screening question. “Try” re-scores with that answer flipped; nothing is researched again."
          ) : (
            "Each line is one profile field. “Try” re-scores with it changed."
          )
        }
      >
        <Drivers drivers={memo.drivers} base={memo.distributions} policy={policy} flipped={new Set(flipped.keys())} onToggle={toggle} loading={whatIfLoading} supported={driversSupported} />
      </Section>

      <Section title="Predicted outcome">
        <DistributionsView d={whatIf ? whatIf.distributions : memo.distributions} policy={policy} />
      </Section>

      <Section title="Founder profile" footer="As of the founding date. “You” means your input, which wins over the agent's findings.">
        <ProfileFields memo={memo} />
      </Section>

      {memo.conflicts.length > 0 && (
        <Section title="Conflicts">
          <Conflicts conflicts={memo.conflicts} />
        </Section>
      )}

      {memo.unknowns.length > 0 && (
        <Section title="Unknown" footer="Unknown fields make the score less certain. Add what you know and screen again.">
          <Unknowns paths={memo.unknowns} />
        </Section>
      )}

      {(memo.notes.investor || memo.notes.post_founding.length > 0) && (
        <Section title="Notes" footer="Memo only. Never sent to the model.">
          <Notes memo={memo} />
        </Section>
      )}

      {memo.sources.length > 0 && (
        <Section title={`Sources (${memo.sources.length})`}>
          <Sources sources={memo.sources} />
        </Section>
      )}

      <Section>
        <ModelInput memo={memo} />
      </Section>

      <Disclaimer text={memo.disclaimer} />
    </Page>
  );
}
