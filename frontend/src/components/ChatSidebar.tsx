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
  Loader2
} from "lucide-react";

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

  return (
    <aside className="w-80 border-r border-slate-800 bg-slate-950 flex flex-col h-full text-slate-200">
      {/* Sidebar Header */}
      <div className="p-5 border-b border-slate-900 flex items-center gap-2.5">
        <div className="p-1.5 rounded-lg bg-gradient-to-tr from-violet-600 to-indigo-600 shadow-md">
          <Bot className="size-5 text-white" />
        </div>
        <div>
          <h1 className="font-semibold text-base text-white">
            Dushman AI
          </h1>
          <span className="text-[10px] text-slate-500 font-medium tracking-wide uppercase">
            LLM Orchestrator
          </span>
        </div>
      </div>

      {/* Action Button */}
      <div className="p-4">
        <button
          onClick={handleCreateChat}
          disabled={isGenerating}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl font-medium text-sm text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 transition-all duration-300 shadow-lg shadow-indigo-600/10 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="size-4" />
          New Conversation
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-3 space-y-1.5 custom-scrollbar">
        {loadingConversations ? (
          <div className="flex flex-col items-center py-10 px-4">
            <Loader2 className="size-5 text-slate-600 animate-spin mb-2" />
            <span className="text-[10px] text-slate-600 font-mono">Loading conversations…</span>
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-8 px-4 text-xs text-slate-600">
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
                    ? "bg-slate-900 border-slate-800 text-white shadow-inner" 
                    : "border-transparent text-slate-400 hover:bg-slate-900/40 hover:text-slate-200"
                  }
                `}
              >
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  <MessageSquare className={`size-4 flex-shrink-0 ${isSelected ? "text-violet-400" : "text-slate-600"}`} />
                  
                  {isEditing ? (
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      className="bg-slate-800 text-white border border-slate-700 rounded px-1.5 py-0.5 text-xs w-full focus:outline-none focus:border-violet-500"
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
                        className="p-1 rounded hover:bg-slate-800 text-emerald-400 transition"
                      >
                        <Check className="size-3.5" />
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="p-1 rounded hover:bg-slate-800 text-rose-400 transition"
                      >
                        <X className="size-3.5" />
                      </button>
                    </>
                  ) : (
                    <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity duration-200">
                      <button
                        onClick={(e) => handleStartEdit(chat.id, chat.title, e)}
                        className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition"
                      >
                        <Edit3 className="size-3.5" />
                      </button>
                      <button
                        onClick={(e) => handleDelete(chat.id, e)}
                        className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-rose-400 transition"
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
      <div className="p-4 border-t border-slate-900 bg-slate-950/80">
        <div className="flex items-center justify-between p-2 rounded-xl bg-slate-900/50 border border-slate-900">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="size-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
              <UserIcon className="size-4" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-300 truncate">
                {user?.email || "Anonymous"}
              </p>
              <p className="text-[10px] text-slate-500 truncate">
                Authenticated Account
              </p>
            </div>
          </div>
          <button
            onClick={logout}
            title="Log Out"
            className="p-2 rounded-lg text-rose-200/80 hover:text-rose-100 hover:bg-rose-950/20 border border-transparent hover:border-rose-900/30 transition-all cursor-pointer"
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
