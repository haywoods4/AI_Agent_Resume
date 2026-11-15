import { defineConfig } from "vite";
export default defineConfig({
  server: {
    allowedHosts: process.env.CODESPACE_NAME
      ? [`${process.env.CODESPACE_NAME}-5173.app.github.dev`] : [],
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
