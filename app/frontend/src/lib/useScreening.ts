"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, api } from "@/lib/api";
import { SCHEMA_VERSION, type FounderIdentifier, type InvestorInput } from "@/lib/types";

/** "linkedin.com/in/x", "acme.com" or "Ada Moreno" -> the founder identifier the API takes. */
export function parseFounder(raw: string): FounderIdentifier | null {
  const s = raw.trim();
  if (!s) return null;
  const looksLikeUrl = /^https?:\/\//i.test(s) || (/^[\w-]+(\.[\w-]+)+(\/\S*)?$/.test(s) && !/\s/.test(s));
  if (looksLikeUrl) {
    try {
      const u = new URL(/^https?:\/\//i.test(s) ? s : `https://${s}`);
      return u.hostname.endsWith("linkedin.com") ? { linkedin_url: u.toString() } : { website_url: u.toString() };
    } catch {
      return null;
    }
  }
  return { name: s };
}

/** Start a screening and go to its progress screen. */
export function useStartScreening() {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function start(input: Omit<InvestorInput, "schema_version">, key = "main") {
    setError(null);
    setBusy(key);
    try {
      const job = await api.startScreening({ ...input, schema_version: SCHEMA_VERSION });
      router.push(`/screenings/${job.job_id}`);
    } catch (e) {
      setBusy(null);
      const err = e as ApiError;
      if (err.status === 401) return;
      setError(err.status === 422 ? "Some details don't fit. Check the founding date and fields, then try again." : err.message);
    }
  }
  /** Forget a started screening's spinner and error (for a component that stays mounted, like the intro). */
  function reset() {
    setBusy(null);
    setError(null);
  }
  return { start, busy, error, setError, reset };
}
