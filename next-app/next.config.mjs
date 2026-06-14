/** @type {import('next').NextConfig} */
const tileProxy = process.env.TILE_PROXY_URL ?? "http://127.0.0.1:8080"

const nextConfig = {
  reactStrictMode: false,
  output: "standalone",
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: "/tiles/:path*",
        destination: `${tileProxy}/tiles/:path*`,
      },
      {
        source: "/parquet/:path*",
        destination: `${tileProxy}/parquet/:path*`,
      },
      {
        source: "/staged/:path*",
        destination: `${tileProxy}/staged/:path*`,
      },
    ]
  },
}

export default nextConfig
