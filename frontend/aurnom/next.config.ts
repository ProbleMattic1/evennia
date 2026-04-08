import type { NextConfig } from "next";
import path from "node:path";

// Browsers load the app via Caddy on :8080; dev HMR checks Origin host against this list.
// Set NEXT_ALLOWED_DEV_ORIGINS (comma-separated, no scheme), e.g. 192.168.1.10,myhost.local
const fromEnv =
  process.env.NEXT_ALLOWED_DEV_ORIGINS?.split(",")
    .map((s) => s.trim())
    .filter(Boolean) ?? [];

const nextConfig: NextConfig = {
  // `next build` emits a minimal Node server for Docker (see frontend/aurnom/Dockerfile).
  output: "standalone",
  // Parent `frontend/package-lock.json` otherwise nests standalone under `aurnom/`.
  // `npm run build` / Docker WORKDIR must be this app root (`frontend/aurnom`).
  outputFileTracingRoot: path.resolve(process.cwd()),
  ...(process.env.NODE_ENV !== "production"
    ? {
        allowedDevOrigins: ["127.0.0.1", "localhost", ...fromEnv],
      }
    : {}),
};

export default nextConfig;
