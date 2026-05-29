"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useChatStore } from "../../../store/chatStore";
import { apiGet } from "../../../utils/api";
import {
  Fingerprint, Search, X, Filter, ChevronDown, AlertTriangle, RefreshCw,
  Shield, ChevronLeft, ChevronRight, BarChart3,
} from "lucide-react";
import type { DlpEventsResponse, DlpEventItem } from "../../../components/admin/types";
import { formatDate, timeAgo } from "../../../components/admin/helpers";
import Badge from "../../../components/admin/Badge";
import LoadingSpinner from "../../../components/admin/LoadingSpinner";

type ActionFilter = "all" | "block" | "warn" | "allow";

export default function AdminDlpPage() {
  const { token, initAuth } = useChatStore();
  const [dlpData, setDlpData] = useState<DlpEventsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Filters & Pagination
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState<ActionFilter>("all");
  const [page, setPage] = useState(1);
  const [perPage] = useState(30);
  const [showActionDropdown, setShowActionDropdown] = useState(false);

  const fetchData = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", String(perPage));
      if (actionFilter !== "all") params.set("action", actionFilter);
      const result = await apiGet<DlpEventsResponse>(`/admin/dlp?${params.toString()}`);
      setDlpData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load DLP events");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [page, perPage, actionFilter]);

  useEffect(() => {
    const init = async () => {
      const store = useChatStore.getState();
      if (!store.token) await store.initAuth();
      if (useChatStore.getState().token) fetchData();
      else setLoading(false);
    };
    init();
  }, [fetchData]);

  // Client-side search
  const filteredItems = useMemo(() => {
    if (!dlpData?.items) return [];
    if (!search.trim()) return dlpData.items;
    const q = search.toLowerCase();
    return dlpData.items.filter((event) =>
      event.action.toLowerCase().includes(q) ||
      (event.redacted_excerpt || "").toLowerCase().includes(q)
    );
  }, [dlpData?.items, search]);

  const stats = useMemo(() => {
    if (!dlpData) return { total: 0, blocked: 0, warned: 0, allowed: 0 };
    const items = dlpData.items;
    return {
      total: dlpData.total,
      blocked: items.filter(e => e.action === "block").length,
      warned: items.filter(e => e.action === "warn").length,
      allowed: items.filter(e => e.action === "allow").length,
    };
  }, [dlpData]);

  const actionBadge = (action: string) => {
    switch (action) {
      case "block": return { label: "Blocked", color: "text-rose-400 bg-rose-950/30 border-rose-900/30" };
      case "warn": return { label: "Warning", color: "text-yellow-400 bg-yellow-950/30 border-yellow-900/30" };
      default: return { label: "Allowed", color: "text-emerald-400 bg-emerald-950/30 border-emerald-900/30" };
    }
  };

  const actionBarColor = (action: string) => {
    switch (action) {
      case "block": return "from-rose-600 to-red-500";
      case "warn": return "from-yellow-500 to-amber-400";
      default: return "from-emerald-500 to-teal-500";
    }
  };

  const totalPages = dlpData?.total_pages || 1;

  if (loading && !dlpData) return <LoadingSpinner message="LOADING DLP EVENTS\u2026" fullScreen />;

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
          <h2 className="text-lg font-bold text-white">DLP Events</h2>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            Data Loss Prevention monitoring &middot; {stats.total} total events
            {dlpData ? ` \u00b7 page ${dlpData.page} of ${dlpData.total_pages}` : ""}
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

      {/* Quick Stats + Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <div className="lg:col-span-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-white tabular-nums">{stats.total}</p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">Total Events</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-rose-400 tabular-nums">{stats.blocked}</p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">Blocked</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-yellow-400 tabular-nums">{stats.warned}</p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">Warnings</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-emerald-400 tabular-nums">
              {stats.total > 0 ? `${Math.round((1 - stats.blocked / stats.total) * 100)}%` : "100%"}
            </p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">Pass Rate</p>
          </div>
        </div>

        {/* Action Distribution Mini Chart */}
        {dlpData && dlpData.action_distribution.length > 0 && (
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 hover:border-slate-700/60 transition-colors">
            <div className="flex items-center gap-1.5 mb-2">
              <BarChart3 className="size-3 text-slate-500" />
              <p className="text-[9px] text-slate-500 font-mono uppercase tracking-wider">By Action</p>
            </div>
            <div className="space-y-1.5">
              {dlpData.action_distribution.map((d) => {
                const maxCount = Math.max(...dlpData.action_distribution.map(a => a.count), 1);
                const pct = (d.count / maxCount) * 100;
                return (
                  <div key={d.action} className="flex items-center gap-2">
                    <span className="text-[9px] text-slate-400 capitalize w-10">{d.action}</span>
                    <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full bg-gradient-to-r ${actionBarColor(d.action)} transition-all duration-500`}
                        style={{ width: `${Math.max(8, pct)}%` }}
                      />
                    </div>
                    <span className="text-[9px] text-slate-500 font-mono w-5 text-right">{d.count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="size-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
          <input
            type="text"
            placeholder="Search events or content..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-8 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-violet-700/50 transition-colors"
          />
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-400">
              <X className="size-3.5" />
            </button>
          )}
        </div>

        {/* Action Filter */}
        <div className="relative">
          <button
            onClick={() => setShowActionDropdown(!showActionDropdown)}
            onBlur={() => setTimeout(() => setShowActionDropdown(false), 200)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:border-slate-700 transition-colors"
          >
            <Filter className="size-3.5 text-slate-500" />
            <span>Action: <span className="font-semibold text-slate-200 capitalize">{actionFilter}</span></span>
            <ChevronDown className="size-3 text-slate-500" />
          </button>
          {showActionDropdown && (
            <div className="absolute top-full mt-1 left-0 w-36 rounded-lg border border-slate-800 bg-slate-950 shadow-xl shadow-black/30 z-20 overflow-hidden">
              {(["all", "block", "warn", "allow"] as const).map((a) => (
                <button
                  key={a}
                  onClick={() => { setActionFilter(a); setPage(1); setShowActionDropdown(false); }}
                  className={`w-full px-3 py-2 text-xs text-left capitalize transition-colors ${
                    actionFilter === a ? "bg-violet-600/20 text-violet-300" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                  }`}
                >
                  {a === "all" ? "All Actions" : a}
                </button>
              ))}
            </div>
          )}
        </div>

        <span className="text-[10px] text-slate-600 font-mono">{filteredItems.length} events</span>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/40 backdrop-blur-sm overflow-hidden hover:border-slate-700/60 transition-all duration-300">
        {filteredItems.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-16 text-center">
            <Fingerprint className="size-10 text-slate-700" />
            <p className="text-xs text-slate-600">No DLP events match your filters</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto max-h-[600px] overflow-y-auto custom-scrollbar">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-slate-950/95 z-10">
                  <tr className="border-b border-slate-800 bg-slate-900/50">
                    <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Action</th>
                    <th className="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Matches</th>
                    <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Content Excerpt</th>
                    <th className="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {filteredItems.map((event) => {
                    const badge = actionBadge(event.action);
                    return (
                      <tr key={event.id} className="hover:bg-slate-900/30 transition-colors">
                        <td className="px-4 py-3">
                          <Badge label={badge.label} color={badge.color} />
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="inline-flex items-center justify-center min-w-[2rem] px-2 py-0.5 rounded-full text-[10px] font-semibold font-mono bg-slate-900 border border-slate-800 text-slate-300">
                            {event.match_count}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-400 text-[10px] max-w-[400px] truncate font-mono">
                          <div className="flex items-center gap-2">
                            <Shield className="size-3 text-slate-600 flex-shrink-0" />
                            <span className="truncate">{event.redacted_excerpt || "\u2014"}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-500 text-[10px]">{formatDate(event.created_at)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800">
                <span className="text-[10px] text-slate-600 font-mono">
                  Page {dlpData!.page} of {totalPages} ({dlpData!.total} total)
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
                    const cp = dlpData!.page;
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
                          p === dlpData!.page
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
        )}
      </div>
    </div>
  );
}
