"use client";

// Plans: a MOCKUP of three subscription tiers with a monthly/yearly toggle. Nothing can be bought and
// there is no payment code: every feature is free while Halomark is a prototype. Prices are illustrative.
import { useState } from "react";

import { IconCheck } from "@/components/icons";
import { Page, PageHeader, Segmented, Tag, cx } from "@/components/ui";

type Period = "monthly" | "yearly";

const TIERS = [
  {
    name: "Free",
    blurb: "For trying Halomark on the founders in your inbox.",
    monthly: 0,
    yearly: 0,
    unit: "",
    features: ["5 screenings a month", "Research with linked sources", "Meet, Look closer or Pass, with the reasons", "Your profile and bar, kept on your device"],
    current: true,
  },
  {
    name: "Pro",
    blurb: "For angels screening every week.",
    monthly: 29,
    yearly: 290,
    unit: "a month",
    features: ["100 screenings a month", "Screen a whole list from a spreadsheet", "Voice notes that fill the form", "A notification when screening finishes", "Everything in Free"],
    featured: true,
  },
  {
    name: "Syndicate",
    blurb: "For syndicates and angel groups that screen together.",
    monthly: 99,
    yearly: 990,
    unit: "a month, up to 5 members",
    features: ["Everything in Pro, for 5 members", "Shared founders and memos", "A shared bar for the group", "Notes the whole group can see"],
  },
] as const;

function Price({ monthly, yearly, period, unit }: { monthly: number; yearly: number; period: Period; unit: string }) {
  if (monthly === 0)
    return (
      <p className="flex items-baseline gap-2">
        <span className="cond text-[56px] font-black leading-none">$0</span>
        <span className="text-[14px] text-muted">for ever</span>
      </p>
    );
  const perMonth = period === "monthly" ? monthly : Math.round(yearly / 12);
  return (
    <div>
      <p className="flex items-baseline gap-2">
        <span className="cond text-[56px] font-black leading-none">${perMonth}</span>
        <span className="text-[14px] text-muted">{unit}</span>
      </p>
      <p className="mt-1 h-5 text-[13px] text-muted">{period === "yearly" ? `$${yearly} billed once a year` : "Billed monthly"}</p>
    </div>
  );
}

export default function PlansPage() {
  const [period, setPeriod] = useState<Period>("monthly");
  return (
    <Page wide>
      <PageHeader title="Plans" subtitle="Every feature is free while Halomark is a prototype. Here's what paid plans could look like." />

      <div className="flex flex-wrap items-center gap-3">
        <div className="w-[260px]">
          <Segmented
            label="Billing period"
            value={period}
            onChange={setPeriod}
            options={[
              { value: "monthly", label: "Monthly" },
              { value: "yearly", label: "Yearly" },
            ]}
          />
        </div>
        <span className="text-[13.5px] font-semibold text-advance">Yearly: 2 months free</span>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        {TIERS.map((t) => (
          <section
            key={t.name}
            aria-labelledby={`tier-${t.name}`}
            className={cx("flex flex-col rounded-[22px] border p-5", "featured" in t ? "border-accent bg-surface shadow-[0_0_0_1px_var(--accent)]" : "border-line bg-surface")}
          >
            <div className="flex items-center justify-between gap-2">
              <h2 id={`tier-${t.name}`} className="text-[22px] font-extrabold tracking-[-0.03em]">
                {t.name}
              </h2>
              {"featured" in t && <Tag tone="accent">Most angels</Tag>}
              {"current" in t && <Tag>Your plan</Tag>}
            </div>
            <p className="mt-1 min-h-[42px] text-[14px] leading-snug text-muted">{t.blurb}</p>
            <div className="mt-4">
              <Price monthly={t.monthly} yearly={t.yearly} period={period} unit={t.unit} />
            </div>
            <ul className="mt-5 flex-1 space-y-2.5 border-t border-line pt-4">
              {t.features.map((f) => (
                <li key={f} className="flex gap-2.5 text-[14.5px] leading-snug">
                  <IconCheck size={18} className="mt-[1px] shrink-0 text-advance" />
                  {f}
                </li>
              ))}
            </ul>
            <button
              type="button"
              disabled
              aria-disabled="true"
              className={cx(
                "mt-6 h-12 w-full cursor-not-allowed rounded-full text-[15.5px] font-semibold",
                "current" in t ? "border border-line-strong text-muted" : "featured" in t ? "bg-accent text-accent-ink opacity-60" : "bg-surface-3 text-ink-2",
              )}
            >
              {"current" in t ? "Current plan" : "Coming soon"}
            </button>
          </section>
        ))}
      </div>

      <p className="mt-6 max-w-[70ch] text-[13px] leading-relaxed text-muted">
        Prices are illustrative and in US dollars. Nothing can be bought yet and nothing is charged. Screening limits and features may change before paid plans launch.
      </p>
    </Page>
  );
}
