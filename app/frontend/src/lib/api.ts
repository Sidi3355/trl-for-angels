// Client for the screening backend (app/backend; API surface in app/contract/README.md).
// Everything runs in the browser. The optional passcode (the backend's ACCESS_TOKEN) is kept in
// sessionStorage only, so it is gone when the tab or app closes.

import type {
  BatchResponse,
  Health,
  InvestorInput,
  Memo,
  ScreeningJob,
  Thresholds,
  WhatIfRequest,
  WhatIfResponse,
  PushWatchRequest,
  PushWatchResponse,
  NoteSortRequest,
  NoteSortResponse,
  NoteTranscript,
} from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

const PASSCODE_KEY = "screener.passcode";
const UNAUTHORIZED_EVENT = "screener:unauthorized";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public retryable = false,
    public details: unknown[] = [],
  ) {
    super(message);
  }
}

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

export function getPasscode(): string | null {
  try {
    return storage()?.getItem(PASSCODE_KEY) ?? null;
  } catch {
    return null;
  }
}

export function setPasscode(value: string | null) {
  try {
    if (value) storage()?.setItem(PASSCODE_KEY, value);
    else storage()?.removeItem(PASSCODE_KEY);
  } catch {
    // private mode or blocked storage: the passcode just isn't remembered
  }
}

/** Fires when the backend says the passcode is missing or wrong; PasscodeGate listens. */
export function onUnauthorized(listener: () => void): () => void {
  window.addEventListener(UNAUTHORIZED_EVENT, listener);
  return () => window.removeEventListener(UNAUTHORIZED_EVENT, listener);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const code = getPasscode();
  if (code) headers.set("X-Access-Token", code);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" });
  } catch {
    throw new ApiError(0, "network", "Can't reach the screening service. Check your connection and try again.", true);
  }
  if (res.status === 401) {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    throw new ApiError(401, "unauthorized", "This app needs its passcode.");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const err = body?.error;
    throw new ApiError(
      res.status,
      err?.code ?? "http_error",
      res.status === 404
        ? "Not found. Screenings are kept for a limited time and then deleted."
        : err?.message ?? `The service answered ${res.status}.`,
      err?.retryable ?? res.status >= 500,
      body?.details ?? [],
    );
  }
  return body as T;
}

let thresholdsPromise: Promise<Thresholds> | null = null;

export const api = {
  health: () => request<Health>("/health"),
  demoFounders: () => request<InvestorInput[]>("/v1/demo/founders"),
  startScreening: (input: InvestorInput) =>
    request<ScreeningJob>("/v1/screenings", { method: "POST", body: JSON.stringify(input) }),
  job: (jobId: string) => request<ScreeningJob>(`/v1/screenings/${encodeURIComponent(jobId)}`),
  memo: (memoId: string) => request<Memo>(`/v1/memos/${encodeURIComponent(memoId)}`),
  whatIf: (memoId: string, body: WhatIfRequest) =>
    request<WhatIfResponse>(`/v1/memos/${encodeURIComponent(memoId)}/what-if`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** Screen a list: the CSV columns are in app/contract/README.md ("Batch CSV columns"). */
  startBatchCsv: (csv: string) =>
    request<BatchResponse>("/v1/batches", { method: "POST", body: csv, headers: { "Content-Type": "text/csv" } }),
  batch: (batchId: string) => request<BatchResponse>(`/v1/batches/${encodeURIComponent(batchId)}`),
  pushKey: () => request<{ schema_version: string; public_key: string }>("/v1/push/key"),
  notifyWhenDone: (kind: "screening" | "batch", id: string, body: PushWatchRequest) =>
    request<PushWatchResponse>(`/v1/${kind === "batch" ? "batches" : "screenings"}/${encodeURIComponent(id)}/notify`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** A voice note's words. The body is the recording itself; the server doesn't keep it. */
  transcribeNote: (audio: Blob) =>
    request<NoteTranscript>("/v1/notes/transcribe", {
      method: "POST",
      body: audio,
      headers: { "Content-Type": audio.type || "audio/webm" },
    }),
  /** Template fields found in free-form notes, for the investor to check before screening. */
  sortNote: (body: NoteSortRequest) =>
    request<NoteSortResponse>("/v1/notes/sort", { method: "POST", body: JSON.stringify(body) }),
  /** The val lookup table behind the risk control. Fetched once per page load. */
  thresholds: () => {
    thresholdsPromise ??= request<Thresholds>("/v1/artifacts/thresholds").catch((e) => {
      thresholdsPromise = null;
      throw e;
    });
    return thresholdsPromise;
  },
};

/** SSE URL for a screening's progress. EventSource can't send headers, so the passcode goes in the query. */
export function eventsUrl(jobId: string): string {
  const code = getPasscode();
  const q = code ? `?access_token=${encodeURIComponent(code)}` : "";
  return `${API_URL}/v1/screenings/${encodeURIComponent(jobId)}/events${q}`;
}
