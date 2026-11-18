import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    // En développement, l'API tourne à part sur le port 3000.
    proxy: { '/api': 'http://localhost:3000' },
  },
});
