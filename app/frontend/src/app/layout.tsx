import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { AppStateProvider } from "@/components/AppState";
import { PasscodeGate } from "@/components/PasscodeGate";
import "./globals.css";

// Self-hosted at build time by next/font: no request to Google from the user's phone.
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const grotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-grotesk", display: "swap", weight: ["500", "600", "700"] });

export const metadata: Metadata = {
  title: { default: "Screener", template: "%s · Screener" },
  description: "Screen a founder in a minute: public research, a calibrated advance, escalate or pass, and the reasons behind it. A screening aid, not investment advice.",
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
    { media: "(prefers-color-scheme: light)", color: "#f4f5f8" },
    { media: "(prefers-color-scheme: dark)", color: "#090b10" },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${grotesk.variable}`}>
      <body>
        <AppStateProvider>
          <AppShell>{children}</AppShell>
          <PasscodeGate />
        </AppStateProvider>
      </body>
    </html>
  );
}
