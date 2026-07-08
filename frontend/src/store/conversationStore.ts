import { create } from "zustand";
import { conversationApi, type SessionItem } from "../api/conversation";

export interface ChatMessage {
  role: string;
  content: string;
}

interface ConversationState {
  sessions: SessionItem[];
  activeId: string | null;
  messages: ChatMessage[];
  loadingMessages: boolean;
  sending: boolean;

  loadSessions: () => Promise<void>;
  newConversation: () => void; // 懒创建：清空当前，首次发消息时后端才真正建会话
  selectSession: (id: string) => Promise<void>;
  sendMessage: (question: string) => Promise<void>;
  renameSession: (id: string, title: string) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  reset: () => void; // 退出登录时清空
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  sessions: [],
  activeId: null,
  messages: [],
  loadingMessages: false,
  sending: false,

  loadSessions: async () => {
    set({ sessions: await conversationApi.list() });
  },

  newConversation: () => set({ activeId: null, messages: [] }),

  selectSession: async (id) => {
    set({ activeId: id, loadingMessages: true, messages: [] });
    try {
      const msgs = await conversationApi.messages(id);
      set({ messages: msgs.map((m) => ({ role: m.role, content: m.content })) });
    } finally {
      set({ loadingMessages: false });
    }
  },

  sendMessage: async (question) => {
    // 乐观追加用户气泡
    set((s) => ({
      messages: [...s.messages, { role: "user", content: question }],
      sending: true,
    }));
    try {
      const res = await conversationApi.dispatch(question, get().activeId);
      set((s) => ({
        messages: [...s.messages, { role: "assistant", content: res.result }],
        activeId: res.session_id,
        sending: false,
      }));
      await get().loadSessions(); // 刷新左侧标题/排序（含新会话）
    } catch (e) {
      set({ sending: false });
      throw e;
    }
  },

  renameSession: async (id, title) => {
    await conversationApi.rename(id, title);
    await get().loadSessions();
  },

  deleteSession: async (id) => {
    await conversationApi.remove(id);
    set((s) => ({
      sessions: s.sessions.filter((x) => x.session_id !== id),
      activeId: s.activeId === id ? null : s.activeId,
      messages: s.activeId === id ? [] : s.messages,
    }));
  },

  reset: () => set({ sessions: [], activeId: null, messages: [] }),
}));
