"use client";

// "You": a sign-in look-alike that creates an investor profile ON THIS DEVICE ONLY (no account on any
// server), the profile itself, the app's settings, and "delete all my data". See lib/profile.ts.
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { useApp } from "@/components/AppState";
import { BarSummary } from "@/components/BarSheet";
import { IconChevronRight, IconLock } from "@/components/icons";
import { showIntro } from "@/components/Onboarding";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button, Card, ChipMulti, ChipPicker, Notice, Page, PageHeader, SectionTitle, Segmented, Spinner, Switch, Tag, cx, linkClass } from "@/components/ui";
import { API_URL, getPasscode, setPasscode } from "@/lib/api";
import { CHEQUES, GEOGRAPHIES, SECTORS, STAGES, deleteAllMyData, initials, newProfile, type Profile } from "@/lib/profile";
import { clearDeals } from "@/lib/session";

const row = "flex items-center justify-between gap-4 border-b border-line py-4";
const input =
  "mt-1.5 h-12 w-full rounded-[12px] border border-line-strong bg-surface px-3.5 text-[16px] outline-none transition-colors placeholder:text-faint focus:border-ink";

function Label({ children, note }: { children: React.ReactNode; note?: string }) {
  return (
    <div className="mb-2">
      <p className="text-[15px] font-bold tracking-[-0.01em]">{children}</p>
      {note && <p className="text-[13px] text-muted">{note}</p>}
    </div>
  );
}

function SignIn({ onDone }: { onDone: (p: Profile) => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  return (
    <>
      <PageHeader eyebrow="Halomark" title="Sign in" subtitle="Set up your investor profile. It stays on this device: there's no Halomark account on a server, so there's no password." />
      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim()) return setError("Add your name.");
          if (email.trim() && !/^\S+@\S+\.\S+$/.test(email.trim())) return setError("That email doesn't look right. Leave it blank if you like.");
          onDone(newProfile(name, email));
        }}
        className="space-y-4"
      >
        <Card className="space-y-4 px-4 py-5">
          <label className="block">
            <span className="eyebrow text-muted">Your name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" placeholder="e.g. Sam Rivera" className={input} />
          </label>
          <label className="block">
            <span className="eyebrow text-muted">Email (optional)</span>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" inputMode="email" autoComplete="email" placeholder="you@example.com" className={input} />
            <span className="mt-1 block text-[12.5px] text-faint">Kept on this device with your profile. Never sent anywhere.</span>
          </label>
        </Card>
        {error && <Notice tone="danger">{error}</Notice>}
        <Button type="submit" size="lg" full>
          Continue
        </Button>
        <p className="text-[13px] leading-relaxed text-muted">
          By continuing you agree to the draft{" "}
          <Link href="/terms" className={linkClass}>
            Terms
          </Link>{" "}
          and{" "}
          <Link href="/privacy" className={linkClass}>
            Privacy notice
          </Link>
          .
        </p>
      </form>
      <p className="mt-8 text-[14px] text-muted">
        Just looking? You can screen founders without a profile.{" "}
        <Link href="/" className={linkClass}>
          Go to Founders
        </Link>
      </p>
    </>
  );
}

