import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import path from "path"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/pending": "http://localhost:8000",
      "/approve": "http://localhost:8000",
      "/reject": "http://localhost:8000",
      "/status": "http://localhost:8000",
      "/strategy": "http://localhost:8000",
      "/dispatch": "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/chat/stream": "http://localhost:8000",
      "/chat": "http://localhost:8000",
      "/conversations": "http://localhost:8000",
    },
  },
})
