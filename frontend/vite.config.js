import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backendTarget = process.env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:5000'
const port = Number(process.env.FRONTEND_PORT) || 5173
const allowedHosts = (process.env.VITE_ALLOWED_HOSTS || 'localhost,127.0.0.1')
  .split(',').map((h) => h.trim()).filter(Boolean)

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port,
    allowedHosts,
    proxy: { '/health': backendTarget, '/api': backendTarget },
  },
})
