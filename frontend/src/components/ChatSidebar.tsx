"use client";

import React, { useEffect, useState } from "react";
import { useChatStore } from "../store/chatStore";
import { 
  Plus, 
  MessageSquare, 
  Trash2, 
  Edit3, 
  Check, 
  X, 
  LogOut, 
  User as UserIcon,
  Bot,
  ChevronLeft,
  Loader2,
  Sun,
  Moon
} from "lucide-react";
import { useThemeStore } from "../store/useThemeStore";

interface ChatSidebarProps {
  onClose?: () => void;
}

export default function ChatSidebar({ onClose }: ChatSidebarProps) {
  const {
    user,
    conversations,
    currentConversationId,
    fetchConversations,
    createConversation,
    selectConversation,
    renameConversation,
    deleteConversation,
    logout,
    isGenerating
  } = useChatStore();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [loadingConversations, setLoadingConversations] = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      await fetchConversations();
      if (mounted) setLoadingConversations(false);
    };
    load();
    return () => { mounted = false; };
  }, [fetchConversations]);

  const handleCreateChat = async () => {
    if (isGenerating) return;
    try {
      await createConversation();
    } catch (e) {
      console.error(e);
    }
  };

  const handleStartEdit = (id: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(id);
    setEditTitle(currentTitle);
  };

  const handleSaveEdit = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      await renameConversation(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleCancelEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("Are you sure you want to delete this conversation?")) {
      await deleteConversation(id);
    }
  };

  const handleConversationKeyDown = (
    e: React.KeyboardEvent<HTMLDivElement>,
    chatId: string,
    isEditing: boolean
  ) => {
    if (isEditing) return;

    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      selectConversation(chatId);
    }
  };

  const { theme, toggleTheme } = useThemeStore();

  return (
    <aside className="w-80 border-r border-[var(--border)] bg-[var(--bg-sidebar)] flex flex-col h-full text-[var(--text-primary)] transition-colors duration-300">
      {/* Sidebar Header */}
      <div className="p-5 border-b border-[var(--border)] flex items-center gap-2.5">
        <div className="p-1.5 rounded-lg bg-gradient-to-tr from-violet-600 to-indigo-600 shadow-md">
          <Bot className="size-5 text-white" />
        </div>
        <div className="flex-1">
          <h1 className="font-semibold text-base text-[var(--text-primary)]">
            ChatHub
          </h1>
          <span className="text-[10px] text-[var(--text-tertiary)] font-medium tracking-wide uppercase">
            LLM Orchestrator
          </span>
        </div>
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg hover:bg-[var(--bg-hover)] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-all"
          title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
          {theme === "dark" ? (
            <Sun className="size-4 text-[var(--accent-amber)]" />
          ) : (
            <Moon className="size-4 text-[var(--primary)]" />
          )}
        </button>
      </div>

      {/* Action Button */}
      <div className="p-4">
        <button
          onClick={handleCreateChat}
          disabled={isGenerating}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl font-medium text-sm text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 transition-all duration-300 shadow-lg shadow-indigo-600/10 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="size-4" />
          New Chat
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-3 space-y-1.5 custom-scrollbar">
        {loadingConversations ? (
          <div className="flex flex-col items-center py-10 px-4">
            <Loader2 className="size-5 text-[var(--text-tertiary)] animate-spin mb-2" />
            <span className="text-[10px] text-[var(--text-tertiary)] font-mono">Loading conversations…</span>
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-8 px-4 text-xs text-[var(--text-tertiary)]">
            No conversations yet. Start a new one!
          </div>
        ) : (
          conversations.map((chat) => {
            const isSelected = currentConversationId === chat.id;
            const isEditing = editingId === chat.id;

            return (
              <div
                key={chat.id}
                onClick={() => !isEditing && selectConversation(chat.id)}
                onKeyDown={(e) => handleConversationKeyDown(e, chat.id, isEditing)}
                role="button"
                tabIndex={0}
                className={`group flex items-center justify-between px-3.5 py-3 rounded-xl cursor-pointer transition-all duration-200 border
                  ${isSelected 
                    ? "bg-[var(--bg-elevated)] border-[var(--border)] text-[var(--text-primary)] shadow-inner" 
                    : "border-transparent text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                  }
                `}
              >
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  <MessageSquare className={`size-4 flex-shrink-0 ${isSelected ? "text-[var(--primary)]" : "text-[var(--text-tertiary)]"}`} />
                  
                  {isEditing ? (
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      className="bg-[var(--bg-input)] text-[var(--text-primary)] border border-[var(--border)] rounded px-1.5 py-0.5 text-xs w-full focus:outline-none focus:border-[var(--primary)]"
                    />
                  ) : (
                    <span className="text-xs font-medium truncate">
                      {chat.title}
                    </span>
                  )}
                </div>

                {/* Operations */}
                <div className="flex items-center gap-1.5 ml-2">
                  {isEditing ? (
                    <>
                      <button
                        onClick={(e) => handleSaveEdit(chat.id, e)}
                        className="p-1 rounded hover:bg-[var(--bg-hover)] text-[var(--accent-emerald)] transition"
                      >
                        <Check className="size-3.5" />
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="p-1 rounded hover:bg-[var(--bg-hover)] text-[var(--accent-rose)] transition"
                      >
                        <X className="size-3.5" />
                      </button>
                    </>
                  ) : (
                    <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity duration-200">
                      <button
                        onClick={(e) => handleStartEdit(chat.id, chat.title, e)}
                        className="p-1 rounded hover:bg-[var(--bg-hover)] text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition"
                      >
                        <Edit3 className="size-3.5" />
                      </button>
                      <button
                        onClick={(e) => handleDelete(chat.id, e)}
                        className="p-1 rounded hover:bg-[var(--bg-hover)] text-[var(--text-tertiary)] hover:text-[var(--accent-rose)] transition"
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Sidebar Footer */}
      <div className="p-4 border-t border-[var(--border)] bg-[var(--bg-sidebar)]/80">
        <div className="flex items-center justify-between p-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border)]">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="size-8 rounded-full bg-[var(--bg-hover)] border border-[var(--border)] flex items-center justify-center text-[var(--text-secondary)]">
              <UserIcon className="size-4" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-[var(--text-primary)] truncate">
                {user?.email || "Anonymous"}
              </p>
              <p className="text-[10px] text-[var(--text-tertiary)] truncate">
                Authenticated Account
              </p>
            </div>
          </div>
          <button
            onClick={logout}
            title="Log Out"
            className="p-2 rounded-lg text-[var(--accent-rose)]/60 hover:text-[var(--accent-rose)] hover:bg-[var(--accent-rose)]/10 border border-transparent hover:border-[var(--accent-rose)]/20 transition-all cursor-pointer"
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
