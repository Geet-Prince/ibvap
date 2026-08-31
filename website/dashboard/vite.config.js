import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// IBVAP backend (FastAPI) runs on :8000 and serves /api, /storage, /stream, /ws.
// The dev proxy keeps the frontend on same-origin paths so no hardcoded host
// is needed and WebSockets work transparently.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/storage': 'http://localhost:8000',
      '/stream': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
