import { create } from "zustand";
import {
  conversationApi,
  streamDispatch,
  type ExpertTake,
  type SessionItem,
} from "../api/conversation";

export interface ChatMessage {
  role: string;
  content: string;
  experts?: ExpertTake[]; // 圆桌专家意见（预测消息才有）
  created_at?: string; // 消息时间（历史来自后端，直播用本地时间）
}

interface ConversationState {
  sessions: SessionItem[];
  activeId: string | null;
  messages: ChatMessage[];
  loadingMessages: boolean;
  sending: boolean;
  streamingStatus: string; // 当前进度（正在检索…），完成后清空
  statusTrail: string[]; // 本轮所有进度事件，供“分析过程”折叠展示

  loadSessions: () => Promise<void>;
  newConversation: () => void;
  selectSession: (id: string) => Promise<void>;
  sendMessage: (question: string) => Promise<void>;
  renameSession: (id: string, title: string) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  reset: () => void;
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  sessions: [],
  activeId: null,
  messages: [],
  loadingMessages: false,
  sending: false,
  streamingStatus: "",
  statusTrail: [],

  loadSessions: async () => {
    set({ sessions: await conversationApi.list() });
  },

  newConversation: () => set({ activeId: null, messages: [], statusTrail: [] }),

  selectSession: async (id) => {
    set({ activeId: id, loadingMessages: true, messages: [], statusTrail: [] });
    try {
      const msgs = await conversationApi.messages(id);
      set({
        messages: msgs.map((m) => ({
          role: m.role,
          content: m.content,
          experts: m.meta?.experts, // 历史消息里的专家会诊
          created_at: m.created_at,
        })),
      });
    } finally {
      set({ loadingMessages: false });
    }
  },

  sendMessage: async (question) => {
    // 追加用户气泡 + 一个待填充的空助手气泡
    const now = new Date().toISOString();
    set((s) => ({
      messages: [
        ...s.messages,
        { role: "user", content: question, created_at: now },
        { role: "assistant", content: "", created_at: now },
      ],
      sending: true,
      streamingStatus: "",
      statusTrail: [],
    }));
    try {
      await streamDispatch(question, get().activeId, {
        onStatus: (text) =>
          set((s) => ({ streamingStatus: text, statusTrail: [...s.statusTrail, text] })),
        onToken: (text) =>
          set((s) => {
            const msgs = s.messages.slice();
            const last = msgs[msgs.length - 1];
            msgs[msgs.length - 1] = { ...last, content: last.content + text };
            return { messages: msgs };
          }),
        onExpert: (e) =>
          set((s) => {
            const msgs = s.messages.slice();
            const last = msgs[msgs.length - 1];
            msgs[msgs.length - 1] = { ...last, experts: [...(last.experts ?? []), e] };
            return { messages: msgs };
          }),
        onDone: (session_id) => set({ activeId: session_id }),
      });
      set({ sending: false, streamingStatus: "" });
      await get().loadSessions(); // 刷新左侧标题/排序
    } catch (e) {
      set({ sending: false, streamingStatus: "" });
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

  reset: () => set({ sessions: [], activeId: null, messages: [], statusTrail: [], streamingStatus: "" }),
}));
