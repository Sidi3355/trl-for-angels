"use client";

// Appearance: follow the system, or always light, or always dark. Saved on this device (lib/theme.ts).
// Two looks: a labelled segmented control (the You page) and three icon buttons (the desktop sidebar).
import { useEffect, useState } from "react";

import { IconMonitor, IconMoon, IconSun } from "@/components/icons";
import { Segmented, cx } from "@/components/ui";
import { loadTheme, onThemeChange, saveTheme, type Theme } from "@/lib/theme";

const OPTIONS = [
  { value: "system", label: "System", icon: IconMonitor },
  { value: "light", label: "Light", icon: IconSun },
  { value: "dark", label: "Dark", icon: IconMoon },
] as const;

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const [theme, setTheme] = useState<Theme>("system");
  useEffect(() => {
    const sync = () => setTheme(loadTheme());
    sync();
    return onThemeChange(sync);
  }, []);

  if (!compact)
    return <Segmented label="Appearance" value={theme} onChange={(t) => saveTheme(t)} options={OPTIONS.map(({ value, label }) => ({ value, label }))} />;

  return (
    <div role="radiogroup" aria-label="Appearance" className="inline-flex gap-0.5 rounded-full bg-surface-2 p-0.5 ring-1 ring-inset ring-line">
      {OPTIONS.map(({ value, label, icon: Icon }) => {
        const on = theme === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={on}
            aria-label={label}
            title={label}
            onClick={() => saveTheme(value)}
            className={cx("flex h-7 w-7 items-center justify-center rounded-full transition-colors", on ? "bg-ink text-bg" : "text-muted hover:text-ink")}
          >
            <Icon size={15} />
          </button>
        );
      })}
    </div>
  );
}
