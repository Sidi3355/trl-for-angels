"use client";

// The fictional demo founders, as tappable rows. Canned research, so they run instantly.
import { useEffect, useState } from "react";

import { IconArrowRight } from "@/components/icons";
import { Avatar, Spinner, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { hostOf, sectorLabel } from "@/lib/format";
import type { InvestorInput } from "@/lib/types";

export function Examples({ onPick, busy, columns = false }: { onPick: (input: InvestorInput, key: string) => void; busy: string | null; columns?: boolean }) {
  const [demos, setDemos] = useState<InvestorInput[] | null>(null);
  useEffect(() => {
    api.demoFounders().then(setDemos, () => setDemos([]));
  }, []);

  const grid = cx("grid gap-2.5", columns && "sm:grid-cols-3");
  if (demos === null) {
    return (
      <div className={grid}>
        {[0, 1, 2].map((i) => (
          <div key={i} className="skeleton h-[68px] rounded-[16px]" />
        ))}
      </div>
    );
  }
  if (!demos.length) return null;

  return (
    <div className={grid}>
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
            className="group flex min-w-0 items-center gap-3 rounded-[16px] border border-line-strong p-3 text-left transition-[border-color,background,transform] duration-150 hover:border-ink hover:bg-surface active:scale-[0.985] disabled:opacity-60"
          >
            <Avatar name={name} size={42} />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[15.5px] font-bold tracking-[-0.01em]">{name}</span>
              <span className="block truncate text-[13px] text-muted">{[company, sector].filter(Boolean).join(" · ")}</span>
            </span>
            {busy === key ? <Spinner className="mr-1 text-muted" /> : <IconArrowRight size={18} className="mr-1 text-faint transition-[transform,color] group-hover:translate-x-0.5 group-hover:text-ink" />}
          </button>
        );
      })}
    </div>
  );
}
