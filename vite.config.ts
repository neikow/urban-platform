import { resolve } from "node:path";

import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

import fontCatalog from "./frontend/theme/fonts.json" with { type: "json" };

const src = (path: string) => resolve(import.meta.dirname, "frontend/src", path);
// One stylesheet per font, linked only by the websites using it: dist/font-<id>.css
// (not in a subdirectory, where its relative font URLs would break).
const fonts = Object.fromEntries(
  Object.keys(fontCatalog.fonts).map((id) => [
    `font-${id}`,
    resolve(import.meta.dirname, "frontend/theme/fonts", `${id}.css`),
  ]),
);

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
        "admin-tasks": src("admin/tasks.ts"),
        "address-input": src("address-input.ts"),
        "address-autocomplete": src("lib/address-autocomplete.css"),
        "projects-map": src("pages/projects-map.ts"),
        "project-location": src("pages/project-location.ts"),
        "event-interest": src("pages/event-interest.ts"),
        ...fonts,
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
