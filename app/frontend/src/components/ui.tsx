// Small building blocks shared by every screen.
import Link from "next/link";
import type { ReactNode } from "react";

import { DECISION_LABELS } from "@/lib/format";
import type { Decision } from "@/lib/types";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

export function Page({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto min-h-dvh w-full max-w-xl px-4 pb-[max(env(safe-area-inset-bottom),24px)] pt-[max(env(safe-area-inset-top),12px)]">
      {children}
    </div>
  );
}

export function TopBar({ back, title, right }: { back?: { href: string; label: string }; title?: string; right?: ReactNode }) {
  return (
    <div className="flex h-11 items-center justify-between gap-2">
      {back ? (
        <Link href={back.href} className="-ml-1 flex items-center gap-0.5 rounded-lg px-1 py-1 text-[17px] text-accent active:opacity-60">
          <ChevronLeft /> {back.label}
        </Link>
      ) : (
        <span />
      )}
      {title && <span className="truncate text-[17px] font-semibold">{title}</span>}
      {right ?? <span className="w-10" />}
    </div>
  );
}

export function Section({
  title,
  aside,
  footer,
  children,
  id,
}: {
  title?: string;
  aside?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  id?: string;
}) {
  return (
    <section id={id} className="mt-7 scroll-mt-4">
      {(title || aside) && (
        <div className="mb-1.5 flex items-end justify-between px-4">
          {title && <h2 className="text-[13px] font-medium uppercase tracking-wide text-muted">{title}</h2>}
          {aside}
        </div>
      )}
      <div className="overflow-hidden rounded-2xl bg-card">{children}</div>
      {footer && <div className="px-4 pt-1.5 text-[13px] leading-snug text-muted">{footer}</div>}
    </section>
  );
}

/** A row inside a Section card, with an inset divider above every row but the first. */
export function Row({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cx("relative px-4 py-3 [&+&]:before:absolute [&+&]:before:left-4 [&+&]:before:right-0 [&+&]:before:top-0 [&+&]:before:h-px [&+&]:before:bg-line", className)}>
      {children}
    </div>
  );
}

export function Segmented<T extends string | number | null>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="flex rounded-[9px] bg-card-2 p-0.5">
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={String(o.value)}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(o.value)}
            className={cx(
              "min-h-8 flex-1 rounded-[7px] px-2 text-[13px] font-medium",
              on ? "bg-card text-ink shadow-[0_1px_3px_rgba(0,0,0,0.12)] dark:bg-[#5a5a5f]" : "text-ink-2 active:opacity-60",
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

export function Switch({ id, checked, onChange }: { id?: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cx("relative h-[31px] w-[51px] shrink-0 rounded-full transition-colors", checked ? "bg-advance" : "bg-card-2 ring-1 ring-inset ring-line")}
    >
      <span className={cx("absolute top-[2px] h-[27px] w-[27px] rounded-full bg-white shadow-[0_2px_4px_rgba(0,0,0,0.2)] transition-[left]", checked ? "left-[22px]" : "left-[2px]")} />
    </button>
  );
}

const DECISION_STYLE: Record<Decision, string> = {
  advance: "bg-advance-soft text-advance",
  escalate: "bg-escalate-soft text-escalate",
  pass: "bg-pass-soft text-pass",
};

export function DecisionPill({ decision, size = "md" }: { decision: Decision; size?: "sm" | "md" | "lg" }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-full font-semibold",
        DECISION_STYLE[decision],
        size === "lg" ? "px-3.5 py-1.5 text-[17px]" : size === "md" ? "px-2.5 py-1 text-[13px]" : "px-2 py-0.5 text-[12px]",
      )}
    >
      <span className={cx("rounded-full bg-current", size === "lg" ? "h-2 w-2" : "h-1.5 w-1.5")} />
      {DECISION_LABELS[decision]}
    </span>
  );
}

export function Chip({ children, tone = "neutral", title }: { children: ReactNode; tone?: "neutral" | "accent" | "warn" | "danger" | "good"; title?: string }) {
  const tones = {
    neutral: "bg-card-2 text-ink-2",
    accent: "bg-accent-soft text-accent",
    warn: "bg-warn-soft text-warn",
    danger: "bg-danger-soft text-danger",
    good: "bg-advance-soft text-advance",
  };
  return (
    <span title={title} className={cx("inline-flex items-center whitespace-nowrap rounded-md px-1.5 py-0.5 text-[12px] font-medium", tones[tone])}>
      {children}
    </span>
  );
}

export function Notice({ tone, children }: { tone: "warn" | "danger" | "info"; children: ReactNode }) {
  const tones = { warn: "bg-warn-soft text-warn", danger: "bg-danger-soft text-danger", info: "bg-accent-soft text-accent" };
  return <div className={cx("rounded-xl px-3.5 py-2.5 text-[14px] leading-snug", tones[tone])}>{children}</div>;
}

export function Spinner({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={cx("h-4 w-4 animate-spin", className)} aria-hidden>
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Disclaimer({ text }: { text?: string }) {
  return (
    <p className="mt-8 px-4 text-center text-[12px] leading-relaxed text-muted">
      {text ??
        "Screening aid, not investment advice. The model estimates the chance of a large outcome from the founder's background on the day the company was founded. It was trained on generated data, so its accuracy on real founders is unknown. Public information only; nothing is stored after the session."}
    </p>
  );
}

// ---- icons (inline, so nothing loads from elsewhere) --------------------------------------

const icon = "h-[18px] w-[18px] shrink-0";
export const ChevronLeft = () => (
  <svg viewBox="0 0 24 24" className="h-[22px] w-[22px]" aria-hidden>
    <path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
export const ChevronDown = ({ open }: { open?: boolean }) => (
  <svg viewBox="0 0 24 24" className={cx("h-4 w-4 transition-transform", open && "rotate-180")} aria-hidden>
    <path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
export const SearchIcon = () => (
  <svg viewBox="0 0 24 24" className={icon} aria-hidden>
    <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" strokeWidth="2" />
    <path d="M16 16l4.5 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);
export const DocIcon = () => (
  <svg viewBox="0 0 24 24" className={icon} aria-hidden>
    <path d="M7 3h7l4 4v14H7z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    <path d="M14 3v4h4M10 12h5M10 16h5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);
export const CheckIcon = () => (
  <svg viewBox="0 0 24 24" className={icon} aria-hidden>
    <path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
export const WarnIcon = () => (
  <svg viewBox="0 0 24 24" className={icon} aria-hidden>
    <path d="M12 4l9 16H3z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    <path d="M12 10v4.5M12 17.5v.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);
export const FieldIcon = () => (
  <svg viewBox="0 0 24 24" className={icon} aria-hidden>
    <circle cx="12" cy="8.5" r="3.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
    <path d="M5 20c1.2-3.6 3.8-5.5 7-5.5s5.8 1.9 7 5.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);
export const ConflictIcon = () => (
  <svg viewBox="0 0 24 24" className={icon} aria-hidden>
    <path d="M7 7h11l-3-3M17 17H6l3 3" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
export const Mark = () => (
  <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden>
    <rect width="32" height="32" rx="8" fill="var(--accent)" />
    <path d="M9 21.5l4.5-5 3.5 3 6-8" fill="none" stroke="var(--accent-ink)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="23" cy="11.5" r="2" fill="var(--accent-ink)" />
  </svg>
);
