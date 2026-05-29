import { create } from "zustand";
import {
  apiGet,
  apiPost,
  apiPatch,
  apiDelete,
  streamChat,
  getAuthToken,
  setAuthToken as saveToken,
  clearAuthToken as removeToken
} from "../utils/api";

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  model_used?: string;
  provider_used?: string;
  created_at: string;
}

interface ConversationDetailResponse {
  conversation: Conversation;
  messages: Message[];
}

interface User {
  id: string;
  email: string;
  role?: string | null;
}

interface ChatState {
  user: User | null;
  token: string | null;
  conversations: Conversation[];
  currentConversationId: string | null;
  messages: Message[];
  modelType: string;
  isGenerating: boolean;
  abortController: AbortController | null;
  error: string | null;

  // Actions
  initAuth: () => Promise<void>;
  login: (token: string, user: User) => void;
  signup: (token: string, user: User) => void;
  logout: () => Promise<void>;
  setModelType: (type: string) => void;
  
  // Conversation actions
  fetchConversations: () => Promise<void>;
  createConversation: (title?: string) => Promise<string>;
  selectConversation: (id: string | null) => Promise<void>;
  renameConversation: (id: string, title: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  
  // Message actions
  sendMessage: (content: string) => Promise<void>;
  stopGeneration: () => void;
}

const getErrorMessage = (error: unknown) =>
  error instanceof Error && error.message ? error.message : "Something went wrong. Please try again.";

export const useChatStore = create<ChatState>((set, get) => ({
  user: null,
  token: typeof window !== "undefined" ? getAuthToken() : null,
  conversations: [],
  currentConversationId: null,
  messages: [],
  modelType: "default",
  isGenerating: false,
  abortController: null,
  error: null,

  initAuth: async () => {
    const token = getAuthToken();
    if (token) {
      try {
        const user = await apiGet<User>("/auth/me");
        set({ token, user, error: null });
      } catch (err: unknown) {
        console.error("Session restoration failed", err);
        removeToken();
        set({ token: null, user: null });
      }
    }
  },

  login: (token, user) => {
    saveToken(token);
    set({ token, user, error: null });
  },

  signup: (token, user) => {
    saveToken(token);
    set({ token, user, error: null });
  },

  logout: async () => {
    try {
      await apiPost("/auth/logout", {});
    } catch (err: unknown) {
      console.warn("Logout request failed", err);
    } finally {
      removeToken();
      set({
        token: null,
        user: null,
        conversations: [],
        currentConversationId: null,
        messages: [],
        isGenerating: false,
        abortController: null,
        error: null
      });
    }
  },

  setModelType: (modelType) => set({ modelType }),

  fetchConversations: async () => {
    try {
      const list = await apiGet<Conversation[]>("/conversations");
      set({ conversations: list });
    } catch (err: unknown) {
      set({ error: getErrorMessage(err) });
    }
  },

  createConversation: async (title = "New Conversation") => {
    try {
      const conversation = await apiPost<Conversation, { title: string }>("/conversations", { title });
      set((state) => ({
        conversations: [conversation, ...state.conversations],
        currentConversationId: conversation.id,
        messages: [],
        error: null
      }));
      return conversation.id;
    } catch (err: unknown) {
      set({ error: getErrorMessage(err) });
      throw err;
    }
  },

  selectConversation: async (id) => {
    if (!id) {
      set({ currentConversationId: null, messages: [] });
      return;
    }

    try {
      // Clear old messages BEFORE loading new ones to prevent overlap
      set({ currentConversationId: id, messages: [], error: null });
      
      const detail = await apiGet<ConversationDetailResponse>(`/conversations/${id}`);
      
      // Only update if we're still viewing this conversation (prevent race condition)
      const currentId = get().currentConversationId;
      if (currentId === id) {
        set({ messages: detail.messages });
      }
    } catch (err: unknown) {
      set({ error: getErrorMessage(err) });
    }
  },

  renameConversation: async (id, title) => {
    try {
      const updated = await apiPatch<Conversation, { title: string }>(`/conversations/${id}`, { title });
      set((state) => ({
        conversations: state.conversations.map((c) => (c.id === id ? updated : c)),
        error: null
      }));
    } catch (err: unknown) {
      set({ error: getErrorMessage(err) });
    }
  },

  deleteConversation: async (id) => {
    try {
      await apiDelete<null>(`/conversations/${id}`);
      set((state) => {
        const nextConversations = state.conversations.filter((c) => c.id !== id);
        const isActive = state.currentConversationId === id;
        return {
          conversations: nextConversations,
          currentConversationId: isActive ? null : state.currentConversationId,
          messages: isActive ? [] : state.messages,
          error: null
        };
      });
    } catch (err: unknown) {
      set({ error: getErrorMessage(err) });
    }
  },

  sendMessage: async (content) => {
    const { currentConversationId, modelType, isGenerating, abortController: existingController } = get();
    
    // Prevent concurrent requests
    if (isGenerating) {
      console.warn("A message is already being sent. Please wait.");
      return;
    }
    
    if (!content.trim()) return;

    // Cancel previous request if still active
    if (existingController) {
      existingController.abort();
    }

    let activeId = currentConversationId;
    
    // Auto-create a conversation if none exists
    if (!activeId) {
      try {
        activeId = await get().createConversation();
      } catch (err: unknown) {
        set({ error: getErrorMessage(err) });
        return;
      }
    }

    if (!activeId) {
      set({ error: "Failed to create conversation." });
      return;
    }

    // 1. Add user message locally with unique ID
    const userMsgId = `msg-user-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const tempUserMsg: Message = {
      id: userMsgId,
      conversation_id: activeId,
      role: "user",
      content,
      created_at: new Date().toISOString()
    };

    set((state) => ({
      messages: [...state.messages, tempUserMsg],
      isGenerating: true,
      error: null
    }));

    // 2. Create placeholder for assistant response
    const assistantMsgId = `msg-assistant-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const tempAssistantMsg: Message = {
      id: assistantMsgId,
      conversation_id: activeId,
      role: "assistant",
      content: "",
      created_at: new Date().toISOString()
    };

    set((state) => ({
      messages: [...state.messages, tempAssistantMsg]
    }));

    // 3. Create abort controller for this stream
    const controller = new AbortController();
    set({ abortController: controller });

    let accumulatedContent = "";
    let streamStarted = false;

    try {
      await streamChat(
        activeId,
        content,
        modelType,
        controller,
        // onChunk callback
        (delta) => {
          streamStarted = true;
          accumulatedContent += delta;
          set((state) => ({
            messages: state.messages.map((m) =>
              m.id === assistantMsgId ? { ...m, content: accumulatedContent } : m
            )
          }));
        },
        // onDone callback
        () => {
          set({ isGenerating: false, abortController: null });
          
          // Only refresh if stream actually started (prevent unnecessary DB hits on error)
          if (streamStarted) {
            // Reload conversation to replace temp messages with DB records
            get().selectConversation(activeId);
            get().fetchConversations();
          }
        },
        // onError callback
        (err) => {
          // If stream never started, remove temp assistant message
          if (!streamStarted) {
            set((state) => ({
              messages: state.messages.filter((m) => m.id !== assistantMsgId),
              isGenerating: false,
              abortController: null,
              error: err
            }));
          } else {
            // If partial content was received, keep it and show error
            set({
              isGenerating: false,
              abortController: null,
              error: err
            });
          }
        }
      );
    } catch (err: unknown) {
      // Catch any unexpected errors
      const errorMsg = getErrorMessage(err);
      set((state) => ({
        messages: state.messages.filter((m) => m.id !== assistantMsgId),
        isGenerating: false,
        abortController: null,
        error: errorMsg
      }));
    }
  },

  stopGeneration: () => {
    const { abortController, isGenerating } = get();

    if (!isGenerating || !abortController) {
      return;
    }

    try {
      // Abort the streaming request
      abortController.abort();
      set({ isGenerating: false, abortController: null });
      // Note: We intentionally do NOT fetch from DB here to avoid a race
      // condition if the user immediately sends another message.
      // The temp assistant message remains in state with whatever content
      // was accumulated before abortion — the next DB refresh (via onDone
      // callback or a subsequent selectConversation) will replace it.
    } catch (err: unknown) {
      console.error("Error stopping generation:", err);
      set({ isGenerating: false, abortController: null });
    }
  }
}));
