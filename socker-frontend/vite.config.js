import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    // 显式绑定 127.0.0.1：Node 17+ 下 'localhost' 可能只解析到 IPv6 的 ::1，
    // 导致用 http://127.0.0.1:5173 访问时连接被拒
    host: '127.0.0.1',
    port: 5173,
    open: true,
    proxy: {
      // 前端请求 /api 开头的地址时，自动转发到 Spring Boot 网关
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
    },
  },

  build: {
    // ECharts / Element Plus 本体较大，按库手动分包，避免首屏一次性下载
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: 'echarts', test: /node_modules[\\/]echarts/ },
            { name: 'element-plus', test: /node_modules[\\/]element-plus/ },
            { name: 'vue-vendor', test: /node_modules[\\/](vue|vue-router|@vue)[\\/]/ },
          ],
        },
      },
    },
    // 分包后单文件仍可能超过默认 500 kB 阈值，这里放宽以免噪音警告
    chunkSizeWarningLimit: 1200,
  },
})
