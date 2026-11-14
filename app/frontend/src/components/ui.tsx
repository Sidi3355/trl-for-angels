"use client";

// Building blocks shared by every screen.
import Link from "next/link";
import { useEffect, useRef, type ReactNode } from "react";

import { IconAlert, IconArrowUpRight, IconChevronLeft, IconMinus, IconX } from "@/components/icons";
import type { Decision } from "@/lib/types";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

// ---- layout -----------------------------------------------------------------------------------

/** A page's content column. `wide` for the memo's two-column desktop layout. */
export function Page({ children, wide = false, className }: { children: ReactNode; wide?: boolean; className?: string }) {
  return (
    <div
      className={cx(
        "mx-auto w-full pb-10 pl-[max(16px,env(safe-area-inset-left))] pr-[max(16px,env(safe-area-inset-right))] pt-[max(env(safe-area-inset-top),12px)] sm:px-6 lg:px-10 lg:pt-10",
        wide ? "max-w-6xl" : "max-w-3xl",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function PageHeader({ title, subtitle, back, action }: { title: ReactNode; subtitle?: ReactNode; back?: { href: string; label: string }; action?: ReactNode }) {
  return (
    <header className="pb-5 pt-2 lg:pt-0">
      {back && (
        <Link href={back.href} className="-ml-1.5 mb-2 inline-flex items-center gap-0.5 rounded-lg py-1 pr-2 text-[15px] font-medium text-accent active:opacity-60 lg:hover:text-accent-hover">
          <IconChevronLeft size={20} /> {back.label}
        </Link>
      )}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="font-display text-[30px] font-semibold leading-[1.1] tracking-[-0.02em] lg:text-[36px]">{title}</h1>
          {subtitle && <p className="mt-1.5 text-[15px] leading-snug text-muted">{subtitle}</p>}
        </div>
        {action && <div className="shrink-0 pt-1">{action}</div>}
      </div>
    </header>
  );
}

export function SectionTitle({ children, action, id }: { children: ReactNode; action?: ReactNode; id?: string }) {
  return (
    <div className="mb-3 flex items-end justify-between gap-3">
      <h2 id={id} className="font-display text-[19px] font-semibold tracking-[-0.01em]">
        {children}
      </h2>
      {action}
    </div>
  );
}

export function Card({ children, className, as: As = "div" }: { children: ReactNode; className?: string; as?: "div" | "section" }) {
  return <As className={cx("rounded-[20px] border border-line bg-surface shadow-card", className)}>{children}</As>;
}

// ---- controls ---------------------------------------------------------------------------------

type ButtonProps = {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost";
  size?: "md" | "lg";
  full?: boolean;
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>;

export function Button({ children, variant = "primary", size = "md", full, className, ...rest }: ButtonProps) {
  return (
    <button
      {...rest}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-[background,opacity,transform] active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50",
        size === "lg" ? "h-[52px] px-6 text-[16px]" : "h-10 px-4 text-[15px]",
        variant === "primary" && "bg-accent text-accent-ink hover:bg-accent-hover",
        variant === "secondary" && "bg-surface-2 text-ink hover:bg-surface-3",
        variant === "ghost" && "text-accent hover:bg-accent-soft",
        full && "w-full",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function Segmented<T extends string | number | null>({
  label,
  value,
  options,
  onChange,
  size = "md",
}: {
  label: string;
  value: T;
  options: { value: T; label: string; hint?: string }[];
  onChange: (v: T) => void;
  size?: "md" | "lg";
}) {
  return (
    <div role="radiogroup" aria-label={label} className="flex gap-1 rounded-[14px] bg-surface-2 p-1">
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
              "flex-1 rounded-[10px] px-2 text-center font-medium",
              size === "lg" ? "py-2.5" : "py-2",
              on ? "bg-surface text-ink shadow-[0_1px_3px_rgba(13,17,32,0.14)] dark:bg-surface-3" : "text-muted hover:text-ink",
            )}
          >
            <span className="block text-[14px] leading-tight">{o.label}</span>
            {o.hint && <span className={cx("mt-0.5 block text-[11px] leading-tight", on ? "text-muted" : "text-faint")}>{o.hint}</span>}
          </button>
        );
      })}
    </div>
  );
}

export function Switch({ id, checked, onChange, label }: { id?: string; checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cx("relative h-[31px] w-[51px] shrink-0 rounded-full transition-colors", checked ? "bg-advance-fill" : "bg-surface-3")}
    >
      <span className={cx("absolute top-[2px] h-[27px] w-[27px] rounded-full bg-white shadow-[0_2px_4px_rgba(0,0,0,0.2)] transition-[left] duration-200", checked ? "left-[22px]" : "left-[2px]")} />
    </button>
  );
}

