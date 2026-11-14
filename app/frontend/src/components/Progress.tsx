"use client";

// Live research progress over server-sent events, then on to the memo.
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { IconAlert, IconCheck, IconDoc, IconFlip, IconSearch, IconUser } from "@/components/icons";
import { Button, Card, Notice, Page, Spinner, cx } from "@/components/ui";
import { api, eventsUrl, type ApiError } from "@/lib/api";
import { DECISION_LABELS } from "@/lib/format";
import { EVENT_TYPES, type Decision, type ProgressEvent, type Stage } from "@/lib/types";

const STEPS: { stage: Stage; label: string; detail: string }[] = [
  { stage: "researching", label: "Researching", detail: "Reading public sources from before the founding date" },
  { stage: "merging", label: "Combining", detail: "Merging the findings with what you entered" },
  { stage: "rendering", label: "Anonymising", detail: "Removing names and writing the standard profile" },
  { stage: "answering", label: "Answering", detail: "Answering the screening questions" },
  { stage: "deciding", label: "Scoring", detail: "Estimating outcome size and timing" },
  { stage: "writing_memo", label: "Writing", detail: "Putting the memo together" },
];
const ORDER: Stage[] = ["queued", ...STEPS.map((s) => s.stage), "done"];
const FEED = new Set(["search", "source", "field", "conflict", "warning", "error"]);

function FeedIcon({ type }: { type: string }) {
  const c = "mt-[1px] shrink-0";
  if (type === "search") return <IconSearch size={17} className={cx(c, "text-faint")} />;
  if (type === "source") return <IconDoc size={17} className={cx(c, "text-accent")} />;
  if (type === "field") return <IconUser size={17} className={cx(c, "text-advance")} />;
  if (type === "conflict") return <IconFlip size={17} className={cx(c, "text-escalate")} />;
  return <IconAlert size={17} className={cx(c, "text-warn")} />;
}

