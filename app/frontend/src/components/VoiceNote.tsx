"use client";

// Record a voice note (up to a minute) and get its words back from the backend's speech-to-text.
// The recording goes straight to the backend and isn't kept anywhere; the parent decides what to do
// with the words (they join the notes, then fill the form for the investor to check).
import { useEffect, useRef, useState } from "react";

import { IconMic, IconStop } from "@/components/icons";
import { Spinner, cx } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { pickAudioType } from "@/lib/notes";
import type { NoteTranscript } from "@/lib/types";

export const MAX_SECONDS = 60;
export type VoicePhase = "idle" | "starting" | "recording" | "transcribing";

function micError(e: unknown): string {
  const name = (e as { name?: string })?.name;
  if (name === "NotAllowedError" || name === "SecurityError")
    return "Microphone access is blocked. Allow it for Halomark (on iPhone: Settings, then Safari or the app), then try again.";
  if (name === "NotFoundError") return "No microphone found on this device.";
  return "Couldn't start the microphone. Try again.";
}

export function VoiceNote({
  onText,
  onError,
  onPhase,
  disabled,
}: {
  onText: (t: NoteTranscript) => void;
  onError: (message: string) => void;
  onPhase?: (p: VoicePhase) => void;
  disabled?: boolean;
}) {
  const [supported, setSupported] = useState<boolean | null>(null);
  const [phase, setPhaseState] = useState<VoicePhase>("idle");
  const [seconds, setSeconds] = useState(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const cancelled = useRef(false);

  const setPhase = (p: VoicePhase) => {
    setPhaseState(p);
    onPhase?.(p);
  };

  // Known only in the browser, so decided after mount (no hydration mismatch).
  useEffect(() => {
    setSupported(typeof window !== "undefined" && "MediaRecorder" in window && !!navigator.mediaDevices?.getUserMedia);
    return () => {
      cancelled.current = true;
      if (timer.current) clearInterval(timer.current);
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  function release() {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
  }

  async function start() {
    setPhase("starting");
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    } catch (e) {
      setPhase("idle");
      onError(micError(e));
      return;
    }
    const type = pickAudioType((t) => MediaRecorder.isTypeSupported(t));
    const rec = new MediaRecorder(stream.current, type ? { mimeType: type } : undefined);
    chunks.current = [];
    rec.ondataavailable = (ev) => ev.data.size && chunks.current.push(ev.data);
    rec.onstop = () => void finish(rec.mimeType || type || "audio/webm");
    recorder.current = rec;
    rec.start(1000);
    setSeconds(0);
    setPhase("recording");
    const began = Date.now();
    timer.current = setInterval(() => {
      const s = Math.floor((Date.now() - began) / 1000);
      setSeconds(s);
      if (s >= MAX_SECONDS && rec.state === "recording") rec.stop();
    }, 250);
  }

  function stop() {
    if (recorder.current?.state === "recording") recorder.current.stop();
  }

  async function finish(mimeType: string) {
    release();
    if (cancelled.current) return;
    const audio = new Blob(chunks.current, { type: mimeType.split(";")[0] });
    chunks.current = [];
    if (audio.size < 1500) {
      setPhase("idle");
      onError("That was too short to hear anything. Hold on a second longer, then tap stop.");
      return;
    }
    setPhase("transcribing");
    try {
      const t = await api.transcribeNote(audio);
      if (!cancelled.current) onText(t);
    } catch (e) {
      if (!cancelled.current) onError(e instanceof ApiError ? e.message : "Couldn't transcribe the note. Try again.");
    } finally {
      if (!cancelled.current) setPhase("idle");
    }
  }

  if (supported === false) return null;
  const recording = phase === "recording";
  const left = MAX_SECONDS - seconds;
  return (
    <button
      type="button"
      onClick={recording ? stop : start}
      disabled={disabled || supported === null || phase === "starting" || phase === "transcribing"}
      aria-label={recording ? `Stop recording, ${left} seconds left` : "Record a voice note"}
      className={cx(
        "inline-flex h-10 shrink-0 items-center gap-2 rounded-full px-4 text-[14.5px] font-semibold transition-[background,transform] duration-150 active:scale-[0.97] disabled:opacity-45",
        recording ? "bg-ink text-bg" : "border border-line-strong text-ink hover:border-ink",
      )}
    >
      {phase === "transcribing" || phase === "starting" ? (
        <>
          <Spinner /> {phase === "starting" ? "Starting…" : "Transcribing…"}
        </>
      ) : recording ? (
        <>
          <span className="relative flex h-2.5 w-2.5" aria-hidden>
            <span className="absolute inline-flex h-full w-full rounded-full bg-danger opacity-60 motion-safe:animate-ping" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-danger" />
          </span>
          <span className="tabular">
            0:{String(seconds).padStart(2, "0")}
          </span>
          <IconStop size={16} /> Stop
        </>
      ) : (
        <>
          <IconMic size={18} /> Record
        </>
      )}
    </button>
  );
}
