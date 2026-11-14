"use client";

// How it works, what the numbers mean, privacy, and the app's settings.
import { useEffect, useState } from "react";

import { useApp } from "@/components/AppState";
import { BarSummary } from "@/components/BarSheet";
import { IconEye, IconLock, IconSearch, IconSliders, IconSparkle } from "@/components/icons";
import { Button, Card, Disclaimer, Page, PageHeader, SectionTitle, VerdictBadge, cx } from "@/components/ui";
import { API_URL, getPasscode, setPasscode } from "@/lib/api";
import { clearDeals } from "@/lib/session";

const STEPS = [
  { icon: IconSearch, title: "Research", body: "An AI agent searches the web for the founder's background, and keeps only what was true on the day the company was founded. Every fact links to its source." },
  { icon: IconEye, title: "Anonymise", body: "Names of people, companies and universities are removed, and the background is written into the same standard profile the model was trained on." },
  { icon: IconSparkle, title: "Score", body: "Screening questions are answered from the profile, and a calibrated decision model estimates how big the outcome could be, and how long it could take." },
  { icon: IconSliders, title: "Decide", body: "Your bar turns that chance into advance, escalate or pass. Change it any time: every verdict updates instantly." },
];

export default function AboutPage() {
  const { bar, openBarSheet, health, healthError, deals } = useApp();
  const [hasCode, setHasCode] = useState(false);
  useEffect(() => setHasCode(Boolean(getPasscode())), []);
  const [cleared, setCleared] = useState(false);

  return (
    <Page>
      <PageHeader title="How it works" subtitle="Angels screen alone. Screener does the first pass for you: research, a calibrated score, and the reasons behind it." />

      <ol className="space-y-3">
        {STEPS.map(({ icon: Icon, title, body }, i) => (
          <li key={title}>
            <Card className="flex gap-4 p-4">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
                <Icon size={20} />
              </span>
              <div>
                <p className="text-[15px] font-semibold">
                  <span className="mr-1.5 text-faint tabular">{i + 1}</span>
                  {title}
                </p>
                <p className="mt-1 text-[14px] leading-relaxed text-muted">{body}</p>
              </div>
            </Card>
          </li>
        ))}
      </ol>

      <section className="mt-10">
        <SectionTitle>Reading a verdict</SectionTitle>
        <Card className="divide-y divide-line">
          {(
            [
              ["advance", "The chance clears your bar. Worth a meeting."],
              ["escalate", "Close to your bar. Your judgement decides."],
              ["pass", "Below your bar. Few founders like this reached your target in testing."],
            ] as const
          ).map(([d, text]) => (
            <div key={d} className="flex items-center gap-3 px-4 py-3.5">
              <span className="w-[92px] shrink-0">
                <VerdictBadge decision={d} />
              </span>
              <p className="text-[14px] leading-snug text-ink-2">{text}</p>
            </div>
          ))}
        </Card>
        <p className="mt-2 px-1 text-[12.5px] leading-snug text-faint">
          The chance is the share of founders with a background like this who reached your target in the model&apos;s data. It is calibrated, so 30% means about 3 in 10.
        </p>
      </section>

      <section className="mt-10">
        <SectionTitle>Settings</SectionTitle>
        <Card className="divide-y divide-line">
          <button type="button" onClick={openBarSheet} className="flex w-full items-center justify-between gap-3 px-4 py-3.5 text-left hover:bg-surface-2">
            <span>
              <span className="block text-[15px] font-medium">Your bar</span>
              <span className="block text-[13px] text-muted">
                <BarSummary bar={bar} />
              </span>
            </span>
            <span className="text-[14px] font-medium text-accent">Change</span>
          </button>
          <div className="flex items-center justify-between gap-3 px-4 py-3.5">
            <span>
              <span className="block text-[15px] font-medium">This session&apos;s founders</span>
              <span className="block text-[13px] text-muted">{cleared ? "Cleared." : `${deals.length} founder${deals.length === 1 ? "" : "s"}. Gone when you close the app.`}</span>
            </span>
            <Button variant="secondary" disabled={!deals.length} onClick={() => { clearDeals(); setCleared(true); }}>
              Clear
            </Button>
          </div>
          {hasCode && (
            <div className="flex items-center justify-between gap-3 px-4 py-3.5">
              <span className="flex items-center gap-2 text-[15px] font-medium">
                <IconLock size={17} className="text-muted" /> Passcode saved for this session
              </span>
              <Button variant="secondary" onClick={() => { setPasscode(null); setHasCode(false); }}>
                Forget
              </Button>
            </div>
          )}
          <div className="flex items-center justify-between gap-3 px-4 py-3.5">
            <span className="min-w-0">
              <span className="block text-[15px] font-medium">Service</span>
              <span className="block truncate text-[13px] text-muted">{API_URL.replace(/^https?:\/\//, "")}</span>
            </span>
            <span className={cx("shrink-0 text-[13px] font-medium", healthError ? "text-danger" : health ? "text-advance" : "text-muted")}>
              {healthError ? "Offline" : health ? (health.mock ? "Online · prototype" : "Online") : "Checking…"}
            </span>
          </div>
        </Card>
      </section>

      <section className="mt-10">
        <SectionTitle>Privacy</SectionTitle>
        <Card className="p-4">
          <ul className="space-y-2 text-[14px] leading-relaxed text-ink-2">
            <li>Only public information is used.</li>
            <li>Your notes appear in the memo and are never sent to the model.</li>
            <li>Nothing is kept after your session: memos are deleted on the server, and the deals list lives only in this app until you close it.</li>
          </ul>
        </Card>
      </section>

      <Disclaimer className="mt-10" />
    </Page>
  );
}
