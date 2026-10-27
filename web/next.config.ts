import type { NextConfig } from "next";

const API_BASE = process.env.ARGUS_API_BASE ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Proxy API + SSE calls to the FastAPI gateway so the browser talks same-origin
  // in dev and no pipeline logic ever runs in the frontend.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_BASE}/api/:path*` },
      { source: "/health", destination: `${API_BASE}/health` },
    ];
  },
};

export default nextConfig;