function ProfileForm({ profile, onSave }: { profile: Profile; onSave: (p: Profile) => boolean }) {
  const [p, setP] = useState(profile);
  const [saved, setSaved] = useState<"" | "saved" | "session">("");
  const set = (patch: Partial<Profile>) => {
    setP((x) => ({ ...x, ...patch }));
    setSaved("");
  };
  const setDefault = (patch: Partial<Profile["defaults"]>) => set({ defaults: { ...p.defaults, ...patch } });
  return (
    <form
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        setSaved(onSave({ ...p, name: p.name.trim() || profile.name, email: p.email.trim() }) ? "saved" : "session");
      }}
      className="space-y-6"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="eyebrow text-muted">Name</span>
          <input value={p.name} onChange={(e) => set({ name: e.target.value })} autoComplete="name" className={input} />
        </label>
        <label className="block">
          <span className="eyebrow text-muted">Email</span>
          <input value={p.email} onChange={(e) => set({ email: e.target.value })} type="email" autoComplete="email" placeholder="Optional" className={input} />
        </label>
      </div>
      <div>
        <Label>Sectors you invest in</Label>
        <ChipMulti label="Sectors" values={p.sectors} onChange={(sectors) => set({ sectors })} options={SECTORS.map((s) => ({ value: s, label: s }))} />
        <div className="mt-3 flex items-center justify-between gap-4 rounded-[14px] bg-surface-2 px-4 py-3">
          <label htmlFor="only-sectors" className="min-w-0 text-[14px] leading-snug">
            <span className="block font-semibold">Only my sectors</span>
            <span className="block text-muted">Founders outside them get Pass, whatever their chance.</span>
          </label>
          <Switch id="only-sectors" label="Only my sectors" checked={p.only_my_sectors} onChange={(only_my_sectors) => set({ only_my_sectors })} />
        </div>
      </div>
      <div>
        <Label>Stage</Label>
        <ChipMulti label="Stage" values={p.stages} onChange={(stages) => set({ stages: stages as Profile["stages"] })} options={STAGES.map(([value, label]) => ({ value, label }))} />
      </div>
      <div>
        <Label>Typical cheque</Label>
        <ChipPicker label="Typical cheque" value={p.cheque} onChange={(cheque) => set({ cheque })} options={CHEQUES.map(([value, label]) => ({ value, label }))} />
      </div>
      <div>
        <Label>Geography</Label>
        <ChipMulti label="Geography" values={p.geographies} onChange={(geographies) => set({ geographies })} options={GEOGRAPHIES.map((g) => ({ value: g, label: g }))} />
      </div>
      <div className="space-y-4 rounded-[18px] border border-line p-4">
        <Label note="Saving sets Your bar to these. Change it per session any time.">Your default bar</Label>
        <Segmented
          label="Default target"
          size="lg"
          value={p.defaults.target}
          onChange={(target) => setDefault({ target })}
          options={[
            { value: "$50M", label: "$50M+", hint: "Solid exit" },
            { value: "$500M", label: "$500M+", hint: "Big outcome" },
            { value: "$1B", label: "$1B+", hint: "Unicorn" },
          ]}
        />
        <Segmented
          label="Default timeline"
          value={p.defaults.timeline_years}
          onChange={(timeline_years) => setDefault({ timeline_years })}
          options={[
            { value: null, label: "Any time" },
            { value: 8, label: "8 years" },
            { value: 5, label: "5 years" },
          ]}
        />
        <Segmented
          label="Default risk appetite"
          value={p.defaults.risk}
          onChange={(risk) => setDefault({ risk })}
          options={[
            { value: "cautious", label: "Cautious" },
            { value: "balanced", label: "Balanced" },
            { value: "bold", label: "Bold" },
          ]}
        />
      </div>
      <p className="text-[13px] leading-relaxed text-muted">Stage, cheque size and geography are for your own reference for now: the model doesn&apos;t use them.</p>
      <div className="flex flex-wrap items-center gap-4">
        <Button type="submit" size="lg">
          Save profile
        </Button>
        <span role="status" className="text-[14px] font-semibold text-advance">
          {saved === "saved" && "Saved on this device. Your bar is updated."}
          {saved === "session" && <span className="text-warn">Saved until you close the app: this browser blocks storage.</span>}
        </span>
      </div>
    </form>
  );
}

function LinkRow({ href, title, note }: { href: string; title: string; note?: string }) {
  return (
    <Link href={href} className="flex items-center justify-between gap-4 border-b border-line py-3.5 transition-opacity active:opacity-60">
      <span className="min-w-0">
        <span className="block text-[15.5px] font-semibold">{title}</span>
        {note && <span className="block text-[13.5px] text-muted">{note}</span>}
      </span>
      <IconChevronRight size={18} className="shrink-0 text-muted" />
    </Link>
  );
}

