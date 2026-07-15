import path from "node:path"
import { fileURLToPath } from "node:url"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "../app/static/react",
    emptyOutDir: false,
    rollupOptions: {
      input: path.resolve(__dirname, "src/nav-main.tsx"),
      output: {
        entryFileNames: "nav.js",
        assetFileNames: (assetInfo) =>
          assetInfo.name?.endsWith(".css") ? "src.[ext]" : "nav.[ext]",
      },
    },
  },
})
