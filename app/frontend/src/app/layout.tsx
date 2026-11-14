import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { PasscodeGate } from "@/components/PasscodeGate";
import "./globals.css";

export const metadata: Metadata = {
  title: "Founder Screener",
  description: "Research a founder and get a calibrated advance, escalate or pass verdict. A screening aid, not investment advice.",
  appleWebApp: { capable: true, title: "Screener", statusBarStyle: "default" },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f2f2f7" },
    { media: "(prefers-color-scheme: dark)", color: "#000000" },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
        <PasscodeGate />
      </body>
    </html>
  );
}
