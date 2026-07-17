import path from "node:path";
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "../public/react",
    emptyOutDir: false,
    rollupOptions: {
      input: path.resolve(__dirname, "src/stories-main.tsx"),
      output: {
        entryFileNames: "stories.js",
        assetFileNames: "stories.[ext]",
      },
    },
  },
});
