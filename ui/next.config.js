import path from "node:path"
import { fileURLToPath } from "node:url"

const uiRoot = path.dirname(fileURLToPath(import.meta.url))
const backendUrl = (process.env.SWARMMIND_API_URL ?? "http://localhost:8000").replace(/\/+$/, "")

const backendProxySources = [
  "/api/chat/:path*",
  "/status/:path*",
  "/health/:path*",
  "/ready/:path*",
  "/models/:path*",
  "/runtime/:path*",
  "/chat/:path*",
  "/conversations/:path*",
  "/projects/:path*",
  "/auth/:path*",
  "/llm-providers/:path*",
  "/gateway/:path*",
  "/users/:path*",
  "/organizations/:path*",
  "/teams/:path*",
  "/admin/:path*",
]

/** @type {import("next").NextConfig} */
const nextConfig = {
  devIndicators: false,
  allowedDevOrigins: ["127.0.0.1"],
  turbopack: {
    root: uiRoot,
  },
  async rewrites() {
    return backendProxySources.map((source) => ({
      source,
      destination: `${backendUrl}${source}`,
    }))
  },
}

export default nextConfig
