import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Dev server proxies `/api/*` to the FastAPI backend.
 * Default matches common local runs; override with VITE_API_PROXY_TARGET in frontend/.env
 * (e.g. VITE_API_PROXY_TARGET=http://127.0.0.1:8000).
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget =
    env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8004";

  return {
    plugins: [react()],
    server: {
      port: 3000,
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
