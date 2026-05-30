import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  optimizeDeps: {
    include: ['spessasynth_lib', 'spessasynth_core'],
  },
  server: {
    proxy: {
      '/generate': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/productions': 'http://localhost:8000',
      '/benchmark-prompts': 'http://localhost:8000',
    }
  }
})
