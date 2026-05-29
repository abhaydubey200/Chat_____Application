"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useChatStore } from "../../../store/chatStore";
import { apiGet } from "../../../utils/api";
import {
  MessageSquare, Search, X, Eye, AlertTriangle, RefreshCw,
  ChevronLeft, ChevronRight, Users, ArrowUpDown, Calendar,
  ChevronUp, ChevronDown,
} from "lucide-react";
import type { ConversationsResponse } from "../../../components/admin/types";
import { timeAgo, formatDateShort } from "../../../components/admin/helpers";
import ConversationDetailModal from "../../../components/admin/ConversationDetailModal";
import LoadingSpinner from "../../../components/admin/LoadingSpinner";

type SortField = "title" | "message_count" | "updated_at" | "created_at";
type SortDir = "asc" | "desc";

export default function AdminConversationsPage() {
  const { token, initAuth } = useChatStore();
  const [convData, setConvData] = useState<ConversationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [perPage] = useState(15);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>("updated_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const fetchConversations = useCallback(async (pageNum: number, searchTerm: string) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("page", String(pageNum));
      params.set("per_page", String(perPage));
      if (searchTerm.trim()) params.set("search", searchTerm.trim());
      const result = await apiGet<ConversationsResponse>(`/admin/conversations?${params.toString()}`);
      setConvData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load conversations");
    } finally {
      setLoading(false);
    }
  }, [perPage]);

  useEffect(() => {
    const init = async () => {
      const store = useChatStore.getState();
      if (!store.token) await store.initAuth();
      fetchConversations(page, search);
    };
    init();
  }, [page, search, fetchConversations]);

  const handleSearch = (val: string) => {
    setSearch(val);
    setPage(1);
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir(field === "title" ? "asc" : "desc");
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown className="size-2.5 inline ml-1 opacity-30" />;
    return sortDir === "asc" ? <ChevronUp className="size-2.5 inline ml-1" /> : <ChevronDown className="size-2.5 inline ml-1" />;
  };

  // Sort items client-side (server returns them sorted by updated_at desc)
  const sortedItems = useMemo(() => {
    if (!convData?.items) return [];
    const items = [...convData.items];
    items.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "title": cmp = a.title.localeCompare(b.title); break;
        case "message_count": cmp = a.message_count - b.message_count; break;
        case "created_at": cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime(); break;
        case "updated_at": cmp = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime(); break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return items;
  }, [convData?.items, sortField, sortDir]);

  const totalPages = convData?.total_pages || 1;

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in">
      {/* Modal */}
      {selectedId && (
        <ConversationDetailModal conversationId={selectedId} onClose={() => setSelectedId(null)} />
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">All Conversations</h2>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            {convData ? `${convData.total} total conversations` : "Loading..."}
          </p>
        </div>
        <button
          onClick={() => fetchConversations(page, search)}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700 transition-all disabled:opacity-50"
        >
          <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} />
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-950/20 border border-rose-900/30 text-rose-300 text-xs animate-in fade-in-down">
          <AlertTriangle className="size-4 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Stats row */}
      {convData && (
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-white tabular-nums">{convData.total}</p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">Total</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-emerald-400 tabular-nums">
              {convData.items.reduce((s, i) => s + i.message_count, 0)}
            </p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">Total Messages</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-amber-400 tabular-nums">
              {convData.items.length > 0 ? Math.round(convData.items.reduce((s, i) => s + i.message_count, 0) / convData.items.length) : 0}
            </p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">Avg Msgs/Conv</p>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="size-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
        <input
          type="text"
          placeholder="Search conversations by title..."
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="w-full pl-8 pr-8 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-violet-700/50 transition-colors"
        />
        {search && (
          <button onClick={() => handleSearch("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-400">
            <X className="size-3.5" />
          </button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/40 backdrop-blur-sm overflow-hidden hover:border-slate-700/60 transition-all duration-300">
        {loading && !convData ? (
          <LoadingSpinner message="LOADING CONVERSATIONS\u2026" />
        ) : convData && sortedItems.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-16 text-center">
            <MessageSquare className="size-10 text-slate-700" />
            <p className="text-xs text-slate-600">No conversations found</p>
            {search && (
              <button onClick={() => handleSearch("")} className="text-xs text-violet-400 hover:text-violet-300">
                Clear search
              </button>
            )}
          </div>
        ) : convData ? (
          <>
            <div className="overflow-x-auto max-h-[550px] overflow-y-auto custom-scrollbar">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-slate-950/95 z-10">
                  <tr className="border-b border-slate-800 bg-slate-900/50">
                    <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono cursor-pointer hover:text-slate-300 select-none" onClick={() => handleSort("title")}>
                      Title <SortIcon field="title" />
                    </th>
                    <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">
                      <span className="flex items-center gap-1"><Users className="size-3" /> User</span>
                    </th>
                    <th className="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono cursor-pointer hover:text-slate-300 select-none" onClick={() => handleSort("message_count")}>
                      <span className="flex items-center justify-center gap-1"><MessageSquare className="size-3" /> Msgs <SortIcon field="message_count" /></span>
                    </th>
                    <th className="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono cursor-pointer hover:text-slate-300 select-none" onClick={() => handleSort("created_at")}>
                      <span className="flex items-center justify-center gap-1"><Calendar className="size-3" /> Created <SortIcon field="created_at" /></span>
                    </th>
                    <th className="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono cursor-pointer hover:text-slate-300 select-none" onClick={() => handleSort("updated_at")}>
                      <span className="flex items-center justify-center gap-1"><ArrowUpDown className="size-3" /> Updated <SortIcon field="updated_at" /></span>
                    </th>
                    <th className="text-center px-4 py-3 w-10"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {sortedItems.map((conv) => (
                    <tr key={conv.id} className="hover:bg-slate-900/30 transition-colors group">
                      <td className="px-4 py-3 min-w-0">
                        <span className="text-xs text-slate-200 truncate block max-w-[280px]">{conv.title}</span>
                        <span className="text-[10px] text-slate-600 font-mono">{conv.id.substring(0, 8)}...</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5">
                          <div className="size-5 rounded-full bg-slate-800 flex items-center justify-center">
                            <Users className="size-2.5 text-slate-500" />
                          </div>
                          <span className="text-[10px] text-slate-400">{conv.user_email}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center font-mono tabular-nums text-slate-400">{conv.message_count}</td>
                      <td className="px-4 py-3 text-center font-mono tabular-nums text-slate-500 text-[10px]">{formatDateShort(conv.created_at)}</td>
                      <td className="px-4 py-3 text-center font-mono tabular-nums text-slate-500 text-[10px]">{timeAgo(conv.updated_at)}</td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => setSelectedId(conv.id)}
                          className="p-1.5 rounded-lg text-slate-600 hover:text-violet-400 hover:bg-violet-950/20 opacity-0 group-hover:opacity-100 transition-all"
                          title="View conversation"
                        >
                          <Eye className="size-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800">
                <span className="text-[10px] text-slate-600 font-mono">
                  Page {convData.page} of {totalPages} ({convData.total} total)
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="p-1.5 rounded text-slate-500 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                  >
                    <ChevronLeft className="size-3.5" />
                  </button>
                  {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                    let pageNum: number;
                    const cp = convData.page;
                    const tp = totalPages;
                    if (tp <= 7) {
                      pageNum = i + 1;
                    } else if (cp <= 4) {
                      pageNum = i + 1;
                    } else if (cp >= tp - 3) {
                      pageNum = tp - 6 + i;
                    } else {
                      pageNum = cp - 3 + i;
                    }
                    return (
                      <button
                        key={pageNum}
                        onClick={() => setPage(pageNum)}
                        className={`px-2.5 py-1 rounded text-[10px] font-mono transition-all ${
                          pageNum === convData.page
                            ? "bg-violet-600/30 text-violet-300 border border-violet-700/40"
                            : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="p-1.5 rounded text-slate-500 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                  >
                    <ChevronRight className="size-3.5" />
                  </button>
                </div>
              </div>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}
