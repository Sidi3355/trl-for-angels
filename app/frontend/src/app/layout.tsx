import type { Metadata, Viewport } from "next";
import { Archivo } from "next/font/google";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { AppStateProvider } from "@/components/AppState";
import { PasscodeGate } from "@/components/PasscodeGate";
import { THEME_SCRIPT } from "@/lib/theme";
import "./globals.css";

// Self-hosted at build time by next/font: no request to Google from the user's phone.
// One variable family; its width axis gives the condensed figures and the wide labels.
const archivo = Archivo({ subsets: ["latin"], axes: ["wdth"], variable: "--font-archivo", display: "swap" });

// Where the app is served, so the link-preview image gets an absolute address. Vercel sets the second one itself.
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || (process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : "http://localhost:3000");

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "Halomark", template: "%s · Halomark" },
  description: "Screen a founder in a minute: public research, a calibrated meet, look closer or pass, and the reasons behind it. A screening aid, not investment advice.",
  applicationName: "Halomark",
  appleWebApp: { capable: true, title: "Halomark", statusBarStyle: "default" },
  formatDetection: { telephone: false },
  icons: {
    icon: [
      { url: "/icons/icon.svg", type: "image/svg+xml" },
      { url: "/icons/favicon-64.png", sizes: "64x64", type: "image/png" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
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
    // data-theme (light or dark) is set before first paint by THEME_SCRIPT when the person chose one in the app;
    // without it the system setting decides. suppressHydrationWarning: the script changes <html> before React.
    <html lang="en" className={archivo.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <AppStateProvider>
          <AppShell>{children}</AppShell>
          <PasscodeGate />
        </AppStateProvider>
      </body>
    </html>
  );
}
