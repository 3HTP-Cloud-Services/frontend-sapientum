import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import path from 'path'

export default defineConfig({
  plugins: [svelte()],
  base: './',  // Use relative paths for assets
  resolve: {
    alias: {
      '@shared': path.resolve(__dirname, 'src/shared')
    }
  },
  optimizeDeps: {
    include: ['i18n-js']
  },
  build: {
    commonjsOptions: {
      include: [/node_modules/, /shared-components/]
    },
    rollupOptions: {
      external: ['i18n-js']
    }
  },
  server: {
    port: 5573, // Use port 5573 instead of default 5173
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})