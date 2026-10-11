import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// In development the console runs on Vite and proxies the same paths the
// production build shares with the API, so no CORS configuration is needed.
const TARGET = 'http://127.0.0.1:8090'
const PROXY_PATHS = ['/health', '/healthz', '/diagnostics', '/control']

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      PROXY_PATHS.map((path) => [path, { target: TARGET, changeOrigin: true }]),
    ),
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
