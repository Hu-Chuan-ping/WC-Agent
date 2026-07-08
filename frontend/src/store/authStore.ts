import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface User {
  user_id: string;
  username: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  /** 登录/注册成功后写入，持久化到 localStorage。 */
  setAuth: (token: string, user: User) => void;
  logout: () => void;
}

/**
 * 全局登录态。用 zustand + persist：刷新页面不掉登录，
 * 任何组件用 useAuthStore((s) => s.xxx) 订阅，值变了自动重渲染。
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: "wc-auth" } // localStorage 的 key
  )
);
