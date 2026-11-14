// Light / dark / follow the system. The choice is a preference kept on this device (localStorage), so
// "Delete all my data" clears it. globals.css does the colours: `data-theme` on <html> overrides the
// system setting either way. THEME_SCRIPT runs in <head> before the page paints, so there's no flash.

export type Theme = "system" | "light" | "dark";
export const THEME_KEY = "screener.theme";
const EVENT = "screener:theme";
/** The browser-chrome colour (iOS status bar, Android toolbar) for each theme: the page background. */
const CHROME = { light: "#eeeeea", dark: "#0b0c0c" } as const;

export function loadTheme(): Theme {
  try {
    const t = window.localStorage.getItem(THEME_KEY);
    return t === "light" || t === "dark" ? t : "system";
  } catch {
    return "system";
  }
}

export function applyTheme(t: Theme) {
  const el = document.documentElement;
  if (t === "system") delete el.dataset.theme;
  else el.dataset.theme = t;
  // Next renders one theme-color tag per system scheme; point both at the chosen theme (or back to their own).
  document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]').forEach((m) => {
    const own = (m.getAttribute("media") ?? "").includes("dark") ? "dark" : "light";
    m.content = CHROME[t === "system" ? own : t];
  });
}

export function saveTheme(t: Theme) {
  try {
    if (t === "system") window.localStorage.removeItem(THEME_KEY);
    else window.localStorage.setItem(THEME_KEY, t);
  } catch {
    // storage blocked: the choice lasts until the page reloads
  }
  applyTheme(t);
  window.dispatchEvent(new Event(EVENT));
}

export function onThemeChange(listener: () => void): () => void {
  window.addEventListener(EVENT, listener);
  return () => window.removeEventListener(EVENT, listener);
}

/** Inline in <head>: set data-theme from the saved choice before first paint. Keep the key in step with THEME_KEY. */
export const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_KEY}");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}})();`;
