import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Ensure built asset paths are relative when loaded via file:// in Electron
  base: './',
  server: {
    port: 5173,
    strictPort: true,
  },
})
