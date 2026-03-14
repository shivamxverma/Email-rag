import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/start_session': 'http://localhost:8000',
      '/ask': 'http://localhost:8000',
    },
  },
})
