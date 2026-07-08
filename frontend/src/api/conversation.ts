import { apiClient } from "./client";

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

export interface DispatchResponse {
  result: string;
  session_id: string;
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

  dispatch: (question: string, session_id: string | null) =>
    apiClient
      .post<DispatchResponse>("/dispatch", { question, session_id })
      .then((r) => r.data),
};
