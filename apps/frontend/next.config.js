/** @type {import('next').NextConfig} */
const apiProxyTarget = process.env.API_BASE_URL || "http://127.0.0.1:8000";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/backend-api/health",
        destination: `${apiProxyTarget}/health`,
      },
      {
        source: "/backend-api/api/:path*",
        destination: `${apiProxyTarget}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
