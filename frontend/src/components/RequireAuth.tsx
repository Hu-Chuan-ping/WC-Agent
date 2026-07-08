import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

/**
 * 路由守卫：未登录（无 token）访问受保护页面时，重定向到登录页。
 * 用法：<RequireAuth><AppLayout /></RequireAuth>
 */
export default function RequireAuth({ children }: { children: ReactNode }) {
  const token = useAuthStore((s) => s.token);
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <>{children}</>;
}
