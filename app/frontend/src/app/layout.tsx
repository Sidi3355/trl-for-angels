import type { Metadata, Viewport } from "next";
import { Archivo } from "next/font/google";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { AppStateProvider } from "@/components/AppState";
import { PasscodeGate } from "@/components/PasscodeGate";
import "./globals.css";

// Self-hosted at build time by next/font: no request to Google from the user's phone.
// One variable family; its width axis gives the condensed figures and the wide labels.
const archivo = Archivo({ subsets: ["latin"], axes: ["wdth"], variable: "--font-archivo", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Screener", template: "%s · Screener" },
  description: "Screen a founder in a minute: public research, a calibrated meet, look closer or pass, and the reasons behind it. A screening aid, not investment advice.",
  applicationName: "Screener",
  appleWebApp: { capable: true, title: "Screener", statusBarStyle: "default" },
  formatDetection: { telephone: false },
  icons: {
    icon: [{ url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#eeeeea" },
    { media: "(prefers-color-scheme: dark)", color: "#0b0c0c" },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={archivo.variable}>
      <body>
        <AppStateProvider>
          <AppShell>{children}</AppShell>
          <PasscodeGate />
        </AppStateProvider>
      </body>
    </html>
  );
}
