"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useChatStore } from "../../../store/chatStore";
import { apiGet } from "../../../utils/api";
import {
  Activity, Search, X, Filter, ChevronDown, AlertTriangle, RefreshCw,
  ChevronLeft, ChevronRight, BarChart3,
} from "lucide-react";
import type { AuditLogsResponse, AuditItem } from "../../../components/admin/types";
import { formatDate, statusColor } from "../../../components/admin/helpers";
import Badge from "../../../components/admin/Badge";
import LoadingSpinner from "../../../components/admin/LoadingSpinner";

type StatusFilter = "all" | "success" | "failure" | "error";

export default function AdminAuditPage() {
  const { token, initAuth } = useChatStore();
  const [auditData, setAuditData] = useState<AuditLogsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Filters & Pagination
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [eventTypeFilter, setEventTypeFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [perPage] = useState(30);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);
  const [showEventDropdown, setShowEventDropdown] = useState(false);

  const fetchData = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", String(perPage));
      if (statusFilter !== "all") params.set("status", statusFilter);
      if (eventTypeFilter !== "all") params.set("event_type", eventTypeFilter);
      if (search.trim()) params.set("search", search.trim());
      const result = await apiGet<AuditLogsResponse>(`/admin/audit?${params.toString()}`);
      setAuditData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load audit logs");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [page, perPage, statusFilter, eventTypeFilter, search]);

  useEffect(() => {
    const init = async () => {
      const store = useChatStore.getState();
      if (!store.token) await store.initAuth();
      if (useChatStore.getState().token) fetchData();
      else setLoading(false);
    };
    init();
  }, [fetchData]);

  const handleSearch = (val: string) => {
    setSearch(val);
    setPage(1);
  };

  // Stats
  const stats = useMemo(() => {
    if (!auditData) return { total: 0, success: 0, failed: 0 };
    return {
      total: auditData.total,
      success: auditData.items.filter(l => l.status === "success").length,
      failed: auditData.items.filter(l => l.status === "failure" || l.status === "error").length,
    };
  }, [auditData]);

  const totalPages = auditData?.total_pages || 1;

  if (loading && !auditData) return <LoadingSpinner message="LOADING AUDIT LOGS\u2026" fullScreen />;

  if (!token) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-slate-500">Authentication required.</p>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">Audit Logs</h2>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            {stats.total} events{auditData ? ` \u00b7 page ${auditData.page} of ${auditData.total_pages}` : ""}
          </p>
        </div>
        <button
          onClick={() => { setPage(1); fetchData(true); }}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700 transition-all disabled:opacity-50"
        >
          <RefreshCw className={`size-3.5 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-950/20 border border-rose-900/30 text-rose-300 text-xs animate-in fade-in-down">
          <AlertTriangle className="size-4 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
          <p className="text-xl font-bold text-white tabular-nums">{stats.total}</p>
          <p className="text-[10px] text-slate-500 font-mono mt-0.5">Total Events</p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
          <p className="text-xl font-bold text-emerald-400 tabular-nums">{stats.success}</p>
          <p className="text-[10px] text-slate-500 font-mono mt-0.5">Success</p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
          <p className="text-xl font-bold text-rose-400 tabular-nums">{stats.failed}</p>
          <p className="text-[10px] text-slate-500 font-mono mt-0.5">Failed</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="size-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
          <input
            type="text"
            placeholder="Search events..."
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

        {/* Status Filter */}
        <div className="relative">
          <button
            onClick={() => setShowStatusDropdown(!showStatusDropdown)}
            onBlur={() => setTimeout(() => setShowStatusDropdown(false), 200)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:border-slate-700 transition-colors"
          >
            <Filter className="size-3.5 text-slate-500" />
            <span>Status: <span className="font-semibold text-slate-200 capitalize">{statusFilter}</span></span>
            <ChevronDown className="size-3 text-slate-500" />
          </button>
          {showStatusDropdown && (
            <div className="absolute top-full mt-1 left-0 w-36 rounded-lg border border-slate-800 bg-slate-950 shadow-xl shadow-black/30 z-20 overflow-hidden">
              {(["all", "success", "failure", "error"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => { setStatusFilter(s); setPage(1); setShowStatusDropdown(false); }}
                  className={`w-full px-3 py-2 text-xs text-left transition-colors ${
                    statusFilter === s ? "bg-violet-600/20 text-violet-300" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                  }`}
                >
                  <span className="capitalize">{s === "all" ? "All Status" : s}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Event Type Filter */}
        {auditData && auditData.event_types.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setShowEventDropdown(!showEventDropdown)}
              onBlur={() => setTimeout(() => setShowEventDropdown(false), 200)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:border-slate-700 transition-colors"
            >
              <Filter className="size-3.5 text-slate-500" />
              <span>Event: <span className="font-semibold text-slate-200 capitalize max-w-[80px] truncate inline-block align-bottom">
                {eventTypeFilter === "all" ? "All" : eventTypeFilter.replace(/_/g, " ")}
              </span></span>
              <ChevronDown className="size-3 text-slate-500" />
            </button>
            {showEventDropdown && (
              <div className="absolute top-full mt-1 left-0 w-52 rounded-lg border border-slate-800 bg-slate-950 shadow-xl shadow-black/30 z-20 max-h-48 overflow-y-auto custom-scrollbar">
                <button
                  onClick={() => { setEventTypeFilter("all"); setPage(1); setShowEventDropdown(false); }}
                  className={`w-full px-3 py-2 text-xs text-left transition-colors ${
                    eventTypeFilter === "all" ? "bg-violet-600/20 text-violet-300" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                  }`}
                >
                  All Events
                </button>
                {auditData.event_types.map((et) => (
                  <button
                    key={et}
                    onClick={() => { setEventTypeFilter(et); setPage(1); setShowEventDropdown(false); }}
                    className={`w-full px-3 py-2 text-xs text-left transition-colors capitalize ${
                      eventTypeFilter === et ? "bg-violet-600/20 text-violet-300" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                    }`}
                  >
                    {et.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <span className="text-[10px] text-slate-600 font-mono">{auditData?.items.length || 0} shown</span>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/40 backdrop-blur-sm overflow-hidden hover:border-slate-700/60 transition-all duration-300">
        {auditData && auditData.items.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-16 text-center">
            <Activity className="size-10 text-slate-700" />
            <p className="text-xs text-slate-600">No audit logs match your filters</p>
          </div>
        ) : auditData ? (
          <>
            <div className="overflow-x-auto max-h-[600px] overflow-y-auto custom-scrollbar">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-slate-950/95 z-10">
                  <tr className="border-b border-slate-800 bg-slate-900/50">
                    <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Event</th>
                    <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Status</th>
                    <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Provider</th>
                    <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Model</th>
                    <th className="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Tokens (I\u2192O)</th>
                    <th className="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Latency</th>
                    <th className="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {auditData.items.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-900/30 transition-colors">
                      <td className="px-4 py-3">
                        <span className="text-slate-200 font-medium capitalize">{log.event_type.replace(/_/g, " ")}</span>
                      </td>
                      <td className="px-4 py-3">
                        <Badge label={log.status} color={statusColor(log.status)} />
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-[10px]">
                        {log.provider_name ? <span className="capitalize">{log.provider_name}</span> : <span className="text-slate-600">\u2014</span>}
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-[10px] font-mono">
                        {log.model_name || "\u2014"}
                      </td>
                      <td className="px-4 py-3 text-center font-mono tabular-nums text-slate-400">
                        {log.input_tokens != null ? `${log.input_tokens}\u2192${log.output_tokens}` : "\u2014"}
                      </td>
                      <td className="px-4 py-3 text-center font-mono tabular-nums text-slate-400">
                        {log.latency_ms != null ? `${log.latency_ms}ms` : "\u2014"}
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-500 text-[10px]">{formatDate(log.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800">
                <span className="text-[10px] text-slate-600 font-mono">
                  Page {auditData.page} of {totalPages} ({auditData.total} total)
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="p-1.5 rounded text-slate-500 hover:text-white hover:bg-slate-800 disabled:opacity-30 transition-all"
                  >
                    <ChevronLeft className="size-3.5" />
                  </button>
                  {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                    let p: number;
                    const cp = auditData.page;
                    const tp = totalPages;
                    if (tp <= 7) p = i + 1;
                    else if (cp <= 4) p = i + 1;
                    else if (cp >= tp - 3) p = tp - 6 + i;
                    else p = cp - 3 + i;
                    return (
                      <button
                        key={p}
                        onClick={() => setPage(p)}
                        className={`px-2.5 py-1 rounded text-[10px] font-mono transition-all ${
                          p === auditData.page
                            ? "bg-violet-600/30 text-violet-300 border border-violet-700/40"
                            : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
                        }`}
                      >
                        {p}
                      </button>
                    );
                  })}
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="p-1.5 rounded text-slate-500 hover:text-white hover:bg-slate-800 disabled:opacity-30 transition-all"
                  >
                    <ChevronRight className="size-3.5" />
                  </button>
                </div>
              </div>
            )}
          </>
        ) : loading ? (
          <LoadingSpinner message="LOADING AUDIT LOGS\u2026" />
        ) : null}
      </div>
    </div>
  );
}
