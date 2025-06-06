import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import path from 'path-browserify'

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
    port: 5173,
    proxy: {
      '/api': {
        //        target: 'http://localhost:8000',
        target: 'https://iiyi5tvfpv6ezql6s3tyyuzcea0xsbdp.lambda-url.us-east-1.on.aws/api',
        changeOrigin: true
      }
    }
  }
})
