import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The browser calls /v1 on the Vite origin and Vite forwards it, so the API needs no CORS.
// Port 8080 is either local uvicorn or `gcloud run services proxy`, which adds the identity token.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/v1": { target: "http://localhost:8080", changeOrigin: true },
    },
  },
});
