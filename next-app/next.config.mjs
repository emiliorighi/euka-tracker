/** @type {import('next').NextConfig} */
const isPagesExport = process.env.GITHUB_PAGES === "1"
/** When set, dev rewrites /tiles and /data to an external static server. Otherwise public/ symlinks are used. */
const tileProxy = process.env.TILE_PROXY_URL

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  output: isPagesExport ? "export" : "standalone",
  trailingSlash: isPagesExport,
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

if (!isPagesExport && tileProxy) {
  nextConfig.rewrites = async () => [
    {
      source: "/tiles/:path*",
      destination: `${tileProxy}/tiles/:path*`,
    },
    {
      source: "/data/:path*",
      destination: `${tileProxy}/data/:path*`,
    },
    {
      source: "/parquet/:path*",
      destination: `${tileProxy}/parquet/:path*`,
    },
  ]
}

export default nextConfig
