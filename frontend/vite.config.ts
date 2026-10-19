/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// ADR-0009: no CORS anywhere. In dev the Vite server proxies /api to the
// FastAPI backend — the browser sees a single origin (localhost:5173).
// In prod FastAPI serves the built SPA itself (also a single origin).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
  },
});
