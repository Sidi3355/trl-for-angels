"use client";

// Shared into Halomark: from Android's share menu (the manifest's share_target) or an iPhone Shortcut
// that opens /share?url=… . Shows what came in and screens it with one tap, so a stray share costs nothing.
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { IconGlobe, IconLink } from "@/components/icons";
import { Button, Card, Notice, Page, PageHeader, Spinner, linkClass } from "@/components/ui";
import { hostOf } from "@/lib/format";
import type { FounderIdentifier } from "@/lib/types";
import { parseFounder, useStartScreening } from "@/lib/useScreening";

const URL_RE = /(https?:\/\/[^\s<>"']+|(?:www\.)?linkedin\.com\/[^\s<>"']+)/i;

/** The shared link (if any) and a likely name, e.g. "Ada Moreno - Founder | LinkedIn" -> "Ada Moreno". */
function readShare(p: URLSearchParams): { link: FounderIdentifier | null; name: string } {
  const pieces = [p.get("url"), p.get("text"), p.get("title")].filter(Boolean) as string[];
  let link: FounderIdentifier | null = null;
  for (const piece of pieces) {
    const m = piece.match(URL_RE);
    if (m) {
      link = parseFounder(m[1].replace(/[),.;]+$/, ""));
      if (link && !link.name) break;
      link = null;
    }
  }
  const title = (p.get("title") ?? "").trim();
  const textNoUrl = (p.get("text") ?? "").replace(URL_RE, "").trim();
  const raw = title || (!link && textNoUrl.length <= 80 ? textNoUrl : "");
  const name = raw.split(/\s[|–—-]\s/)[0].replace(/\s+/g, " ").trim();
  return { link, name: /^https?:/i.test(name) ? "" : name.slice(0, 120) };
}

function SharePage() {
  const params = useSearchParams();
  const initial = readShare(params);
  const [name, setName] = useState(initial.name);
  const { start, busy, error } = useStartScreening();
  const link = initial.link;
  const url = link?.linkedin_url ?? link?.website_url ?? null;

  if (!link && !initial.name) {
    return (
      <Page>
        <PageHeader eyebrow="Shared to Halomark" title="Nothing to screen" subtitle="What was shared didn't include a link or a name. Type the founder instead." />
        <Link href="/new" className={linkClass}>
          Screen a founder
        </Link>
      </Page>
    );
  }

  return (
    <Page>
      <PageHeader eyebrow="Shared to Halomark" title="Screen this founder?" subtitle="The agent reads only what was public before they started the company." />
      <Card className="divide-y divide-line overflow-hidden">
        {url && (
          <div className="flex items-center gap-3 px-4 py-4">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px] bg-ink text-bg">{link?.linkedin_url ? <IconLink size={19} /> : <IconGlobe size={19} />}</span>
            <span className="min-w-0">
              <span className="eyebrow block text-muted">{link?.linkedin_url ? "LinkedIn" : "Website"}</span>
              <span className="block truncate text-[16px] font-semibold">{hostOf(url) + new URL(url).pathname.replace(/\/$/, "")}</span>
            </span>
          </div>
        )}
        <div className="px-4 py-3.5">
          <label htmlFor="share-name" className="eyebrow block text-muted">
            Name {url && <span className="normal-case tracking-normal text-faint">(optional, helps the search)</span>}
          </label>
          <input id="share-name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="off" placeholder="e.g. Ada Moreno" className="mt-1.5 w-full bg-transparent text-[17px] font-medium outline-none placeholder:font-normal placeholder:text-faint" />
        </div>
      </Card>

      {error && <div className="mt-4"><Notice tone="danger">{error}</Notice></div>}

      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <Button
          size="lg"
          full
          disabled={busy !== null || (!url && !name.trim())}
          onClick={() => start({ founder: { ...(link ?? {}), ...(name.trim() ? { name: name.trim() } : {}) }, options: { research: true } })}
        >
          {busy && <Spinner />} Screen founder
        </Button>
        <Link href={`/new?q=${encodeURIComponent(url ?? name)}`} className="flex h-[52px] items-center justify-center rounded-full px-6 text-[16px] font-semibold text-ink underline decoration-line-strong underline-offset-4 hover:decoration-ink">
          Add what you know first
        </Link>
      </div>
    </Page>
  );
}

export default function Page_() {
  return (
    <Suspense>
      <SharePage />
    </Suspense>
  );
}
