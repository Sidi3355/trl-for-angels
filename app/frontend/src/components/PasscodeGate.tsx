"use client";

// Asks for the backend's passcode (ACCESS_TOKEN) the first time the service refuses a request.
import { useEffect, useState } from "react";

import { getPasscode, onUnauthorized, setPasscode } from "@/lib/api";

export function PasscodeGate() {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const [wrong, setWrong] = useState(false);

  useEffect(
    () =>
      onUnauthorized(() => {
        setWrong(Boolean(getPasscode()));
        setOpen(true);
      }),
    [],
  );

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center" role="dialog" aria-modal="true" aria-labelledby="passcode-title">
      <form
        className="rise-in w-full max-w-md rounded-t-3xl bg-card px-5 pb-[max(env(safe-area-inset-bottom),20px)] pt-5 sm:rounded-3xl"
        onSubmit={(e) => {
          e.preventDefault();
          if (!value.trim()) return;
          setPasscode(value.trim());
          window.location.reload();
        }}
      >
        <h2 id="passcode-title" className="text-[20px] font-semibold">
          Enter the passcode
        </h2>
        <p className="mt-1 text-[15px] text-muted">
          {wrong ? "That passcode didn't work. Try again." : "This screening service is private. The passcode is kept only until you close the app."}
        </p>
        <input
          autoFocus
          type="password"
          autoComplete="current-password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="mt-4 w-full rounded-xl bg-card-2 px-4 py-3 outline-none ring-accent focus:ring-2"
          placeholder="Passcode"
          aria-label="Passcode"
        />
        <button type="submit" className="mt-4 w-full rounded-xl bg-accent py-3.5 text-[17px] font-semibold text-accent-ink active:opacity-80">
          Continue
        </button>
      </form>
    </div>
  );
}
