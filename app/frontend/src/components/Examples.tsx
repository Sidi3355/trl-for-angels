"use client";

// The fictional demo founders, as tappable cards. Canned research, so they run instantly.
import { useEffect, useState } from "react";

import { IconArrowRight } from "@/components/icons";
import { Avatar, Spinner, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { hostOf, sectorLabel } from "@/lib/format";
import type { InvestorInput } from "@/lib/types";

export function Examples({ onPick, busy, compact = false }: { onPick: (input: InvestorInput, key: string) => void; busy: string | null; compact?: boolean }) {
  const [demos, setDemos] = useState<InvestorInput[] | null>(null);
  useEffect(() => {
    api.demoFounders().then(setDemos, () => setDemos([]));
  }, []);

  if (demos === null) {
    return (
      <div className={cx("grid gap-3", compact ? "sm:grid-cols-3" : "sm:grid-cols-3")}>
        {[0, 1, 2].map((i) => (
          <div key={i} className="skeleton h-[76px] rounded-2xl" />
        ))}
      </div>
    );
  }
  if (!demos.length) return null;

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {demos.map((d, i) => {
        const name = d.founder.name ?? (d.founder.website_url ? hostOf(d.founder.website_url) : `Example ${i + 1}`);
        const company = d.founder.company_name ?? (d.founder.website_url ? hostOf(d.founder.website_url) : null);
        const sector = sectorLabel(d.fields?.industry);
        const key = `demo-${i}`;
        return (
          <button
            key={key}
            type="button"
            disabled={busy !== null}
            onClick={() => onPick(d, key)}
            className="group flex min-w-0 items-center gap-3 rounded-2xl border border-line bg-surface p-3 text-left shadow-card transition-[border-color,transform] hover:border-line-strong active:scale-[0.99] disabled:opacity-60"
          >
            <Avatar name={name} size={36} />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[15px] font-semibold">{name}</span>
              <span className="block truncate text-[13px] text-muted">{[company, sector].filter(Boolean).join(" · ")}</span>
            </span>
            {busy === key ? <Spinner className="text-muted" /> : <IconArrowRight size={18} className="text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />}
          </button>
        );
      })}
    </div>
  );
}
