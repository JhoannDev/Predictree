import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Puerto fijo: debe coincidir con CORS_ORIGINS del backend.
    port: 5173,
    strictPort: true,
  },
});
