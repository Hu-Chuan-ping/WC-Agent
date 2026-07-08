import axios from "axios";
import { useAuthStore } from "../store/authStore";

/**
 * 全局 axios 实例。所有后端请求都走它，统一处理两件横切事务：
 *  1) 请求拦截：自动带上登录令牌（Authorization 头）。
 *  2) 响应拦截：401 自动登出并回登录页；把后端 {code,message} 错误转成可读 Error。
 */
export const apiClient = axios.create({
  baseURL: "/api/v1", // 经 vite 代理转发到后端
  timeout: 30000,
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    // 后端业务异常统一是 {code, message}，抽出 message 给上层展示
    const message =
      error.response?.data?.message || error.message || "请求失败，请稍后重试";
    return Promise.reject(new Error(message));
  }
);
