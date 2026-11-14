"use client";

// Building blocks shared by every screen.
import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { IconAlert, IconArrowUpRight, IconChevronLeft, IconMinus, IconX } from "@/components/icons";
import { HALO_VIEWBOX, MARK_HALO, MARK_PATH, MARK_SIZE } from "@/lib/mark";
import type { Decision } from "@/lib/types";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

// ---- layout -----------------------------------------------------------------------------------

/** A page's content column. `wide` for the two-column desktop layouts. */
export function Page({ children, wide = false, className }: { children: ReactNode; wide?: boolean; className?: string }) {
  return (
    <div
      className={cx(
        "mx-auto w-full pb-10 pl-[max(20px,env(safe-area-inset-left))] pr-[max(20px,env(safe-area-inset-right))] pt-2 sm:px-8 lg:px-12 lg:pt-12",
        wide ? "max-w-[1120px]" : "max-w-[720px]",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function PageHeader({ title, subtitle, back, action, eyebrow }: { title: ReactNode; subtitle?: ReactNode; back?: { href: string; label: string }; action?: ReactNode; eyebrow?: ReactNode }) {
  return (
    <header className="pb-6 pt-3 lg:pt-0">
      {back && (
        <Link href={back.href} className="-ml-1.5 mb-3 inline-flex items-center gap-0.5 rounded-lg py-1 pr-2 text-[14px] font-medium text-muted transition-colors hover:text-ink active:opacity-60">
          <IconChevronLeft size={18} /> {back.label}
        </Link>
      )}
      {eyebrow && <p className="eyebrow mb-2 text-muted">{eyebrow}</p>}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-[34px] font-extrabold leading-[1.02] tracking-[-0.035em] lg:text-[46px]">{title}</h1>
          {subtitle && <div className="mt-2.5 max-w-[54ch] text-[15.5px] leading-snug text-muted">{subtitle}</div>}
        </div>
        {action && <div className="shrink-0 pt-1">{action}</div>}
      </div>
    </header>
  );
}

export function SectionTitle({ children, action, id, note }: { children: ReactNode; action?: ReactNode; id?: string; note?: ReactNode }) {
  return (
    <div className="mb-3.5 border-t-2 border-ink pt-3">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id={id} className="text-[21px] font-bold leading-tight tracking-[-0.025em]">
          {children}
        </h2>
        {action}
      </div>
      {note && <p className="mt-1 text-[13.5px] leading-snug text-muted">{note}</p>}
    </div>
  );
}

/** A plain panel. Used sparingly: most sections sit straight on the paper under a rule. */
export function Card({ children, className, as: As = "div" }: { children: ReactNode; className?: string; as?: "div" | "section" }) {
  return <As className={cx("rounded-[18px] border border-line bg-surface", className)}>{children}</As>;
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
        "inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-[background,opacity,transform] duration-150 active:scale-[0.97] disabled:pointer-events-none disabled:opacity-45",
        size === "lg" ? "h-[54px] px-7 text-[16.5px]" : "h-10 px-4.5 text-[14.5px]",
        variant === "primary" && "bg-accent text-accent-ink hover:bg-accent-hover",
        variant === "secondary" && "bg-surface-3 text-ink hover:bg-line-strong",
        variant === "ghost" && "text-ink underline decoration-line-strong decoration-2 underline-offset-4 hover:decoration-ink",
        full && "w-full",
        className,
      )}
    >
      {children}
    </button>
  );
}

/** An inline text action: ink, underlined. */
export const linkClass = "font-semibold text-ink underline decoration-line-strong decoration-[1.5px] underline-offset-[3px] transition-colors hover:decoration-ink";

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
    <div role="radiogroup" aria-label={label} className="flex gap-1 rounded-[16px] bg-surface-2 p-1 ring-1 ring-inset ring-line">
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
              "flex-1 rounded-[12px] px-2 text-center transition-[background,color] duration-150",
              size === "lg" ? "py-2.5" : "py-2",
              on ? "bg-ink text-bg" : "text-ink-2 hover:bg-surface-3",
            )}
          >
            <span className={cx("block leading-tight", size === "lg" ? "text-[16px] font-bold tracking-[-0.01em]" : "text-[14px] font-semibold")}>{o.label}</span>
            {o.hint && <span className={cx("mt-0.5 block text-[11.5px] leading-tight", on ? "opacity-70" : "text-muted")}>{o.hint}</span>}
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
      className={cx("relative h-[32px] w-[54px] shrink-0 rounded-full transition-colors duration-200", checked ? "bg-ink" : "bg-line-strong")}
    >
      <span className={cx("absolute top-[3px] h-[26px] w-[26px] rounded-full bg-bg shadow-[0_1px_3px_rgba(0,0,0,0.3)] transition-[left] duration-200", checked ? "left-[25px]" : "left-[3px]")} />
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
              "h-10 rounded-full border px-4 text-[14.5px] font-medium transition-colors duration-150",
              on ? "border-ink bg-ink text-bg" : "border-line-strong text-ink-2 hover:border-ink",
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
  advance: { pill: "bg-advance-soft text-advance", dot: "bg-advance-fill", label: "Meet" },
  escalate: { pill: "bg-escalate-soft text-escalate", dot: "bg-escalate-fill", label: "Look closer" },
  pass: { pill: "bg-pass-soft text-pass", dot: "bg-pass-fill", label: "Pass" },
};