export function Progress({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [stage, setStage] = useState<Stage>("queued");
  const [who, setWho] = useState<string | null>(null);
  const [ready, setReady] = useState<{ memo_id: string; decision: Decision } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const seen = useRef(new Set<number>());

  useEffect(() => {
    const es = new EventSource(eventsUrl(jobId));
    let finished = false;
    const done = () => {
      finished = true;
      es.close();
    };
    const handle = (ev: ProgressEvent) => {
      if (seen.current.has(ev.seq) || ev.type === "heartbeat") return;
      seen.current.add(ev.seq);
      if (ev.type === "stage" && ev.stage) {
        setStage(ev.stage);
        const m = ev.message.match(/^Researching (.+?) \(/);
        if (m) setWho(m[1]);
      }
      if (ev.type === "memo_ready" && ev.data?.memo_id) {
        done();
        setReady({ memo_id: ev.data.memo_id, decision: ev.data.decision });
        window.setTimeout(() => router.replace(`/memos/${ev.data!.memo_id}`), 900);
      }
      if (ev.type === "error") {
        done();
        setError(ev.data?.message ?? ev.message);
      }
      if (FEED.has(ev.type)) setEvents((l) => [...l, ev]);
    };
    for (const t of EVENT_TYPES) {
      es.addEventListener(t, (m) => {
        try {
          handle(JSON.parse((m as MessageEvent).data));
        } catch {
          // a malformed event is skipped; the stream carries on
        }
      });
    }
    // The stream drops when the job ends or the network blips; EventSource reconnects by itself.
    // Check the job too, so a finished, failed or expired screening never leaves this screen hanging.
    es.onerror = () => {
      if (finished) return;
      api.job(jobId).then(
        (job) => {
          if (job.status === "complete" && job.memo_id) {
            done();
            router.replace(`/memos/${job.memo_id}`);
          } else if (job.status === "failed") {
            done();
            setError(job.error?.message ?? "The screening failed.");
          }
        },
        (e: ApiError) => {
          if (e.status === 404 || e.status === 401) {
            done();
            if (e.status === 404) setError("This screening has expired. Screenings are kept for a limited time.");
          }
        },
      );
    };
    return () => es.close();
  }, [jobId, router]);

  const at = ready ? ORDER.length : ORDER.indexOf(stage);
  const pct = Math.min(100, Math.max(6, ((at - 1) / STEPS.length) * 100 + (ready ? 0 : 100 / STEPS.length / 2)));
  const current = STEPS.find((s) => s.stage === stage);
  const counts = {
    sources: events.filter((e) => e.type === "source").length,
    facts: events.filter((e) => e.type === "field").length,
  };
  const feed = showAll ? events : events.slice(-6);

  return (
    <Page>
      <div className="pt-6 lg:pt-4">
        <p className="text-[13px] font-semibold uppercase tracking-[0.06em] text-muted">{ready ? "Done" : error ? "Stopped" : "Screening"}</p>
        <h1 className="mt-1 font-display text-[30px] font-semibold leading-[1.1] tracking-[-0.02em] lg:text-[36px]">
          {ready ? "Memo ready" : who ? `Researching ${who}` : "Starting…"}
        </h1>
        <p className="mt-2 text-[15px] text-muted" aria-live="polite">
          {ready ? `Verdict: ${DECISION_LABELS[ready.decision]}. Opening the memo…` : error ? "The screening couldn't finish." : current?.detail ?? "Getting ready"}
        </p>

        <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-surface-3" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} aria-label="Progress">
          <div className={cx("h-full rounded-full transition-[width] duration-700 ease-out", error ? "bg-danger" : ready ? "bg-advance-fill" : "bg-accent")} style={{ width: `${ready ? 100 : pct}%` }} />
        </div>
        <ol className="mt-3 grid grid-cols-3 gap-x-3 gap-y-1.5 text-[12.5px] sm:grid-cols-6">
          {STEPS.map((s) => {
            const idx = ORDER.indexOf(s.stage);
            const isDone = at > idx;
            const isNow = at === idx && !error;
            return (
              <li key={s.stage} className={cx("flex shrink-0 items-center gap-1 font-medium", isDone ? "text-ink-2" : isNow ? "text-accent" : "text-faint")}>
                {isDone ? <IconCheck size={14} strokeWidth={2.4} className="text-advance" /> : isNow ? <Spinner size={12} /> : null}
                {s.label}
              </li>
            );
          })}
        </ol>
      </div>

      {error && (
        <div className="mt-6 space-y-3">
          <Notice tone="danger">{error}</Notice>
          <Button variant="secondary" onClick={() => router.push("/new")}>
            Try again
          </Button>
        </div>
      )}

      <Card className="mt-8 overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 className="text-[15px] font-semibold">What the agent found</h2>
          <span className="text-[13px] tabular text-muted">
            {counts.sources} source{counts.sources === 1 ? "" : "s"} · {counts.facts} fact{counts.facts === 1 ? "" : "s"}
          </span>
        </div>
        <div className="px-4 py-2">
          {events.length === 0 ? (
            <div className="space-y-3 py-2">
              {[70, 55, 80].map((w) => (
                <div key={w} className="flex items-center gap-2.5">
                  <span className="skeleton h-4 w-4 rounded" />
                  <span className="skeleton h-3.5 rounded" style={{ width: `${w}%` }} />
                </div>
              ))}
            </div>
          ) : (
            <>
              {!showAll && events.length > 6 && (
                <button type="button" onClick={() => setShowAll(true)} className="w-full py-2 text-left text-[13px] font-medium text-accent">
                  Show {events.length - 6} earlier
                </button>
              )}
              <ul>
                {feed.map((ev) => (
                  <li key={ev.seq} className={cx("anim-fade-up flex gap-2.5 py-2 text-[14.5px] leading-snug", ev.type === "search" ? "text-muted" : "text-ink-2")}>
                    <FeedIcon type={ev.type} />
                    <span className="min-w-0 break-words">{ev.message}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </Card>
      <p className="mt-3 px-1 text-[12.5px] leading-snug text-faint">Only facts from before the founding date reach the model. Anything later goes to the memo&apos;s notes.</p>
    </Page>
  );
}
