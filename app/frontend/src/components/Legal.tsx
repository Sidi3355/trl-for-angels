// Shared pieces of the Terms and Privacy drafts: the "draft" banner and plain numbered sections.
import type { ReactNode } from "react";

import { Notice } from "@/components/ui";

export const LEGAL_UPDATED = "14 November 2026";

export function DraftBanner() {
  return (
    <Notice tone="warn" title="Draft for review">
      Not legal advice, and not yet reviewed by a lawyer. It describes how the Halomark prototype works today, and will change before any public launch.
    </Notice>
  );
}

export function Clause({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <section className="border-t border-line-strong py-6" aria-labelledby={`clause-${n}`}>
      <h2 id={`clause-${n}`} className="flex gap-3 text-[19px] font-bold tracking-[-0.02em]">
        <span className="cond w-6 shrink-0 text-[22px] font-black text-muted">{n}</span>
        {title}
      </h2>
      <div className="mt-2.5 space-y-2.5 pl-9 text-[15px] leading-relaxed text-ink-2 [&_li]:flex [&_li]:gap-3 [&_li]:before:mt-[0.62em] [&_li]:before:h-[3px] [&_li]:before:w-3 [&_li]:before:shrink-0 [&_li]:before:rounded-full [&_li]:before:bg-ink [&_li]:before:content-[''] [&_ul]:space-y-2">
        {children}
      </div>
    </section>
  );
}
