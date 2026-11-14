"use client";

// The home question: one box to screen a founder by name, LinkedIn or website.
import Link from "next/link";
import { useState } from "react";

import { IconArrowRight } from "@/components/icons";
import { Notice, Spinner, cx, linkClass } from "@/components/ui";
import { parseFounder, useStartScreening } from "@/lib/useScreening";

export function QuickScreen() {
  const [q, setQ] = useState("");
  const { start, busy, error, setError } = useStartScreening();
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const founder = parseFounder(q);
        if (!founder) return setError("Type a founder's name, or paste a LinkedIn or website link.");
        start({ founder, options: { research: true } });
      }}
    >
      <label htmlFor="quick" className="block text-[40px] font-extrabold leading-[0.98] tracking-[-0.04em] sm:text-[52px] lg:text-[60px]">
        Who&apos;s the founder?
      </label>
      <div className="mt-5 flex h-[64px] items-center gap-2 rounded-[20px] border-2 border-ink bg-surface pl-5 pr-2 transition-shadow focus-within:shadow-[0_0_0_4px_var(--surface-3)] lg:h-[72px] lg:pl-6 lg:pr-2.5">
        <input
          id="quick"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Name, LinkedIn or website"
          autoComplete="off"
          autoCapitalize="words"
          enterKeyHint="go"
          className="min-w-0 flex-1 bg-transparent text-[18px] font-medium outline-none placeholder:font-normal placeholder:text-faint lg:text-[20px]"
        />
        <button
          type="submit"
          disabled={busy !== null || !q.trim()}
          aria-label="Screen founder"
          className="flex h-12 shrink-0 items-center gap-2 rounded-[14px] bg-accent px-4 text-[15.5px] font-bold text-accent-ink transition-[background,opacity,transform] hover:bg-accent-hover active:scale-95 disabled:opacity-30 lg:h-[52px] lg:px-5"
        >
          <span className="hidden sm:inline">Screen</span>
          {busy ? <Spinner /> : <IconArrowRight size={20} strokeWidth={2.4} />}
        </button>
      </div>
      <p className="mt-3 text-[13.5px] leading-snug text-muted">
        Reads only what was public before they started the company.{" "}
        <Link href={q.trim() ? `/new?q=${encodeURIComponent(q.trim())}` : "/new"} className={cx(linkClass, "whitespace-nowrap")}>
          Add what you know
        </Link>{" "}
        or{" "}
        <Link href="/batch" className={cx(linkClass, "whitespace-nowrap")}>
          screen a list
        </Link>
      </p>
      {error && (
        <div className="mt-3">
          <Notice tone="danger">{error}</Notice>
        </div>
      )}
    </form>
  );
}