/** The slab colours: the verdict as a block of colour with its own ink. */
export const SLAB: Record<Decision, string> = {
  advance: "bg-[var(--slab-advance)] text-[var(--slab-advance-ink)]",
  escalate: "bg-[var(--slab-escalate)] text-[var(--slab-escalate-ink)]",
  pass: "bg-[var(--slab-pass)] text-[var(--slab-pass-ink)]",
};

export function VerdictIcon({ decision, size = 14 }: { decision: Decision; size?: number }) {
  if (decision === "advance") return <IconArrowUpRight size={size} strokeWidth={2.6} />;
  if (decision === "escalate") return <IconAlert size={size} strokeWidth={2.3} />;
  return <IconMinus size={size} strokeWidth={2.8} />;
}

/** The verdict as a status pill: colour plus icon plus label, never colour alone. */
export function VerdictBadge({ decision, size = "md" }: { decision: Decision; size?: "sm" | "md" }) {
  const s = VERDICT_STYLE[decision];
  return (
    <span className={cx("inline-flex items-center gap-1 rounded-full font-bold", s.pill, size === "sm" ? "px-2 py-[3px] text-[12px]" : "px-2.5 py-1 text-[13px]")}>
      <VerdictIcon decision={decision} size={size === "sm" ? 12 : 14} />
      {s.label}
    </span>
  );
}

/** The verdict struck as a hallmark: a cut-corner punch of the slab colour with the verdict's icon. */
export function VerdictTile({ decision, size = 44 }: { decision: Decision | null; size?: number }) {
  if (!decision) return <span className="skeleton punch shrink-0" style={{ width: size, height: size }} />;
  return (
    <span aria-hidden className={cx("punch inline-flex shrink-0 items-center justify-center", SLAB[decision])} style={{ width: size, height: size }}>
      <VerdictIcon decision={decision} size={Math.round(size * 0.45)} />
    </span>
  );
}

export function verdictDot(decision: Decision): string {
  return VERDICT_STYLE[decision].dot;
}

export function Tag({ children, tone = "neutral", title }: { children: ReactNode; tone?: "neutral" | "accent" | "warn" | "good"; title?: string }) {
  const tones = {
    neutral: "bg-surface-3 text-ink-2",
    accent: "bg-ink text-bg",
    warn: "bg-warn-soft text-warn",
    good: "bg-advance-soft text-advance",
  };
  return (
    <span title={title} className={cx("inline-flex items-center gap-1 whitespace-nowrap rounded-[6px] px-1.5 py-[2px] text-[11.5px] font-semibold leading-none", tones[tone])}>
      {children}
    </span>
  );
}

/** A footnote-style source number that jumps to the source list. */
export function SourceRef({ id }: { id: string }) {
  return (
    <a href={`#source-${id}`} className="tabular inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full border border-line-strong px-1 text-[11px] font-semibold leading-none text-ink-2 transition-colors hover:border-ink hover:bg-ink hover:text-bg">
      {id.replace(/^s/, "")}
    </a>
  );
}

