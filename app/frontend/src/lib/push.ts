// Push notifications: "tell me when it's ready". The browser subscribes with the server's public key,
// and the backend sends one notification when the screening or batch finishes. iPhones allow web push
// only for apps added to the Home Screen.

import { api } from "./api";
import type { Policy } from "./policy";
import { SCHEMA_VERSION } from "./types";

export type PushSupport = "yes" | "install" | "no";

export function pushSupport(): PushSupport {
  if (typeof window === "undefined") return "no";
  if ("serviceWorker" in navigator && "PushManager" in window && "Notification" in window) return "yes";
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const standalone = window.matchMedia("(display-mode: standalone)").matches || (navigator as { standalone?: boolean }).standalone === true;
  return ios && !standalone ? "install" : "no";
}

export function registerServiceWorker() {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
  navigator.serviceWorker.register("/sw.js").catch(() => {
    // no service worker (private mode, an old browser): the app works, just without notifications
  });
}

function keyBytes(b64url: string): Uint8Array<ArrayBuffer> {
  const pad = "=".repeat((4 - (b64url.length % 4)) % 4);
  const raw = atob((b64url + pad).replace(/-/g, "+").replace(/_/g, "/"));
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

function sameKey(a: ArrayBuffer | null | undefined, b: Uint8Array): boolean {
  if (!a) return false;
  const x = new Uint8Array(a);
  return x.length === b.length && x.every((v, i) => v === b[i]);
}

export type NotifyResult = "watching" | "sent" | "failed" | "denied";

/** Ask permission (must run straight from a tap), subscribe, and register for one notification. */
export async function notifyWhenDone(kind: "screening" | "batch", id: string, bar: Policy): Promise<NotifyResult> {
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return "denied";
  const reg = await navigator.serviceWorker.register("/sw.js");
  await navigator.serviceWorker.ready;
  const { public_key } = await api.pushKey();
  const key = keyBytes(public_key);
  let sub = await reg.pushManager.getSubscription();
  // The server makes a new key when it restarts; an old subscription can't be used with the new key.
  if (sub && !sameKey(sub.options.applicationServerKey, key)) {
    await sub.unsubscribe();
    sub = null;
  }
  sub ??= await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: key });
  const res = await api.notifyWhenDone(kind, id, { schema_version: SCHEMA_VERSION, subscription: sub.toJSON(), policy: bar });
  return res.status;
}
