import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      { source: "/api/search/:path*", destination: "http://cortana-search:8080/api/:path*" },
    ];
  },
};

export default nextConfig;
