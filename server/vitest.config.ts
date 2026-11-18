import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Les tests d'intégration partagent un serveur MariaDB : on les exécute en série.
    fileParallelism: false,
    testTimeout: 20000,
    hookTimeout: 60000,
  },
});
