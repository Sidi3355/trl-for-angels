"use client";

// "You": a sign-in look-alike that creates an investor profile ON THIS DEVICE ONLY (no account on any
// server), and the profile itself. Settings, links and "delete all my data" live on /settings.
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { useApp } from "@/components/AppState";
import { IconChevronRight } from "@/components/icons";
import { Button, Card, ChipMulti, ChipPicker, Notice, Page, PageHeader, SectionTitle, Segmented, Spinner, Switch, Tag, linkClass } from "@/components/ui";
import { CHEQUES, GEOGRAPHIES, SECTORS, STAGES, initials, newProfile, type Profile } from "@/lib/profile";

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
          Go to the dashboard
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

function SettingsPointer() {
  return (
    <Link href="/settings" className="mt-12 flex items-center justify-between gap-4 rounded-[18px] border border-line bg-surface px-4 py-4 transition-colors hover:border-ink">
      <span>
        <span className="block text-[16px] font-bold tracking-[-0.015em]">Settings</span>
        <span className="block text-[13.5px] text-muted">Appearance, your bar, notifications, and deleting your data</span>
      </span>
      <IconChevronRight size={20} className="shrink-0 text-muted" />
    </Link>
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
        <SettingsPointer />
      </Page>
    );

  return (
    <Page>
      <header className="flex items-center gap-4 pb-6 pt-3 lg:pt-0">
        <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-accent text-[22px] font-bold tracking-[-0.02em] text-accent-ink" aria-hidden>
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

      <SettingsPointer />
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
