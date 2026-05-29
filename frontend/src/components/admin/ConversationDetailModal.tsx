"use client";

import React, { useEffect, useState } from "react";
import { MessageSquare, X, Loader2, AlertTriangle } from "lucide-react";
import { apiGet } from "../../utils/api";
import { ConversationDetailResponse } from "./types";
import { formatDateFull } from "./helpers";

interface ConversationDetailModalProps {
  conversationId: string;
  onClose: () => void;
}

export default function ConversationDetailModal({ conversationId, onClose }: ConversationDetailModalProps) {
  const [data, setData] = useState<ConversationDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchConversation = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await apiGet<ConversationDetailResponse>(`/admin/conversations/${conversationId}`);
        setData(result);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load conversation");
      } finally {
        setLoading(false);
      }
    };
    fetchConversation();
  }, [conversationId]);

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-12 pb-8 px-4 overflow-y-auto">
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-3xl rounded-2xl border border-slate-800 bg-slate-950/95 backdrop-blur-xl shadow-2xl shadow-black/50 overflow-hidden">
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <div className="flex items-center gap-3 min-w-0">
            <div className="size-10 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center flex-shrink-0">
              <MessageSquare className="size-5 text-white" />
            </div>
            <div className="min-w-0">
              {loading ? (
                <p className="text-sm font-semibold text-slate-300">Loading...</p>
              ) : (
                <>
                  <p className="text-sm font-semibold text-white truncate">{data?.conversation.title || "Conversation"}</p>
                  <p className="text-[10px] text-slate-500 font-mono">by {data?.conversation.user_email || "unknown"}</p>
                </>
              )}
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-800 text-slate-500 hover:text-white transition-colors flex-shrink-0">
            <X className="size-5" />
          </button>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="size-8 text-violet-400 animate-spin" />
          </div>
        )}

        {error && (
          <div className="p-6">
            <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-950/20 border border-rose-900/30 text-rose-300 text-xs">
              <AlertTriangle className="size-4" />{error}
            </div>
          </div>
        )}

        {data && !loading && (
          <div className="p-5 space-y-3 max-h-[70vh] overflow-y-auto custom-scrollbar">
            <div className="flex items-center gap-4 text-[10px] text-slate-600 font-mono pb-3 border-b border-slate-800">
              <span>Created: {formatDateFull(data.conversation.created_at)}</span>
              <span>Messages: {data.messages.length}</span>
            </div>
            {data.messages.length === 0 ? (
              <p className="text-xs text-slate-600 text-center py-8">No messages in this conversation.</p>
            ) : (
              data.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`p-3 rounded-lg ${
                    msg.role === "user"
                      ? "bg-violet-950/20 border border-violet-900/20"
                      : "bg-slate-900/50 border border-slate-800/50"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={`text-[10px] font-bold uppercase tracking-wider ${msg.role === "user" ? "text-violet-400" : "text-emerald-400"}`}>
                      {msg.role}
                    </span>
                    {msg.model_used && (
                      <span className="text-[10px] text-slate-600 font-mono">{msg.model_used}</span>
                    )}
                    {msg.provider_used && (
                      <span className="text-[10px] text-slate-600 font-mono">via {msg.provider_used}</span>
                    )}
                  </div>
                  <p className="text-xs text-slate-300 whitespace-pre-wrap break-words leading-relaxed">{msg.content}</p>
                </div>
              ))
            )}
          </div>
        )}

        <div className="border-t border-slate-800 p-3 flex justify-end">
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700 transition-all">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
