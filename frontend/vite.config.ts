import { fileURLToPath, URL } from "node:url"
import { defineConfig, loadEnv } from "vite"
import vue from "@vitejs/plugin-vue"

export default defineConfig(({ mode }) => {
  // LAN_DEV_ORIGIN (set via frontend/.env.local) lets the dashboard be reached from another device on the same network during development.
  const env = loadEnv(mode, process.cwd(), "")

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    server: {
      host: true,
      port: 3000,
      allowedHosts: env.LAN_DEV_ORIGIN ? [env.LAN_DEV_ORIGIN] : undefined,
      // Windows bind-mounts into the container don't propagate inotify events, so the default
      // watcher silently never sees file changes — polling is required for HMR to work at all.
      watch: {
        usePolling: true,
        interval: 300,
      },
      proxy: {
        // Targets the container_name, not the bare "backend" service alias — shared-infra is a
        // Docker network shared across multiple personal projects, and another project's service
        // is also named "backend", so the short alias round-robins between the two containers.
        "/api/v1": {
          target: "http://atlas-backend:8000",
          changeOrigin: true,
        },
      },
    },
  }
})
