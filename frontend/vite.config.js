import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path'
import { createRequire } from 'module'
const require = createRequire(import.meta.url)
const proxyOptions = require('./proxyOptions.cjs')

export default defineConfig({
  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
  },
  plugins: [react(), tailwindcss()],
  server: {
    port: 8081,
    host: '0.0.0.0',
    proxy: proxyOptions,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  esbuild: {
    drop: ['debugger'],
  },
  build: {
    outDir: resolve(__dirname, '../e2next_ai/public/dist'),
    emptyOutDir: true,
    target: 'es2019',
    sourcemap: false,
    cssCodeSplit: false,
    lib: {
      entry: resolve(__dirname, 'src/main.jsx'),
      name: 'E2NextChatbot',
      formats: ['iife'],
      fileName: () => 'e2next-chatbot.js',
    },
    rollupOptions: {
      output: {
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith('.css')) {
            return 'e2next-chatbot.css'
          }
          return '[name][extname]'
        },
      },
    },
  },
})
