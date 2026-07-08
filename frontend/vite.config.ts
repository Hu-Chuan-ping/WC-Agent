import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 开发服务器把 /api 代理到后端（uvicorn 默认 8000 端口），前端不必处理跨域。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
