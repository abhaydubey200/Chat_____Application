"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useChatStore } from "../../../store/chatStore";
import { apiGet } from "../../../utils/api";
import {
  Users, Search, X, Eye, AlertTriangle, RefreshCw, Filter,
  ChevronDown, UserCheck, UserX, Calendar, ArrowUpDown,
  Download, ChevronUp, BarChart3,
} from "lucide-react";
import type { DashboardData, UserRow } from "../../../components/admin/types";
import {
  formatNumber, formatCost, formatDateShort, formatDateFull, timeAgo, roleBadge,
} from "../../../components/admin/helpers";
import UserDetailModal from "../../../components/admin/UserDetailModal";
import LoadingSpinner from "../../../components/admin/LoadingSpinner";

type RoleFilter = "all" | "super_admin" | "admin" | "security_admin" | "manager" | "employee";
type StatusFilter = "all" | "active" | "inactive";
type SortField = "email" | "role" | "created_at" | "conversation_count" | "message_count" | "total_tokens" | "total_cost" | "last_active";
type SortDir = "asc" | "desc";

export default function AdminUsersPage() {
  const { token, initAuth } = useChatStore();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Filters
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [showRoleDropdown, setShowRoleDropdown] = useState(false);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);

  // Sort
  const [sortField, setSortField] = useState<SortField>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  // Selected user for detail modal
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  const fetchData = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const result = await apiGet<DashboardData>("/admin/dashboard");
      setData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      const store = useChatStore.getState();
      if (!store.token) await store.initAuth();
      if (useChatStore.getState().token) fetchData();
      else setLoading(false);
    };
    init();
  }, [fetchData]);

  // Toggle sort
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir(field === "email" ? "asc" : "desc");
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown className="size-2.5 inline ml-1 opacity-30" />;
    return sortDir === "asc" ? <ChevronUp className="size-2.5 inline ml-1" /> : <ChevronDown className="size-2.5 inline ml-1" />;
  };

  // Filter & sort logic
  const filteredUsers = useMemo(() => {
    if (!data?.users) return [];
    let result = data.users.filter((u) => {
      if (search.trim()) {
        const q = search.toLowerCase();
        if (!u.email.toLowerCase().includes(q) && !(u.role && u.role.toLowerCase().includes(q))) return false;
      }
      if (roleFilter !== "all" && u.role !== roleFilter) return false;
      if (statusFilter === "active" && !u.is_active) return false;
      if (statusFilter === "inactive" && u.is_active) return false;
      return true;
    });

    result.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "email": cmp = a.email.localeCompare(b.email); break;
        case "role": cmp = (a.role || "").localeCompare(b.role || ""); break;
        case "created_at": cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime(); break;
        case "conversation_count": cmp = a.conversation_count - b.conversation_count; break;
        case "message_count": cmp = a.message_count - b.message_count; break;
        case "total_tokens": cmp = a.total_tokens - b.total_tokens; break;
        case "total_cost": cmp = a.total_cost - b.total_cost; break;
        case "last_active": cmp = (a.last_active || "").localeCompare(b.last_active || ""); break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return result;
  }, [data?.users, search, roleFilter, statusFilter, sortField, sortDir]);

  const stats = useMemo(() => {
    if (!data?.users) return { total: 0, active: 0, withCost: 0, totalCost: 0 };
    return {
      total: data.users.length,
      active: data.users.filter(u => u.is_active).length,
      withCost: data.users.filter(u => u.total_cost > 0).length,
      totalCost: data.users.reduce((sum, u) => sum + u.total_cost, 0),
    };
  }, [data?.users]);

  // Role distribution for chart
  const roleDistribution = useMemo(() => {
    if (!data?.users) return [];
    const map = new Map<string, number>();
    for (const u of data.users) {
      const role = u.role || "unassigned";
      map.set(role, (map.get(role) || 0) + 1);
    }
    return Array.from(map.entries()).sort((a, b) => b[1] - a[1]);
  }, [data?.users]);

  // Export CSV
  const exportCSV = () => {
    if (!filteredUsers.length) return;
    const headers = ["Email", "Role", "Status", "Conversations", "Messages", "Tokens", "Cost", "Created", "Last Active"];
    const rows = filteredUsers.map((u) => [
      u.email,
      u.role || "N/A",
      u.is_active ? "Active" : "Inactive",
      u.conversation_count,
      u.message_count,
      u.total_tokens,
      u.total_cost.toFixed(4),
      formatDateShort(u.created_at),
      u.last_active ? formatDateShort(u.last_active) : "N/A",
    ]);
    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `users-export-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading && !data) return <LoadingSpinner message="LOADING USERS\u2026" fullScreen />;

  if (!token) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-slate-500">Authentication required. Please log in.</p>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in">
      {/* Modal */}
      {selectedUserId && (
        <UserDetailModal userId={selectedUserId} onClose={() => setSelectedUserId(null)} />
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white">User Management</h2>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            {stats.total} users &middot; {stats.active} active &middot; {formatCost(stats.totalCost)} total cost
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={exportCSV}
            disabled={filteredUsers.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700 transition-all disabled:opacity-30"
          >
            <Download className="size-3.5" />
            Export CSV
          </button>
          <button
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`size-3.5 ${refreshing ? "animate-spin" : ""}`} />
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-950/20 border border-rose-900/30 text-rose-300 text-xs animate-in fade-in-down">
          <AlertTriangle className="size-4 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
          <button onClick={() => fetchData(true)} className="ml-auto text-rose-400 hover:text-rose-300 underline">Retry</button>
        </div>
      )}

      {/* Stats + Role Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <div className="lg:col-span-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-white tabular-nums">{stats.total}</p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">Total Users</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-emerald-400 tabular-nums">{stats.active}</p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">Active</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-amber-400 tabular-nums">{stats.total - stats.active}</p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">Inactive</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-center hover:border-slate-700/60 transition-colors">
            <p className="text-xl font-bold text-white tabular-nums">{stats.withCost}</p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">With Activity</p>
          </div>
        </div>

        {/* Role Distribution Mini Chart */}
        {roleDistribution.length > 0 && (
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 hover:border-slate-700/60 transition-colors">
            <div className="flex items-center gap-1.5 mb-2">
              <BarChart3 className="size-3 text-slate-500" />
              <p className="text-[9px] text-slate-500 font-mono uppercase tracking-wider">By Role</p>
            </div>
            <div className="space-y-1.5">
              {roleDistribution.slice(0, 4).map(([role, count]) => {
                const maxCount = roleDistribution[0][1];
                const pct = (count / maxCount) * 100;
                return (
                  <div key={role} className="flex items-center gap-2">
                    <span className="text-[9px] text-slate-400 capitalize w-16 truncate">{role.replace("_", " ")}</span>
                    <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-violet-600 to-indigo-500 transition-all duration-500"
                        style={{ width: `${Math.max(8, pct)}%` }}
                      />
                    </div>
                    <span className="text-[9px] text-slate-500 font-mono w-5 text-right">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="size-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
          <input
            type="text"
            placeholder="Search by email or role..."
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

        {/* Role Filter Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowRoleDropdown(!showRoleDropdown)}
            onBlur={() => setTimeout(() => setShowRoleDropdown(false), 200)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:border-slate-700 transition-colors"
          >
            <Filter className="size-3.5 text-slate-500" />
            <span>Role: <span className="font-semibold text-slate-200 capitalize">{roleFilter === "all" ? "All" : roleFilter.replace("_", " ")}</span></span>
            <ChevronDown className="size-3 text-slate-500" />
          </button>
          {showRoleDropdown && (
            <div className="absolute top-full mt-1 right-0 w-44 rounded-lg border border-slate-800 bg-slate-950 shadow-xl shadow-black/30 z-20 overflow-hidden">
              {(["all", "super_admin", "admin", "security_admin", "manager", "employee"] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => { setRoleFilter(r); setShowRoleDropdown(false); }}
                  className={`w-full px-3 py-2 text-xs text-left transition-colors ${
                    roleFilter === r ? "bg-violet-600/20 text-violet-300" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                  }`}
                >
                  <span className="capitalize">{r === "all" ? "All Roles" : r.replace("_", " ")}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Status Filter Dropdown */}
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
            <div className="absolute top-full mt-1 right-0 w-36 rounded-lg border border-slate-800 bg-slate-950 shadow-xl shadow-black/30 z-20 overflow-hidden">
              {(["all", "active", "inactive"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => { setStatusFilter(s); setShowStatusDropdown(false); }}
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

        <span className="text-[10px] text-slate-600 font-mono">{filteredUsers.length} users</span>
      </div>

      {/* Users Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/40 backdrop-blur-sm overflow-hidden hover:border-slate-700/60 transition-all duration-300">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/50">
                <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono cursor-pointer hover:text-slate-300 select-none" onClick={() => handleSort("email")}>
                  User <SortIcon field="email" />
                </th>
                <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono cursor-pointer hover:text-slate-300 select-none" onClick={() => handleSort("role")}>
                  Role <SortIcon field="role" />
                </th>
                <th className="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Status</th>
                <th className="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono cursor-pointer hover:text-slate-300 select-none" onClick={() => handleSort("conversation_count")}>
                  Convs <SortIcon field="conversation_count" />
                </th>
                <th className="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono cursor-pointer hover:text-slate-300 select-none" onClick={() => handleSort("message_count")}>
                  Msgs <SortIcon field="message_count" />
                </th>
                <th className="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono cursor-pointer hover:text-slate-300 select-none" onClick={() => handleSort("total_tokens")}>
                  Tokens <SortIcon field="total_tokens" />
                </th>
                <th className="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono cursor-pointer hover:text-slate-300 select-none" onClick={() => handleSort("total_cost")}>
                  Cost <SortIcon field="total_cost" />
                </th>
                <th className="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono cursor-pointer hover:text-slate-300 select-none" onClick={() => handleSort("last_active")}>
                  Last Active <SortIcon field="last_active" />
                </th>
                <th className="text-center px-4 py-3 w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-12 text-center text-slate-600">
                    <div className="flex flex-col items-center gap-2">
                      <Users className="size-8 text-slate-700" />
                      <span>No users match your filters</span>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => {
                  const badge = roleBadge(u.role);
                  return (
                    <tr key={u.id} className="hover:bg-slate-900/30 transition-colors group">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className="size-8 rounded-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 flex items-center justify-center text-slate-400 flex-shrink-0">
                            <Users className="size-3.5" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-medium text-slate-200 truncate max-w-[180px]">{u.email}</p>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <Calendar className="size-3 text-slate-600" />
                              <p className="text-[10px] text-slate-600 font-mono">{formatDateShort(u.created_at)}</p>
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border ${badge.color}`}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`inline-flex items-center gap-1 text-[10px] font-mono ${u.is_active ? "text-emerald-400" : "text-slate-500"}`}>
                          {u.is_active ? <UserCheck className="size-3" /> : <UserX className="size-3" />}
                          {u.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center font-mono tabular-nums text-slate-300">{u.conversation_count}</td>
                      <td className="px-4 py-3 text-center font-mono tabular-nums text-slate-300">{u.message_count}</td>
                      <td className="px-4 py-3 text-center font-mono tabular-nums text-slate-300">{formatNumber(u.total_tokens)}</td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-400">{formatCost(u.total_cost)}</td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-500 text-[10px]">{u.last_active ? timeAgo(u.last_active) : "\u2014"}</td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => setSelectedUserId(u.id)}
                          className="p-1.5 rounded-lg text-slate-600 hover:text-violet-400 hover:bg-violet-950/20 opacity-0 group-hover:opacity-100 transition-all"
                          title="View user details"
                        >
                          <Eye className="size-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
