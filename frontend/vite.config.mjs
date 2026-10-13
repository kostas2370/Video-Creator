import { defineConfig, loadEnv, transformWithOxc } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), ["VITE_", "REACT_APP_"]);
  return {
    plugins: [
      {
        name: "app-jsx-in-js",
        enforce: "pre",
        async transform(code, id) {
          if (!/\/src\/.*\.js$/.test(id)) return;
          return transformWithOxc(code, id, { lang: "jsx", jsx: { runtime: "automatic" } });
        },
      },
      react(),
      tailwindcss(),
    ],
    define: {
      "process.env.REACT_APP_API_HOST": JSON.stringify(env.REACT_APP_API_HOST || ""),
    },
    optimizeDeps: { rolldownOptions: { moduleTypes: { ".js": "jsx" } } },
    build: { outDir: "build", assetsDir: "static", target: "es2020" },
    server: {
      port: 3000,
      strictPort: true,
      proxy: Object.fromEntries(
        ["/api", "/admin", "/swagger", "/redoc", "/media"].map(path => [
          path, { target: "http://localhost:8000", changeOrigin: false },
        ]),
      ),
    },
    test: { environment: "node" },
  };
});
