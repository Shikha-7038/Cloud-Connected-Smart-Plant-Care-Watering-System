import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Backend URL comes from VITE_API_URL (see .env.example) so the same build
// can point at localhost during development and at the deployed API in production.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
