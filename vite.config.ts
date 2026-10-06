import { resolve } from "node:path";

import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

const src = (path: string) => resolve(import.meta.dirname, "frontend/src", path);

// Assets are built into a static directory with stable names, then served by
// Django's staticfiles like any other file: ManifestStaticFilesStorage adds the
// content hash in production, so no manifest integration is needed.
export default defineConfig(({ mode }) => ({
  plugins: [tailwindcss()],
  // Relative URLs: assets resolve next to the bundle wherever STATIC_URL points.
  base: "./",
  publicDir: false,
  build: {
    outDir: resolve(import.meta.dirname, "urban_platform/static/dist"),
    emptyOutDir: true,
    sourcemap: mode === "development",
    minify: mode !== "development",
    rollupOptions: {
      input: {
        main: src("main.ts"),
        styles: src("styles/main.css"),
        map: src("styles/map.css"),
        vote: src("pages/vote.ts"),
        ideas: src("pages/ideas.ts"),
        "code-of-conduct": src("pages/code-of-conduct.ts"),
        admin: src("admin/main.ts"),
        "admin-vote-stats": src("admin/vote-stats.ts"),
        "admin-location": src("admin/location-input.ts"),
        "projects-map": src("pages/projects-map.ts"),
        "project-location": src("pages/project-location.ts"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: (asset) =>
          asset.names.some((name) => name.endsWith(".css")) ? "[name][extname]" : "assets/[name]-[hash][extname]",
      },
    },
  },
}));
