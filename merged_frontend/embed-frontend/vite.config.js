import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import path from 'path'

export default defineConfig({
  plugins: [svelte()],
  base: './',  // Use relative paths for assets
  resolve: {
    alias: {
      '@shared': path.resolve(__dirname, '../shared-components')
    },
    // Help Vite find dependencies for shared components
    preserveSymlinks: false
  },
  optimizeDeps: {
    include: ['svelte-spa-router', 'i18n-js']
  },
  build: {
    commonjsOptions: {
      include: [/node_modules/, /shared-components/]
    },
    rollupOptions: {
      // Don't externalize these dependencies
      external: []
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