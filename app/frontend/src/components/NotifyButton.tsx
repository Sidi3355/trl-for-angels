"use client";

// "Notify me when it's ready": one push notification when a screening or batch finishes.
import { useEffect, useState } from "react";

import { useApp } from "@/components/AppState";
import { IconBell, IconCheck } from "@/components/icons";
import { Spinner, cx } from "@/components/ui";
import { notifyWhenDone, pushSupport, type PushSupport } from "@/lib/push";

type State = "idle" | "working" | "on" | "sent" | "denied" | "error";

export function NotifyButton({ kind, id, className }: { kind: "screening" | "batch"; id: string; className?: string }) {
  const { bar } = useApp();
  const [support, setSupport] = useState<PushSupport>("no");
  const [state, setState] = useState<State>("idle");
  useEffect(() => setSupport(pushSupport()), []);

  if (support === "no") return null;
  if (support === "install")
    return (
      <p className={cx("text-[13.5px] leading-snug text-muted", className)}>
        <IconBell size={15} className="mr-1 inline-block align-[-2px]" />
        To be notified when it&apos;s ready, add Halomark to your Home Screen: Share, then Add to Home Screen.
      </p>
    );

  if (state === "on" || state === "sent")
    return (
      <p className={cx("inline-flex items-center gap-2 text-[14px] font-semibold text-ink", className)} role="status">
        <IconCheck size={17} strokeWidth={2.4} className="text-advance" />
        {state === "on" ? "We'll notify you when it's ready. You can leave the app." : "Notification sent."}
      </p>
    );

  return (
    <div className={className}>
      <button
        type="button"
        disabled={state === "working"}
        onClick={async () => {
          setState("working");
          try {
            const r = await notifyWhenDone(kind, id, bar);
            setState(r === "watching" ? "on" : r === "sent" ? "sent" : r === "denied" ? "denied" : "error");
          } catch {
            setState("error");
          }
        }}
        className="inline-flex h-11 items-center gap-2 rounded-full border-[1.5px] border-ink px-4 text-[14.5px] font-bold transition-[background,transform] hover:bg-ink hover:text-bg active:scale-[0.98] disabled:opacity-60"
      >
        {state === "working" ? <Spinner size={16} /> : <IconBell size={18} />}
        Notify me when it&apos;s ready
      </button>
      {state === "denied" && <p className="mt-2 text-[13px] text-muted">Notifications are blocked for Halomark. Turn them on in your phone&apos;s Settings, then try again.</p>}
      {state === "error" && <p className="mt-2 text-[13px] text-danger">Couldn&apos;t turn on notifications. Try again in a moment.</p>}
    </div>
  );
}