export function Notice({ tone, title, children, action }: { tone: "warn" | "danger" | "info"; title?: string; children: ReactNode; action?: ReactNode }) {
  const tones = { warn: "bg-warn-soft text-warn", danger: "bg-danger-soft text-danger", info: "bg-surface-3 text-ink-2" };
  return (
    <div className={cx("flex items-start gap-3 rounded-[14px] px-4 py-3 text-[14px] leading-snug", tones[tone])} role={tone === "danger" ? "alert" : undefined}>
      <IconAlert size={18} className="mt-[1px] shrink-0" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-bold">{title}</p>}
        <div className={title ? "mt-0.5" : undefined}>{children}</div>
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

/** A monogram: the founder's initials, set tight in a square. */
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
      className="semi-cond inline-flex shrink-0 items-center justify-center rounded-[12px] bg-surface-3 font-extrabold tracking-[-0.02em] text-ink"
      style={{ width: size, height: size, fontSize: size * 0.42 }}
    >
      {initials || "?"}
    </span>
  );
}

/** Counts a number up (or across) to its new value. Jumps straight there with reduced motion. */
export function useCountTo(target: number, ms = 520): number {
  const [shown, setShown] = useState(target);
  const from = useRef(target);
  useEffect(() => {
    const start = from.current;
    if (start === target || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      from.current = target;
      setShown(target);
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const tick = (now: number) => {
      const k = Math.min(1, (now - t0) / ms);
      const v = start + (target - start) * (1 - Math.pow(1 - k, 3));
      from.current = v;
      setShown(v);
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return shown;
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
      <button type="button" aria-label="Close" onClick={onClose} className="anim-fade-in absolute inset-0 cursor-default bg-[var(--overlay)] backdrop-blur-[2px]" />
      <div
        ref={panel}
        tabIndex={-1}
        className="anim-sheet-up relative flex max-h-[92dvh] w-full max-w-[520px] flex-col rounded-t-[30px] bg-surface shadow-float outline-none sm:rounded-[30px]"
      >
        <div className="mx-auto mt-2.5 h-[5px] w-10 rounded-full bg-line-strong sm:hidden" aria-hidden />
        <div className="flex items-center justify-between px-6 pb-2 pt-4 sm:pt-6">
          <h2 className="text-[26px] font-extrabold tracking-[-0.03em]">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="-mr-1.5 flex h-9 w-9 items-center justify-center rounded-full bg-surface-2 text-ink-2 transition-colors hover:bg-surface-3 hover:text-ink">
            <IconX size={18} />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-5">{children}</div>
        {footer && <div className="border-t border-line px-6 pb-[max(env(safe-area-inset-bottom),16px)] pt-3">{footer}</div>}
      </div>
    </div>
  );
}

export function Disclaimer({ text, className }: { text?: string; className?: string }) {
  return (
    <p className={cx("max-w-[70ch] border-t border-line pt-4 text-[12.5px] leading-relaxed text-faint", className)}>
      {text ??
        "Screening aid, not investment advice. The model estimates the chance of a large outcome from a founder's background on the day the company was founded. It was trained on generated data, so its accuracy on real founders is unknown. Public information only; nothing is stored after the session."}
    </p>
  );
}

/**
 * The mark: a hallmark punch (the cut-corner stamp an assay office strikes into gold) with a halo
 * struck into it. One shape, so it takes whatever colour it's given: stamp-pad blue by default.
 */
export function Logo({ size = 32, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox={`0 0 ${MARK_SIZE} ${MARK_SIZE}`} className={cx("text-brand", className)} aria-hidden>
      <path d={MARK_PATH} fill="currentColor" fillRule="evenodd" />
    </svg>
  );
}

/** The halo on its own, in the current text colour: the O of the wordmark. Height sets its size. */
export function Halo({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg viewBox={HALO_VIEWBOX} className={className} style={style} aria-hidden>
      <path d={MARK_HALO} fill="currentColor" fillRule="evenodd" />
    </svg>
  );
}

/**
 * The name with the halo as its O, all in the text colour. Inside the app the halo stands alone; the
 * punch around it belongs to the app icon. `size` is the type size in pixels.
 */
export function Wordmark({ size = 17 }: { size?: number }) {
  return (
    <span role="img" aria-label="Halomark" className="wordmark" style={{ fontSize: size }}>
      <span aria-hidden>HAL</span>
      <Halo />
      <span aria-hidden>MARK</span>
    </span>
  );
}
