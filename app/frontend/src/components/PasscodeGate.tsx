"use client";

// Asks for the backend's passcode (ACCESS_TOKEN) the first time the service refuses a request.
import { useEffect, useState } from "react";

import { IconLock } from "@/components/icons";
import { Button } from "@/components/ui";
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
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-[var(--overlay)] sm:items-center" role="dialog" aria-modal="true" aria-labelledby="passcode-title">
      <form
        className="anim-sheet-up w-full max-w-md rounded-t-[30px] bg-surface px-6 pb-[max(env(safe-area-inset-bottom),20px)] pt-7 shadow-float sm:rounded-[30px] sm:pb-7"
        onSubmit={(e) => {
          e.preventDefault();
          if (!value.trim()) return;
          setPasscode(value.trim());
          window.location.reload();
        }}
      >
        <span className="flex h-12 w-12 items-center justify-center rounded-[14px] bg-ink text-bg">
          <IconLock size={22} />
        </span>
        <h2 id="passcode-title" className="mt-5 text-[30px] font-extrabold leading-[1] tracking-[-0.035em]">
          Enter your passcode
        </h2>
        <p className="mt-2 text-[15px] leading-snug text-muted">
          {wrong ? "That passcode didn't work. Try again." : "This screening service is private. The passcode is kept only until you close the app."}
        </p>
        <label htmlFor="passcode" className="sr-only">
          Passcode
        </label>
        <input
          id="passcode"
          autoFocus
          type="password"
          autoComplete="current-password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="mt-5 h-14 w-full rounded-[14px] border-2 border-line-strong bg-surface px-4 outline-none transition-colors placeholder:text-faint focus:border-ink"
          placeholder="Passcode"
        />
        <Button type="submit" size="lg" full className="mt-4">
          Continue
        </Button>
      </form>
    </div>
  );
}
