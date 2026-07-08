import { apiClient } from "./client";

// 与后端 auth 接口一一对应的类型（对齐 backend/app/models/schemas/auth.py）。
export interface Captcha {
  captcha_id: string;
  image: string; // data:image/png;base64,... 可直接放进 <img src>
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
}

export interface RegisterPayload {
  username: string;
  password: string;
  captcha_id: string;
  captcha_text: string;
}

export interface LoginPayload {
  username: string;
  password: string;
  captcha_id: string;
  captcha_text: string;
}

/** 鉴权相关的后端调用集中在这里，页面通过它请求，不直接碰 axios。 */
export const authApi = {
  getCaptcha: () =>
    apiClient.get<Captcha>("/auth/captcha").then((r) => r.data),

  register: (payload: RegisterPayload) =>
    apiClient.post<TokenResponse>("/auth/register", payload).then((r) => r.data),

  login: (payload: LoginPayload) =>
    apiClient.post<TokenResponse>("/auth/login", payload).then((r) => r.data),

  getMe: () =>
    apiClient.get<{ user_id: string }>("/auth/me").then((r) => r.data),
};