/** Pick one of a few values by tapping a chip; tap the selected one again to clear it. */
export function ChipPicker<T extends string>({ label, value, options, onChange }: { label: string; value: T | ""; options: { value: T; label: string }[]; onChange: (v: T | "") => void }) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(on ? "" : o.value)}
            className={cx(
              "h-9 rounded-full border px-3.5 text-[14px] font-medium transition-colors",
              on ? "border-accent bg-accent text-accent-ink" : "border-line-strong bg-surface text-ink-2 hover:border-faint",
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

// ---- status -----------------------------------------------------------------------------------

const VERDICT_STYLE: Record<Decision, { pill: string; dot: string; label: string }> = {
  advance: { pill: "bg-advance-soft text-advance", dot: "bg-advance-fill", label: "Advance" },
  escalate: { pill: "bg-escalate-soft text-escalate", dot: "bg-escalate-fill", label: "Escalate" },
  pass: { pill: "bg-pass-soft text-pass", dot: "bg-pass-fill", label: "Pass" },
};

export function VerdictIcon({ decision, size = 14 }: { decision: Decision; size?: number }) {
  if (decision === "advance") return <IconArrowUpRight size={size} strokeWidth={2.4} />;
  if (decision === "escalate") return <IconAlert size={size} strokeWidth={2.2} />;
  return <IconMinus size={size} strokeWidth={2.6} />;
}

/** The verdict as a status pill: colour plus icon plus label, never colour alone. */
export function VerdictBadge({ decision, size = "md" }: { decision: Decision; size?: "sm" | "md" }) {
  const s = VERDICT_STYLE[decision];
  return (
    <span className={cx("inline-flex items-center gap-1 rounded-full font-semibold", s.pill, size === "sm" ? "px-2 py-0.5 text-[12px]" : "px-2.5 py-1 text-[13px]")}>
      <VerdictIcon decision={decision} size={size === "sm" ? 12 : 14} />
      {s.label}
    </span>
  );
}

export function verdictDot(decision: Decision): string {
  return VERDICT_STYLE[decision].dot;
}

export function Tag({ children, tone = "neutral", title }: { children: ReactNode; tone?: "neutral" | "accent" | "warn" | "good"; title?: string }) {
  const tones = {
    neutral: "bg-surface-2 text-muted",
    accent: "bg-accent-soft text-accent",
    warn: "bg-warn-soft text-warn",
    good: "bg-advance-soft text-advance",
  };
  return (
    <span title={title} className={cx("inline-flex items-center gap-1 whitespace-nowrap rounded-md px-1.5 py-[1px] text-[11.5px] font-medium", tones[tone])}>
      {children}
    </span>
  );
}

export function Notice({ tone, title, children, action }: { tone: "warn" | "danger" | "info"; title?: string; children: ReactNode; action?: ReactNode }) {
  const tones = { warn: "bg-warn-soft text-warn", danger: "bg-danger-soft text-danger", info: "bg-accent-soft text-accent" };
  return (
    <div className={cx("flex items-start gap-3 rounded-2xl px-4 py-3 text-[14px] leading-snug", tones[tone])} role={tone === "danger" ? "alert" : undefined}>
      <div className="min-w-0 flex-1">
        {title && <p className="font-semibold">{title}</p>}
        <div className={title ? "mt-0.5 opacity-90" : undefined}>{children}</div>
      </div>
      {action}
    </div>
  );
}

export function Spinner({ size = 16, className }: { size?: number; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} className={cx("animate-spin", className)} aria-hidden>
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.2" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Avatar({ name, size = 40 }: { name: string; size?: number }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("");
  return (
    <span
      aria-hidden
      className="inline-flex shrink-0 items-center justify-center rounded-full bg-surface-3 font-display font-semibold text-ink-2"
      style={{ width: size, height: size, fontSize: size * 0.38 }}
    >
      {initials || "?"}
    </span>
  );
}

// ---- overlay ----------------------------------------------------------------------------------

/** A bottom sheet on phones, a centred dialog on larger screens. */
export function Sheet({ open, onClose, title, children, footer }: { open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode }) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    panel.current?.focus();
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-6" role="dialog" aria-modal="true" aria-label={title}>
      <button type="button" aria-label="Close" onClick={onClose} className="anim-fade-in absolute inset-0 cursor-default bg-[var(--overlay)]" />
      <div
        ref={panel}
        tabIndex={-1}
        className="anim-sheet-up relative flex max-h-[92dvh] w-full max-w-lg flex-col rounded-t-[28px] bg-surface shadow-float outline-none sm:rounded-[28px]"
      >
        <div className="mx-auto mt-2.5 h-1.5 w-10 rounded-full bg-surface-3 sm:hidden" aria-hidden />
        <div className="flex items-center justify-between px-6 pb-2 pt-4">
          <h2 className="font-display text-[21px] font-semibold tracking-[-0.01em]">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="-mr-2 rounded-full p-2 text-muted hover:bg-surface-2 hover:text-ink">
            <IconX size={20} />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-4">{children}</div>
        {footer && <div className="border-t border-line px-6 pb-[max(env(safe-area-inset-bottom),16px)] pt-3">{footer}</div>}
      </div>
    </div>
  );
}

export function Disclaimer({ text, className }: { text?: string; className?: string }) {
  return (
    <p className={cx("text-[12px] leading-relaxed text-faint", className)}>
      {text ??
        "Screening aid, not investment advice. The model estimates the chance of a large outcome from a founder's background on the day the company was founded. It was trained on generated data, so its accuracy on real founders is unknown. Public information only; nothing is stored after the session."}
    </p>
  );
}

export function Logo({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="9" fill="var(--ink)" />
      <path d="M8 21.5 13 16l3.5 3L24 10.5" fill="none" stroke="var(--bg)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="24" cy="10.5" r="2.4" fill="var(--accent)" stroke="var(--ink)" strokeWidth="1" />
    </svg>
  );
}
