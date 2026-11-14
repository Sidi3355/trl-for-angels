"use client";

// Settings: appearance, screening (your bar, notifications), this session, the service, links, and
// "delete all my data". Everything here is about this device: nothing is stored on a server.
import Link from "next/link";
import { useEffect, useState } from "react";

import { useApp } from "@/components/AppState";
import { BarSummary } from "@/components/BarSheet";
import { IconChevronRight, IconLock } from "@/components/icons";
import { showIntro } from "@/components/Onboarding";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button, Page, PageHeader, SectionTitle, Spinner, cx } from "@/components/ui";
import { API_URL, getPasscode, setPasscode } from "@/lib/api";
import { deleteAllMyData } from "@/lib/profile";
import { pushSupport } from "@/lib/push";
import { clearDeals } from "@/lib/session";

const row = "flex items-center justify-between gap-4 border-b border-line py-4";

/** Whether this browser can show "screening finished" notifications, and what to do if not. */
function NotificationsRow() {
  const [state, setState] = useState<{ label: string; note: string } | null>(null);
  useEffect(() => {
    const support = pushSupport();
    if (support === "install") return setState({ label: "Add to Home Screen first", note: "On iPhone, notifications work once Halomark is on your Home Screen: Share, then Add to Home Screen." });
    if (support === "no") return setState({ label: "Not available", note: "This browser can't show notifications." });
    const p = Notification.permission;
    setState(
      p === "granted"
        ? { label: "Allowed", note: "Tap \u201cNotify me when it's ready\u201d on any screening or list that's running." }
        : p === "denied"
          ? { label: "Blocked", note: "Turn notifications on for Halomark in your phone's or browser's settings." }
          : { label: "Not asked yet", note: "You'll be asked the first time you tap \u201cNotify me when it's ready\u201d." },
    );
  }, []);
  return (
    <div className={row}>
      <span className="min-w-0">
        <span className="block text-[15.5px] font-semibold">Notifications</span>
        <span className="block text-[13.5px] text-muted">{state?.note ?? "Checking…"}</span>
      </span>
      <span className="shrink-0 text-[13.5px] font-semibold">{state?.label}</span>
    </div>
  );
}

function LinkRow({ href, title, note }: { href: string; title: string; note?: string }) {
  return (
    <Link href={href} className="flex items-center justify-between gap-4 border-b border-line py-3.5 transition-opacity active:opacity-60">
      <span className="min-w-0">
        <span className="block text-[15.5px] font-semibold">{title}</span>
        {note && <span className="block text-[13.5px] text-muted">{note}</span>}
      </span>
      <IconChevronRight size={18} className="shrink-0 text-muted" />
    </Link>
  );
}

