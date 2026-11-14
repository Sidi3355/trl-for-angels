"use client";

// First-run intro: three short screens (what Halomark does, what the percentages mean, try a sample
// founder). Skippable at every step, shown once per device (flag in localStorage), and replayable from
// the account page. Not shown over shared links or the legal pages.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Examples } from "@/components/Examples";
import { Button, Notice, VerdictTile, Wordmark, cx, linkClass } from "@/components/ui";
import { DECISION_LABELS } from "@/lib/format";
import { introSeen, markIntroSeen } from "@/lib/profile";
import { useStartScreening } from "@/lib/useScreening";

const SHOW_EVENT = "halomark:show-intro";
const NOT_OVER = ["/share", "/terms", "/privacy"];

/** Open the intro again (account page). */
export function showIntro() {
  window.dispatchEvent(new Event(SHOW_EVENT));
}

function Odds() {
  return (
    <div className="flex items-end gap-6" aria-hidden>
      <p className="cond text-[112px] font-black leading-[0.8] tracking-[-0.02em]">
        30<span className="text-[56px]">%</span>
      </p>
      <div className="grid grid-cols-5 gap-1.5 pb-2">
        {Array.from({ length: 10 }, (_, i) => (
          <span key={i} className={cx("h-5 w-5 rounded-full", i < 3 ? "bg-ink" : "bg-surface-3 ring-1 ring-inset ring-line-strong")} />
        ))}
      </div>
    </div>
  );
}

const STEPS = [
  {
    title: "Screen a founder in a minute.",
    body: "Type a name or share a LinkedIn. Halomark reads what was public before they started the company, scores it against your bar, and gives you a verdict with the reasons behind it.",
  },
  {
    title: "A percentage is odds, not a promise.",
    body: "The chances are calibrated: when Halomark says 30%, about 30 in 100 founders with a background like this reached your target in testing. It says nothing certain about one person, so treat it as a first pass, not a decision.",
  },
  {
    title: "Try a sample founder.",
    body: "Three made-up founders, one tap each. You'll see the research, the verdict and what moves it.",
  },
];

export function Onboarding() {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const { start, busy, error } = useStartScreening();
  const dialog = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!introSeen() && !NOT_OVER.some((p) => pathname.startsWith(p))) setOpen(true);
    const onShow = () => {
      setStep(0);
      setOpen(true);
    };
    window.addEventListener(SHOW_EVENT, onShow);
    return () => window.removeEventListener(SHOW_EVENT, onShow);
    // only on first load: later navigation doesn't reopen it
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!open) return;
    dialog.current?.focus(); // the dialog itself: screen readers start at its title, no ring on a button nobody touched
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    document.addEventListener("keydown", onKey);
    document.documentElement.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.documentElement.style.overflow = "";
    };
  }, [open, step]);

  function close() {
    markIntroSeen();
    setOpen(false);
  }

  if (!open) return null;
  const s = STEPS[step];
  const last = step === STEPS.length - 1;

  return (
    <div
      ref={dialog}
      role="dialog"
      aria-modal="true"
      aria-labelledby="intro-title"
      tabIndex={-1}
      className="fixed inset-0 z-50 outline-none overflow-y-auto bg-bg pb-[max(env(safe-area-inset-bottom),20px)] pt-[env(safe-area-inset-top)] motion-safe:animate-[fade-in_.25s_ease-out]"
    >
      <div className="mx-auto flex min-h-full max-w-[560px] flex-col px-5 sm:px-8">
        <div className="flex h-14 items-center justify-between">
          <Wordmark size={17} />
          <button type="button" onClick={close} className="h-10 rounded-full px-3 text-[15px] font-semibold text-muted transition-colors hover:text-ink">
            Skip
          </button>
        </div>

        <div key={step} className="flex flex-1 flex-col pt-6 motion-safe:animate-[fade-up_.3s_ease-out] sm:pt-14">
          <p className="eyebrow text-muted">
            {step + 1} of {STEPS.length}
          </p>
          <div className="mt-6">
            {step === 0 && (
              <ul className="flex gap-3" aria-label="The three verdicts">
                {(["advance", "escalate", "pass"] as const).map((d) => (
                  <li key={d} className="flex flex-1 flex-col items-start gap-2">
                    <VerdictTile decision={d} size={52} />
                    <span className="text-[15px] font-bold tracking-[-0.01em]">{DECISION_LABELS[d]}</span>
                  </li>
                ))}
              </ul>
            )}
            {step === 1 && <Odds />}
          </div>
          <h1 id="intro-title" className="mt-8 text-[36px] font-extrabold leading-[1.02] tracking-[-0.04em] sm:text-[44px]">
            {s.title}
          </h1>
          <p className="mt-4 text-[17px] leading-relaxed text-ink-2">{s.body}</p>
          {step === 1 && (
            <p className="mt-3 text-[14px] text-muted">
              For now the scores are examples, while the model is trained.{" "}
              <Link href="/calibration" onClick={close} className={linkClass}>
                How we check the odds
              </Link>
            </p>
          )}
          {last && (
            <div className="mt-6 space-y-4">
              <Examples onPick={(i, key) => { markIntroSeen(); start(i, key); }} busy={busy} />
              {error && <Notice tone="danger">{error}</Notice>}
            </div>
          )}

          <div className="mt-auto pt-10">
            <div className="flex items-center justify-between gap-4">
              <div className="flex gap-1.5" aria-hidden>
                {STEPS.map((_, i) => (
                  <span key={i} className={cx("h-1.5 rounded-full transition-all", i === step ? "w-6 bg-ink" : "w-1.5 bg-line-strong")} />
                ))}
              </div>
              <div className="flex items-center gap-2">
                {step > 0 && (
                  <Button variant="ghost" onClick={() => setStep(step - 1)}>
                    Back
                  </Button>
                )}
                {last ? (
                  <Button size="lg" onClick={() => { close(); router.push("/new"); }}>
                    I&apos;ll start with my own
                  </Button>
                ) : (
                  <Button size="lg" onClick={() => setStep(step + 1)}>
                    Next
                  </Button>
                )}
              </div>
            </div>
            {last && (
              <p className="mt-4 text-right text-[14px] text-muted">
                Or{" "}
                <Link href="/account" onClick={close} className={linkClass}>
                  set up your profile
                </Link>{" "}
                first.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
