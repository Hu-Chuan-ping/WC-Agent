import { apiClient } from "./client";
import { useAuthStore } from "../store/authStore";

// 与后端会话接口一一对应（backend/app/api/v1/chat.py）。全部 POST。
export interface SessionItem {
  session_id: string;
  title: string;
  last_message: string | null;
  updated_at: string;
}

export interface MessageItem {
  role: string;
  content: string;
  created_at: string;
}

export const conversationApi = {
  create: () =>
    apiClient.post<{ session_id: string; title: string }>("/sessions/create").then((r) => r.data),

  list: () => apiClient.post<SessionItem[]>("/sessions/list").then((r) => r.data),

  messages: (session_id: string) =>
    apiClient.post<MessageItem[]>("/sessions/messages", { session_id }).then((r) => r.data),

  rename: (session_id: string, title: string) =>
    apiClient.post("/sessions/rename", { session_id, title }).then((r) => r.data),

  remove: (session_id: string) =>
    apiClient.post("/sessions/delete", { session_id }).then((r) => r.data),
};

export interface StreamHandlers {
  onStatus: (text: string) => void; // 进度事件（正在检索…）
  onToken: (text: string) => void; // 正文逐段
  onDone: (session_id: string) => void; // 完成，带后端确定的 session_id
}

/**
 * 流式发消息（SSE）。用 fetch 读取 ReadableStream，逐条解析 `data:{...}` 事件。
 * 注意：fetch 不走 axios 拦截器，所以这里手动处理 401。
 */
export async function streamDispatch(
  question: string,
  session_id: string | null,
  handlers: StreamHandlers
): Promise<void> {
  const token = useAuthStore.getState().token;
  const res = await fetch("/api/v1/dispatch/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question, session_id }),
  });

  if (res.status === 401) {
    useAuthStore.getState().logout();
    if (window.location.pathname !== "/login") window.location.href = "/login";
    throw new Error("登录已过期，请重新登录");
  }
  if (!res.ok || !res.body) {
    throw new Error(`请求失败（${res.status}）`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n"); // SSE 事件以空行分隔
    buffer = parts.pop() ?? ""; // 最后一段可能不完整，留到下次
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      let ev: { type: string; text?: string; session_id?: string };
      try {
        ev = JSON.parse(payload);
      } catch {
        continue;
      }
      if (ev.type === "status" && ev.text) handlers.onStatus(ev.text);
      else if (ev.type === "token" && ev.text) handlers.onToken(ev.text);
      else if (ev.type === "done" && ev.session_id) handlers.onDone(ev.session_id);
    }
  }
}
