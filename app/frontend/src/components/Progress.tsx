"use client";

// Live research progress over server-sent events, then on to the memo.
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  CheckIcon,
  ConflictIcon,
  DocIcon,
  FieldIcon,
  Notice,
  Page,
  SearchIcon,
  Spinner,
  TopBar,
  WarnIcon,
  cx,
} from "@/components/ui";
import { api, eventsUrl, type ApiError } from "@/lib/api";
import { DECISION_LABELS } from "@/lib/format";
import { EVENT_TYPES, type ProgressEvent, type Stage } from "@/lib/types";

const STEPS: { stage: Stage; label: string }[] = [
  { stage: "researching", label: "Researching the founder" },
  { stage: "merging", label: "Merging with what you know" },
  { stage: "rendering", label: "Anonymising the profile" },
  { stage: "answering", label: "Answering the screening questions" },
  { stage: "deciding", label: "Scoring outcome and timeline" },
  { stage: "writing_memo", label: "Writing the memo" },
];
const ORDER: Stage[] = ["queued", ...STEPS.map((s) => s.stage), "done"];

const FEED_TYPES = new Set(["search", "source", "field", "conflict", "warning", "error"]);

function FeedIcon({ type }: { type: string }) {
  if (type === "search") return <SearchIcon />;
  if (type === "source") return <DocIcon />;
  if (type === "field") return <FieldIcon />;
  if (type === "conflict") return <ConflictIcon />;
  return <WarnIcon />;
}

export function Progress({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [stage, setStage] = useState<Stage>("queued");
  const [headline, setHeadline] = useState("Starting the screening…");
  const [ready, setReady] = useState<{ memo_id: string; decision: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const seen = useRef(new Set<number>());
  const feedEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const es = new EventSource(eventsUrl(jobId));
    let finished = false;

    const handle = (ev: ProgressEvent) => {
      if (seen.current.has(ev.seq)) return;
      seen.current.add(ev.seq);
      if (ev.type === "heartbeat") return;
      if (ev.type === "stage" && ev.stage) {
        setStage(ev.stage);
        if (ev.stage !== "done") setHeadline(ev.message);
      }
      if (ev.type === "memo_ready" && ev.data?.memo_id) {
        finished = true;
        setReady({ memo_id: ev.data.memo_id, decision: ev.data.decision });
        es.close();
        window.setTimeout(() => router.replace(`/memos/${ev.data!.memo_id}`), 700);
      }
      if (ev.type === "error") {
        finished = true;
        setError(ev.data?.message ?? ev.message);
        es.close();
      }
      if (FEED_TYPES.has(ev.type)) setEvents((list) => [...list, ev]);
    };

    for (const t of EVENT_TYPES) {
      es.addEventListener(t, (m) => {
        try {
          handle(JSON.parse((m as MessageEvent).data));
        } catch {
          // ignore a malformed event; the stream carries on
        }
      });
    }

    // The stream drops when the job ends or the network blips; EventSource reconnects on its own.
    // Check the job itself, so a finished, failed or expired screening never leaves this screen hanging.
    es.onerror = () => {
      if (finished) return;
      api.job(jobId).then(
        (job) => {
          if (job.status === "complete" && job.memo_id) {
            finished = true;
            es.close();
            router.replace(`/memos/${job.memo_id}`);
          } else if (job.status === "failed") {
            finished = true;
            es.close();
            setError(job.error?.message ?? "The screening failed.");
          }
        },
        (e: ApiError) => {
          if (e.status === 404 || e.status === 401) {
            finished = true;
            es.close();
            if (e.status === 404) setError("This screening has expired or doesn't exist.");
          }
        },
      );
    };
    return () => es.close();
  }, [jobId, router]);

  useEffect(() => {
    feedEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events.length]);

  const at = ORDER.indexOf(stage);
  const counts = {
    searches: events.filter((e) => e.type === "search").length,
    sources: events.filter((e) => e.type === "source").length,
    fields: events.filter((e) => e.type === "field").length,
  };

  return (
    <Page>
      <TopBar back={{ href: "/", label: "New" }} />
      <h1 className="mt-2 text-[28px] font-bold leading-tight tracking-tight">{ready ? "Memo ready" : error ? "Screening stopped" : "Screening…"}</h1>
      <p className="mt-1 text-[15px] text-muted" aria-live="polite">
        {ready ? `Verdict: ${DECISION_LABELS[ready.decision as keyof typeof DECISION_LABELS] ?? ready.decision}. Opening the memo…` : headline}
      </p>

      {error && <div className="mt-4"><Notice tone="danger">{error}</Notice></div>}

      <ol className="mt-5 overflow-hidden rounded-2xl bg-card">
        {STEPS.map((s, i) => {
          const idx = ORDER.indexOf(s.stage);
          const done = at > idx || Boolean(ready);
          const current = at === idx && !ready && !error;
          return (
            <li key={s.stage} className={cx("relative flex items-center gap-3 px-4 py-3", i > 0 && "before:absolute before:left-12 before:right-0 before:top-0 before:h-px before:bg-line")}>
              <span className={cx("flex h-6 w-6 items-center justify-center rounded-full text-[12px]", done ? "bg-advance text-card" : current ? "bg-accent-soft text-accent" : "bg-card-2 text-muted")}>
                {done ? <CheckIcon /> : current ? <Spinner className="h-3.5 w-3.5" /> : i + 1}
              </span>
              <span className={cx("text-[15px]", !done && !current && "text-muted")}>{s.label}</span>
            </li>
          );
        })}
      </ol>

      <div className="mt-7 flex items-end justify-between px-4">
        <h2 className="text-[13px] font-medium uppercase tracking-wide text-muted">Live research</h2>
        <span className="text-[13px] tabular-nums text-muted">
          {counts.searches} searches · {counts.sources} sources · {counts.fields} fields
        </span>
      </div>
      <div className="mt-1.5 rounded-2xl bg-card px-4 py-2">
        {events.length === 0 && (
          <p className="flex items-center gap-2 py-2 text-[15px] text-muted">
            <span className="pulse-dot h-2 w-2 rounded-full bg-accent" /> Waiting for the first results…
          </p>
        )}
        <ul>
          {events.map((ev) => (
            <li key={ev.seq} className={cx("rise-in flex gap-2.5 py-2 text-[15px] leading-snug", ev.type === "warning" || ev.type === "error" ? "text-warn" : ev.type === "conflict" ? "text-escalate" : "text-ink-2")}>
              <span className={cx("mt-0.5", ev.type === "field" ? "text-advance" : ev.type === "source" ? "text-accent" : "text-muted")}>
                <FeedIcon type={ev.type} />
              </span>
              <span className="min-w-0 break-words">{ev.message}</span>
            </li>
          ))}
        </ul>
        <div ref={feedEnd} />
      </div>
      <p className="mt-3 px-4 text-[13px] text-muted">Only information from before the founding date reaches the model. Later facts go to the memo&apos;s notes.</p>
    </Page>
  );
}
