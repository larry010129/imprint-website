import type { NextConfig } from "next";

/**
 * Next owns HTML/SSR; FastAPI stays JSON + static SoT.
 * Rewrites proxy browser calls same-origin when Next is the edge.
 * Server Components prefer API_INTERNAL_BASE (direct to FastAPI).
 */
function normalizeApiBase(raw: string | undefined, fallback: string): string {
  const value = (raw || fallback).replace(/\/$/, "");
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  return `https://${value}`;
}

const apiProxy = normalizeApiBase(
  process.env.API_PROXY_TARGET,
  "http://127.0.0.1:8080",
);

const nextConfig: NextConfig = {
  // Jewelry/shop registry paths use trailing slashes; Next serves without.
  // Default redirect /path/ → /path is acceptable cutover debt for App Router.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiProxy}/api/:path*` },
      { source: "/static/:path*", destination: `${apiProxy}/static/:path*` },
      { source: "/js/:path*", destination: `${apiProxy}/js/:path*` },
      { source: "/css/:path*", destination: `${apiProxy}/css/:path*` },
      { source: "/favicon.svg", destination: `${apiProxy}/favicon.svg` },
      { source: "/robots.txt", destination: `${apiProxy}/robots.txt` },
      { source: "/sitemap.xml", destination: `${apiProxy}/sitemap.xml` },
      { source: "/admin.html", destination: `${apiProxy}/admin.html` },
    ];
  },
};

export default nextConfig;
