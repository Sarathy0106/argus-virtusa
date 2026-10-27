import type { Metadata } from "next";
import "../styles/globals.css";
import { Providers } from "./providers";

// Fonts are declared as CSS stacks in styles/tokens.css to keep the build fully
// offline-safe (no build-time Google Fonts fetch). R6 polish can swap in
// self-hosted font files via next/font/local.

export const metadata: Metadata = {
  title: "ARGUS v2 — Regulatory Mission Control",
  description: "Circular in, safe rule out. Every number is computed live.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg text-text antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
