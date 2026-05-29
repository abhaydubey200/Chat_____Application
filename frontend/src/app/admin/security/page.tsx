"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useChatStore } from "../../../store/chatStore";
import { apiGet } from "../../../utils/api";
import {
  Shield, Search, X, Filter, ChevronDown, AlertTriangle, RefreshCw,
  Globe, ChevronLeft, ChevronRight, BarChart3,
} from "lucide-react";
import type { SecurityEventsResponse, SecurityItem } from "../../../components/admin/types";
import { formatDate, severityColor, statusColor } from "../../../components/admin/helpers";
import Badge from "../../../components/admin/Badge";
import LoadingSpinner from "../../../components/admin/LoadingSpinner";

type SeverityFilter = "all" | "critical" | "high" | "medium" | "low";
type StatusFilterSecurity = "all" | "open" | "resolved" | "closed";

export default function AdminSecurityPage() {
  const { token, initAuth } = useChatStore();
  const [secData, setSecData] = useState<SecurityEventsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Filters & Pagination
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilterSecurity>("all");
  const [page, setPage] = useState(1);
  const [perPage] = useState(30);
  const [showSeverityDropdown, setShowSeverityDropdown] = useState(false);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);

  const fetchData = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", String(perPage));
      if (severityFilter !== "all") params.set("severity", severityFilter);
      if (statusFilter !== "all") params.set("status", statusFilter);
      const result = await apiGet<SecurityEventsResponse>(`/admin/security?${params.toString()}`);
      setSecData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load security events");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [page, perPage, severityFilter, statusFilter]);

  useEffect(() => {
    const init = async () => {
      const store = useChatStore.getState();
      if (!store.token) await store.initAuth();
      if (useChatStore.getState().token) fetchData();
      else setLoading(false);
    };
    init();
  }, [fetchData]);

  // Client-side search filter
  const filteredItems = useMemo(() => {
    if (!secData?.items) return [];
    if (!search.trim()) return secData.items;
    const q = search.toLowerCase();
    return secData.items.filter((event) =>
      event.event_type.toLowerCase().includes(q) ||
      event.severity.toLowerCase().includes(q) ||
      (event.ip_address || "").toLowerCase().includes(q)
    );
  }, [secData?.items, search]);

  const stats = useMemo(() => {
    if (!secData) return { total: 0, critical: 0, high: 0, open: 0 };
    const items = secData.items;
    return {
      total: secData.total,
      critical: items.filter(e => e.severity === "critical").length,
      high: items.filter(e => e.severity === "high").length,
      open: items.filter(e => e.status === "open").length,
    };
  }, [secData]);

  const totalPages = secData?.total_pages || 1;

  // Severity color for distribution bars
  const severityBarColor = (sev: string) => {
    switch (sev) {
      case "critical": return "from-rose-600 to-red-500";
      case "high": return "from-orange-500 to-amber-500";
      case "medium": return "from-yellow-500 to-amber-400";
      case "low": return "from-slate-500 to-slate-400";
      default: return "from-violet-600 to-indigo-500";
    }
  };

  if (loading && !secData) return <LoadingSpinner message="LOADING SECURITY EVENTS\u2026" fullScreen />;

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
          <h2 className="text-lg font-bold text-white">Security Events</h2>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            {stats.total} events{secData ? ` \u00b7 page ${secData.page} of ${secData.total_pages}` : ""}
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

      {/* Quick Stats + Severity Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <div className="lg:col-span-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-white tabular-nums">{stats.total}</p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">Total Events</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-rose-400 tabular-nums">{stats.critical}</p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">Critical</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-orange-400 tabular-nums">{stats.high}</p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">High</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-yellow-400 tabular-nums">{stats.open}</p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">Open</p>
          </div>
        </div>

        {/* Severity Distribution Mini Chart */}
        {secData && secData.severity_distribution.length > 0 && (
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 hover:border-slate-700/60 transition-colors">
            <div className="flex items-center gap-1.5 mb-2">
              <BarChart3 className="size-3 text-slate-500" />
              <p className="text-[9px] text-slate-500 font-mono uppercase tracking-wider">Distribution</p>
            </div>
            <div className="space-y-1.5">
              {secData.severity_distribution.map((d) => {
                const maxCount = Math.max(...secData.severity_distribution.map(s => s.count), 1);
                const pct = (d.count / maxCount) * 100;
                return (
                  <div key={d.severity} className="flex items-center gap-2">
                    <span className="text-[9px] text-slate-400 capitalize w-10">{d.severity}</span>
                    <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full bg-gradient-to-r ${severityBarColor(d.severity)} transition-all duration-500`}
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
            placeholder="Search events, severity, or IP..."
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

        {/* Severity Filter */}
        <div className="relative">
          <button
            onClick={() => setShowSeverityDropdown(!showSeverityDropdown)}
            onBlur={() => setTimeout(() => setShowSeverityDropdown(false), 200)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:border-slate-700 transition-colors"
          >
            <Filter className="size-3.5 text-slate-500" />
            <span>Severity: <span className="font-semibold text-slate-200 capitalize">{severityFilter}</span></span>
            <ChevronDown className="size-3 text-slate-500" />
          </button>
          {showSeverityDropdown && (
            <div className="absolute top-full mt-1 left-0 w-36 rounded-lg border border-slate-800 bg-slate-950 shadow-xl shadow-black/30 z-20 overflow-hidden">
              {(["all", "critical", "high", "medium", "low"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => { setSeverityFilter(s); setPage(1); setShowSeverityDropdown(false); }}
                  className={`w-full px-3 py-2 text-xs text-left capitalize transition-colors ${
                    severityFilter === s ? "bg-violet-600/20 text-violet-300" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                  }`}
                >
                  {s === "all" ? "All Severities" : s}
                </button>
              ))}
            </div>
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
              {(["all", "open", "resolved", "closed"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => { setStatusFilter(s); setPage(1); setShowStatusDropdown(false); }}
                  className={`w-full px-3 py-2 text-xs text-left capitalize transition-colors ${
                    statusFilter === s ? "bg-violet-600/20 text-violet-300" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                  }`}
                >
                  {s === "all" ? "All Status" : s}
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
            <Shield className="size-10 text-slate-700" />
            <p className="text-xs text-slate-600">No security events match your filters</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto max-h-[600px] overflow-y-auto custom-scrollbar">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-slate-950/95 z-10">
                  <tr className="border-b border-slate-800 bg-slate-900/50">
                    <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Event</th>
                    <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Severity</th>
                    <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Status</th>
                    <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">IP Address</th>
                    <th className="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {filteredItems.map((event) => (
                    <tr key={event.id} className="hover:bg-slate-900/30 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Shield className="size-3.5 text-slate-500" />
                          <span className="text-slate-200 font-medium capitalize">{event.event_type.replace(/_/g, " ")}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge label={event.severity} color={severityColor(event.severity)} />
                      </td>
                      <td className="px-4 py-3">
                        <Badge label={event.status} color={statusColor(event.status)} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5">
                          <Globe className="size-3 text-slate-600" />
                          <span className="text-slate-400 font-mono text-[10px]">{event.ip_address || "\u2014"}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-500 text-[10px]">{formatDate(event.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800">
                <span className="text-[10px] text-slate-600 font-mono">
                  Page {secData!.page} of {totalPages} ({secData!.total} total)
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
                    const cp = secData!.page;
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
                          p === secData!.page
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