function DeleteAll() {
  const [step, setStep] = useState<"idle" | "confirm" | "busy">("idle");
  return (
    <section className="mt-12" aria-labelledby="delete">
      <SectionTitle id="delete">Delete all my data</SectionTitle>
      <p className="max-w-[62ch] text-[14.5px] leading-relaxed text-ink-2">
        Removes everything Halomark keeps on this device: your profile, your bar, this session&apos;s founders, a saved passcode and notification sign-ups. Our servers keep nothing after the session anyway: a
        screening is held in memory for up to about two hours, then deleted.
      </p>
      {step === "idle" ? (
        <button type="button" onClick={() => setStep("confirm")} className="mt-4 h-11 rounded-full border border-danger px-5 text-[15px] font-semibold text-danger transition-colors hover:bg-danger-soft">
          Delete all my data
        </button>
      ) : (
        <div className="mt-4 rounded-[16px] bg-danger-soft p-4" role="alertdialog" aria-label="Confirm deleting your data">
          <p className="text-[15px] font-bold text-danger">Delete everything on this device? This can&apos;t be undone.</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={step === "busy"}
              onClick={async () => {
                setStep("busy");
                await deleteAllMyData();
                window.location.assign("/account?deleted=1");
              }}
              className="inline-flex h-11 items-center gap-2 rounded-full bg-danger px-5 text-[15px] font-semibold text-white disabled:opacity-60"
            >
              {step === "busy" && <Spinner />} Delete everything
            </button>
            <Button variant="secondary" onClick={() => setStep("idle")} disabled={step === "busy"}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}

export default function SettingsPage() {
  const { bar, openBarSheet, health, healthError, deals } = useApp();
  const [hasCode, setHasCode] = useState(false);
  const [cleared, setCleared] = useState(false);
  useEffect(() => setHasCode(Boolean(getPasscode())), []);
  return (
    <Page>
      <PageHeader title="Settings" subtitle="How Halomark looks and works on this device. Nothing here leaves it." />
      <section>
        <SectionTitle>Appearance</SectionTitle>
        <ThemeToggle />
      </section>

      <section className="mt-12">
        <SectionTitle>Screening</SectionTitle>
        <div className="-mt-3.5">
          <div className={row}>
            <span className="min-w-0">
              <span className="block text-[15.5px] font-semibold">Your bar</span>
              <span className="block text-[13.5px] text-muted">
                <BarSummary bar={bar} />
              </span>
            </span>
            <Button variant="secondary" onClick={openBarSheet}>
              Change
            </Button>
          </div>
          <NotificationsRow />
        </div>
      </section>

      <section className="mt-12">
        <SectionTitle>This session</SectionTitle>
        <div className="-mt-3.5">
          <div className={row}>
            <span className="min-w-0">
              <span className="block text-[15.5px] font-semibold">This session&apos;s founders</span>
              <span className="block text-[13.5px] text-muted">{cleared ? "Cleared." : `${deals.length} founder${deals.length === 1 ? "" : "s"}. Gone when you close the app.`}</span>
            </span>
            <Button variant="secondary" disabled={!deals.length} onClick={() => { clearDeals(); setCleared(true); }}>
              Clear
            </Button>
          </div>
          {hasCode && (
            <div className={row}>
              <span className="flex items-center gap-2 text-[15.5px] font-semibold">
                <IconLock size={17} className="text-muted" /> Passcode saved for this session
              </span>
              <Button variant="secondary" onClick={() => { setPasscode(null); setHasCode(false); }}>
                Forget
              </Button>
            </div>
          )}
          <div className={row}>
            <span className="min-w-0">
              <span className="block text-[15.5px] font-semibold">The intro</span>
              <span className="block text-[13.5px] text-muted">The three first-run screens.</span>
            </span>
            <Button variant="secondary" onClick={showIntro}>
              Show again
            </Button>
          </div>
          <div className={row}>
            <span className="min-w-0">
              <span className="block text-[15.5px] font-semibold">Service</span>
              <span className="block truncate text-[13.5px] text-muted">{API_URL.replace(/^https?:\/\//, "")}</span>
            </span>
            <span className={cx("flex shrink-0 items-center gap-1.5 text-[13.5px] font-semibold", healthError ? "text-danger" : health ? "text-ink" : "text-muted")}>
              {health && !healthError && <span className={cx("h-2 w-2 rounded-full", health.mock ? "bg-escalate-fill" : "bg-advance-fill")} aria-hidden />}
              {healthError ? "Offline" : health ? (health.mock ? "Online · example scores" : "Online") : "Checking…"}
            </span>
          </div>
        </div>
      </section>

      <section className="mt-12">
        <SectionTitle>Halomark</SectionTitle>
        <div className="-mt-3.5">
          <LinkRow href="/account" title="Your profile" note="Sectors, cheque size and your default bar, on this device" />
          <LinkRow href="/about" title="How it works" note="From a name to Meet, Look closer or Pass" />
          <LinkRow href="/calibration" title="How accurate are the odds?" note="What 30% really means" />
          <LinkRow href="/model-card" title="Model card" note="The model, its data and its limits" />
          <LinkRow href="/plans" title="Plans" note="Free for now" />
          <LinkRow href="/terms" title="Terms" note="Draft" />
          <LinkRow href="/privacy" title="Privacy" note="Draft" />
        </div>
      </section>

      <DeleteAll />
    </Page>
  );
}

