import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: "index.html",
        login: "login/index.html",
        securityKey: "login/securityKey.html",
        register: "register/index.html",
        forgot: "forgot/index.html",
        terms: "terms/index.html",
        gdpr: "gdpr/index.html",
        app: "app/index.html",
      },
    },
  },
});
