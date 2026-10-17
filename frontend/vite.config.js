import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  build: {
    outDir: '../backend/static/dist'
  },
  server: {
    host: 'localhost',
    port: 5173,
    proxy: {
      // 精确匹配 /ai 接口，避免代理 /ai-assistant 路由（Vite 代理默认前缀匹配）
      '^/ai($|/)': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/kb': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/folder': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/file': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/stats': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/settings': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/user': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})