function DeleteAll() {
  const [step, setStep] = useState<"idle" | "confirm" | "busy">("idle");
  return (
    <section className="mt-12" aria-labelledby="delete">
      <SectionTitle id="delete">Delete all my data</SectionTitle>
      <p className="max-w-[62ch] text-[14.5px] leading-relaxed text-ink-2">
        Removes everything Halomark keeps on this device: your profile, your bar, this session&apos;s founders, a saved passcode and notification sign-ups. Our servers keep nothing after the session anyway: a
        screening is held in memory for up to about two hours, then deleted.
      </p>
      {step === "idle" ? (
        <button type="button" onClick={() => setStep("confirm")} className="mt-4 h-11 rounded-full border border-danger px-5 text-[15px] font-semibold text-danger transition-colors hover:bg-danger-soft">
          Delete all my data
        </button>
      ) : (
        <div className="mt-4 rounded-[16px] bg-danger-soft p-4" role="alertdialog" aria-label="Confirm deleting your data">
          <p className="text-[15px] font-bold text-danger">Delete everything on this device? This can&apos;t be undone.</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={step === "busy"}
              onClick={async () => {
                setStep("busy");
                await deleteAllMyData();
                window.location.assign("/account?deleted=1");
              }}
              className="inline-flex h-11 items-center gap-2 rounded-full bg-danger px-5 text-[15px] font-semibold text-white disabled:opacity-60"
            >
              {step === "busy" && <Spinner />} Delete everything
            </button>
            <Button variant="secondary" onClick={() => setStep("idle")} disabled={step === "busy"}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}

/** Settings and links, shown whether or not there's a profile (so How it works, Terms etc. are always reachable). */
function SettingsAndLinks() {
  const { bar, openBarSheet, health, healthError, deals } = useApp();
  const [hasCode, setHasCode] = useState(false);
  const [cleared, setCleared] = useState(false);
  useEffect(() => setHasCode(Boolean(getPasscode())), []);
  return (
    <>
      <section className="mt-12">
        <SectionTitle>Settings</SectionTitle>
        <div className="-mt-3.5">
          <div className="space-y-2.5 border-b border-line py-4">
            <span className="block text-[15.5px] font-semibold">Appearance</span>
            <ThemeToggle />
          </div>
          <div className={row}>
            <span className="min-w-0">
              <span className="block text-[15.5px] font-semibold">Your bar</span>
              <span className="block text-[13.5px] text-muted">
                <BarSummary bar={bar} />
              </span>
            </span>
            <Button variant="secondary" onClick={openBarSheet}>
              Change
            </Button>
          </div>
          <div className={row}>
            <span className="min-w-0">
              <span className="block text-[15.5px] font-semibold">This session&apos;s founders</span>
              <span className="block text-[13.5px] text-muted">{cleared ? "Cleared." : `${deals.length} founder${deals.length === 1 ? "" : "s"}. Gone when you close the app.`}</span>
            </span>
            <Button variant="secondary" disabled={!deals.length} onClick={() => { clearDeals(); setCleared(true); }}>
              Clear
            </Button>
          </div>
          {hasCode && (
            <div className={row}>
              <span className="flex items-center gap-2 text-[15.5px] font-semibold">
                <IconLock size={17} className="text-muted" /> Passcode saved for this session
              </span>
              <Button variant="secondary" onClick={() => { setPasscode(null); setHasCode(false); }}>
                Forget
              </Button>
            </div>
          )}
          <div className={row}>
            <span className="min-w-0">
              <span className="block text-[15.5px] font-semibold">The intro</span>
              <span className="block text-[13.5px] text-muted">The three first-run screens.</span>
            </span>
            <Button variant="secondary" onClick={showIntro}>
              Show again
            </Button>
          </div>
          <div className={row}>
            <span className="min-w-0">
              <span className="block text-[15.5px] font-semibold">Service</span>
              <span className="block truncate text-[13.5px] text-muted">{API_URL.replace(/^https?:\/\//, "")}</span>
            </span>
            <span className={cx("flex shrink-0 items-center gap-1.5 text-[13.5px] font-semibold", healthError ? "text-danger" : health ? "text-ink" : "text-muted")}>
              {health && !healthError && <span className={cx("h-2 w-2 rounded-full", health.mock ? "bg-escalate-fill" : "bg-advance-fill")} aria-hidden />}
              {healthError ? "Offline" : health ? (health.mock ? "Online · example scores" : "Online") : "Checking…"}
            </span>
          </div>
        </div>
      </section>

      <section className="mt-12">
        <SectionTitle>How Halomark works</SectionTitle>
        <div className="-mt-3.5">
          <LinkRow href="/about" title="How it works" note="From a name to Meet, Look closer or Pass" />
          <LinkRow href="/calibration" title="How accurate are the odds?" note="What 30% really means" />
          <LinkRow href="/model-card" title="Model card" note="The model, its data and its limits" />
          <LinkRow href="/plans" title="Plans" note="Free for now" />
          <LinkRow href="/terms" title="Terms" note="Draft" />
          <LinkRow href="/privacy" title="Privacy" note="Draft" />
        </div>
      </section>

      <DeleteAll />
    </>
  );
}

function Account() {
  const { ready, profile, saveProfile } = useApp();
  const params = useSearchParams();
  const deleted = params.get("deleted") === "1";

  if (!ready)
    return (
      <Page>
        <div className="flex h-40 items-center justify-center text-muted">
          <Spinner size={20} />
        </div>
      </Page>
    );
  if (!profile)
    return (
      <Page>
        {deleted && (
          <div className="pb-2 pt-3">
            <Notice tone="info" title="Deleted">
              Everything Halomark kept on this device is gone.
            </Notice>
          </div>
        )}
        <SignIn onDone={(p) => saveProfile(p)} />
        <SettingsAndLinks />
      </Page>
    );

  return (
    <Page>
      <header className="flex items-center gap-4 pb-6 pt-3 lg:pt-0">
        <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-ink text-[22px] font-bold tracking-[-0.02em] text-bg" aria-hidden>
          {initials(profile.name)}
        </span>
        <div className="min-w-0">
          <h1 className="truncate text-[30px] font-extrabold leading-tight tracking-[-0.035em]">{profile.name}</h1>
          <p className="flex flex-wrap items-center gap-2 text-[14px] text-muted">
            {profile.email && <span className="truncate">{profile.email}</span>}
            <Tag>Stored on this device only</Tag>
          </p>
        </div>
      </header>

      <section aria-labelledby="profile">
        <SectionTitle id="profile">Your investing profile</SectionTitle>
        <ProfileForm profile={profile} onSave={saveProfile} />
      </section>

      <SettingsAndLinks />
    </Page>
  );
}

export default function AccountPage() {
  return (
    <Suspense>
      <Account />
    </Suspense>
  );
}
