"use client";

// Live research progress over server-sent events, then on to the memo.
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { IconAlert, IconCheck, IconDoc, IconFlip, IconSearch, IconUser } from "@/components/icons";
import { Button, Notice, Page, Spinner, VerdictBadge, cx, linkClass } from "@/components/ui";
import { NotifyButton } from "@/components/NotifyButton";
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
  if (type === "source") return <IconDoc size={17} className={cx(c, "text-ink")} />;
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

  const stepNo = Math.min(STEPS.length, Math.max(1, at));

  return (
    <Page>
      <div className="pt-4 lg:pt-2">
        <div className="flex items-end justify-between gap-4">
          <div className="min-w-0">
            <p className="eyebrow text-muted">{ready ? "Done" : error ? "Stopped" : "Screening"}</p>
            {/* a pasted web address is one long word: let it wrap instead of running off the screen */}
            <h1 className="mt-2 text-[36px] font-extrabold leading-[1] tracking-[-0.04em] [overflow-wrap:anywhere] lg:text-[50px]">
              {ready ? "Memo ready" : who ? `Researching ${who}` : "Starting…"}
            </h1>
          </div>
          <p className="cond shrink-0 text-[64px] font-black leading-[0.78] lg:text-[84px]" aria-hidden>
            {stepNo}
            <span className="text-[0.5em] text-faint">/{STEPS.length}</span>
          </p>
        </div>

        <div className="mt-6 flex gap-1.5" role="progressbar" aria-valuenow={Math.round(ready ? 100 : pct)} aria-valuemin={0} aria-valuemax={100} aria-label="Progress">
          {STEPS.map((s) => {
            const idx = ORDER.indexOf(s.stage);
            const isDone = at > idx;
            const isNow = at === idx && !error;
            return (
              <span key={s.stage} className={cx("h-2.5 flex-1 rounded-full transition-colors duration-500", error && at === idx ? "bg-danger" : isDone ? "bg-ink" : isNow ? "anim-pulse bg-ink" : "bg-line-strong")} />
            );
          })}
        </div>
        <ol className="mt-2.5 hidden gap-1.5 text-[12.5px] sm:flex">
          {STEPS.map((s) => {
            const idx = ORDER.indexOf(s.stage);
            const isDone = at > idx;
            const isNow = at === idx && !error;
            return (
              <li key={s.stage} className={cx("flex flex-1 items-center gap-1", isDone ? "font-medium text-ink-2" : isNow ? "font-bold text-ink" : "text-faint")}>
                {isDone && <IconCheck size={13} strokeWidth={2.6} />}
                {s.label}
              </li>
            );
          })}
        </ol>
        <p className="mt-4 flex min-h-[1.5em] items-start gap-2 text-[16px] font-medium text-ink-2" aria-live="polite">
          {ready ? (
            <>
              <span className="sr-only">Verdict: {DECISION_LABELS[ready.decision]}.</span>
              <VerdictBadge decision={ready.decision} /> Opening the memo…
            </>
          ) : error ? (
            "The screening couldn't finish."
          ) : (
            <>
              <Spinner size={15} className="mt-[4px] shrink-0 text-muted" />
              <span>
                <span className="font-bold text-ink sm:hidden">{current?.label ?? "Getting ready"}. </span>
                {current?.detail ?? "Getting ready"}
              </span>
            </>
          )}
        </p>
      </div>

      {!ready && !error && <NotifyButton kind="screening" id={jobId} className="mt-5" />}

      {error && (
        <div className="mt-6 space-y-3">
          <Notice tone="danger">{error}</Notice>
          <Button variant="secondary" onClick={() => router.push("/new")}>
            Try again
          </Button>
        </div>
      )}

      <section className="mt-10" aria-labelledby="found">
        <div className="flex items-end justify-between gap-4 border-t-2 border-ink pt-3">
          <h2 id="found" className="text-[21px] font-bold tracking-[-0.025em]">
            What the agent found
          </h2>
          <p className="flex items-baseline gap-4 text-[13px] font-medium text-muted">
            <span>
              <span className="cond mr-1 text-[26px] font-extrabold leading-none text-ink">{counts.sources}</span>source{counts.sources === 1 ? "" : "s"}
            </span>
            <span>
              <span className="cond mr-1 text-[26px] font-extrabold leading-none text-ink">{counts.facts}</span>fact{counts.facts === 1 ? "" : "s"}
            </span>
          </p>
        </div>
        <div className="mt-2">
          {events.length === 0 ? (
            <div className="space-y-4 py-3">
              {[70, 55, 80].map((w) => (
                <div key={w} className="flex items-center gap-3">
                  <span className="skeleton h-4 w-4 rounded" />
                  <span className="skeleton h-3.5 rounded" style={{ width: `${w}%` }} />
                </div>
              ))}
            </div>
          ) : (
            <>
              {!showAll && events.length > 6 && (
                <button type="button" onClick={() => setShowAll(true)} className={cx(linkClass, "my-2 text-[13.5px]")}>
                  Show {events.length - 6} earlier
                </button>
              )}
              <ul>
                {feed.map((ev) => (
                  <li key={ev.seq} className={cx("anim-fade-up flex gap-3 border-b border-line py-3 text-[15px] leading-snug", ev.type === "search" ? "text-muted" : "text-ink")}>
                    <FeedIcon type={ev.type} />
                    <span className="min-w-0 break-words">{ev.message}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </section>
      <p className="mt-4 text-[12.5px] leading-snug text-faint">Only facts from before the founding date reach the model. Anything later goes to the memo&apos;s notes.</p>
    </Page>
  );
}
