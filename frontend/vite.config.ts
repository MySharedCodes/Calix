import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  root: 'frontend',
  plugins: [react()],
  clearScreen: false,
  build: { target: 'es2022', outDir: 'dist', chunkSizeWarningLimit: 4200 },
  server: { proxy: { '/api': process.env.CALIX_BACKEND_URL || 'http://127.0.0.1:8765' } },
});
