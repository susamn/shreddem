import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Support dynamic port overrides for dev environment
const backendPort = process.env.BACKEND_PORT || 17811;
const frontendPort = process.env.FRONTEND_PORT || 18710;

export default defineConfig({
  plugins: [vue()],
  server: {
    port: parseInt(frontendPort),
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
    },
  },
})
