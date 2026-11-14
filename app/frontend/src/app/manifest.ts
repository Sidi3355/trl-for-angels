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
    background_color: "#f4f5f8",
    theme_color: "#f4f5f8",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
