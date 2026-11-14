import type { MetadataRoute } from "next";

// Installable app: "Add to Home Screen" opens it full-screen with its own icon.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Screener: founder screening for angels",
    short_name: "Screener",
    description: "Screen a founder in a minute: public research, a calibrated verdict, and the reasons behind it.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#eeeeea",
    theme_color: "#eeeeea",
    // Android: once installed, Screener appears in the share menu; a shared link opens /share.
    share_target: { action: "/share", method: "GET", params: { title: "title", text: "text", url: "url" } },
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
