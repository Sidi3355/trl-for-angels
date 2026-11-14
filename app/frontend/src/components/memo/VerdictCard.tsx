// The verdict at the current controls: decision, probability, where it sits against the thresholds,
// and what the thresholds mean on validation data.
import { Chip, DecisionPill, cx } from "@/components/ui";
import { DECISION_HINTS, TARGET_LABELS, percent } from "@/lib/format";
import type { Resolved } from "@/lib/policy";
import type { Verdict } from "@/lib/types";

function niceMax(x: number): number {
  for (const m of [0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1]) if (x <= m) return m;
  return 1;
}

function Track({ prob, advance, pass, baseline }: { prob: number; advance: number | null; pass: number | null; baseline?: number }) {
  const max = niceMax(Math.max(prob, baseline ?? 0, advance ?? 0, pass ?? 0) * 1.25 || 0.1);
  const at = (x: number) => `${Math.min(100, (x / max) * 100)}%`;
  const p = pass ?? 0;
  const a = advance ?? max;
  // Keep the tick labels apart: merge them when the thresholds coincide, push them apart when close.
  const near = pass !== null && advance !== null && Math.abs(advance - pass) / max < 0.12;
  const same = pass !== null && advance !== null && percent(advance) === percent(pass);
  const showZero = (pass ?? advance ?? max) / max > 0.1;
  return (
    <div className="mt-5" aria-hidden>
      <div className="relative h-2.5 overflow-hidden rounded-full bg-pass/20">
        <div className="absolute inset-y-0 bg-escalate/35" style={{ left: at(p), width: `calc(${at(a)} - ${at(p)})` }} />
        <div className="absolute inset-y-0 right-0 bg-advance/35" style={{ left: at(a) }} />
      </div>
      <div className="relative h-0">
        {baseline !== undefined && (
          <span className="absolute -top-[15px] h-4 w-4 -translate-x-1/2 rounded-full border-2 border-dashed border-muted bg-card/60" style={{ left: at(baseline) }} />
        )}
        <span className="absolute -top-[17px] h-5 w-5 -translate-x-1/2 rounded-full border-[3px] border-card bg-ink shadow" style={{ left: at(prob) }} />
      </div>
      <div className="relative mt-2 h-4 text-[11px] tabular-nums text-muted">
        {showZero && <span className="absolute left-0">0%</span>}
        {pass !== null && !same && (
          <span className={cx("absolute", near ? "-translate-x-full pr-1" : "-translate-x-1/2")} style={{ left: at(pass) }}>
            {percent(pass)}
          </span>
        )}
        {advance !== null && (
          <span className={cx("absolute", near && !same ? "pl-1" : "-translate-x-1/2")} style={{ left: at(advance) }}>
            {percent(advance)}
          </span>
        )}
        <span className="absolute right-0">{percent(max)}</span>
      </div>
      <div className="mt-1 flex justify-between text-[11px] font-medium">
        <span className="text-pass">Pass</span>
        <span className="text-escalate">Escalate</span>
        <span className="text-advance">Advance</span>
      </div>
    </div>
  );
}

export function VerdictCard({
  verdict,
  resolved,
  baseline,
  whatIfActive,
  whatIfLoading,
  onResetWhatIf,
}: {
  verdict: Verdict;
  resolved: Resolved;
  baseline: Verdict | null;
  whatIfActive: boolean;
  whatIfLoading: boolean;
  onResetWhatIf: () => void;
}) {
  const pol = verdict.policy;
  const target = TARGET_LABELS[pol.target];
  const horizon = pol.timeline_years ? ` within ${pol.timeline_years} years` : "";
  const filtered = verdict.filters_failed.length > 0;

  return (
    <div className={cx("rounded-3xl bg-card p-5 transition-opacity", whatIfLoading && "opacity-70")}>
      <div className="flex items-center justify-between gap-2">
        <DecisionPill decision={verdict.decision} size="lg" />
        {whatIfActive && (
          <button type="button" onClick={onResetWhatIf} className="rounded-full bg-accent-soft px-3 py-1 text-[13px] font-medium text-accent active:opacity-60">
            What-if on · Reset
          </button>
        )}
      </div>
      <p className="mt-1.5 text-[15px] text-muted">{DECISION_HINTS[verdict.decision]}</p>

      <div className="mt-4 flex items-baseline gap-2">
        <span className="text-[44px] font-bold leading-none tracking-tight tabular-nums">
          {verdict.probability_is_estimate ? "≈" : ""}
          {percent(verdict.probability)}
        </span>
        {baseline && baseline.probability !== verdict.probability && (
          <span className="text-[17px] tabular-nums text-muted line-through">{percent(baseline.probability)}</span>
        )}
      </div>
      <p className="mt-1 text-[15px] leading-snug text-ink-2">
        chance of reaching {target}
        {horizon}
        {verdict.probability_is_estimate && <span className="text-muted"> (estimate: assumes outcome size and timing are independent)</span>}
      </p>

      <Track prob={verdict.probability} advance={pol.advance_threshold} pass={pol.pass_threshold} baseline={whatIfActive && baseline ? baseline.probability : undefined} />

      {filtered && (
        <p className="mt-4 rounded-xl bg-warn-soft px-3 py-2 text-[14px] text-warn">
          Outside your filters: {verdict.filters_failed.map((f) => f.replace("_", " ")).join(", ")}.
        </p>
      )}

      <dl className="mt-5 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-2xl bg-card-2 px-2 py-2.5">
          <dt className="text-[11px] leading-tight text-muted">Hit rate when advanced</dt>
          <dd className="mt-1 text-[20px] font-semibold tabular-nums">{percent(verdict.expected_precision)}</dd>
        </div>
        <div className="rounded-2xl bg-card-2 px-2 py-2.5">
          <dt className="text-[11px] leading-tight text-muted">Winners advanced</dt>
          <dd className="mt-1 text-[20px] font-semibold tabular-nums">{percent(verdict.expected_recall)}</dd>
        </div>
        <div className="rounded-2xl bg-card-2 px-2 py-2.5">
          <dt className="text-[11px] leading-tight text-muted">Winners lost to auto-pass</dt>
          <dd className="mt-1 text-[20px] font-semibold tabular-nums">{percent(verdict.missed_winners_if_pass)}</dd>
        </div>
      </dl>
      <p className="mt-2.5 text-[13px] leading-snug text-muted">
        On held-out validation founders at this setting: of those advanced, {percent(verdict.expected_precision)} reached {target}
        {horizon}, and {percent(verdict.expected_recall)} of all who did were advanced.
        {resolved.sparse && (
          <>
            {" "}
            <Chip tone="warn">Rough</Chip> only {resolved.n_positive} validation founders reached this target, so these rates are noisy.
          </>
        )}
      </p>
    </div>
  );
}
