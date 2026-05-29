"use client";

import React, { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { useChatStore } from "../../store/chatStore";
import { apiGet } from "../../utils/api";
import {
  Bot, Users, MessageSquare, FileText, DollarSign, Activity,
  Shield, AlertTriangle, TrendingUp, Clock, RefreshCw, UserCheck,
  Database, Key, Fingerprint, BarChart3, PieChart, Layers, Calendar, ChevronRight,
  Play, Pause, ExternalLink,
} from "lucide-react";
import StatCard from "../../components/admin/StatCard";
import MiniBarChart from "../../components/admin/MiniBarChart";
import StatusDot from "../../components/admin/StatusDot";
import Badge from "../../components/admin/Badge";
import LoadingSpinner from "../../components/admin/LoadingSpinner";
import { type DashboardData, type AuditItem, type SecurityItem, type DlpEventItem, type UserRow } from "../../components/admin/types";
import { formatNumber, formatCost, formatDateShort, formatDateFull, timeAgo, roleBadge, statusColor, severityColor } from "../../components/admin/helpers";

/* ─── Animated Counter ─── */
function AnimatedCounter({ value, suffix = "", duration = 800 }: { value: number; suffix?: string; duration?: number }) {
  const [display, setDisplay] = useState(0);
  const ref = useRef<number | null>(null);
  useEffect(() => {
    const start = performance.now();
    const from = 0;
    const to = value;
    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(from + (to - from) * eased));
      if (progress < 1) ref.current = requestAnimationFrame(animate);
    };
    ref.current = requestAnimationFrame(animate);
    return () => { if (ref.current) cancelAnimationFrame(ref.current); };
  }, [value, duration]);
  return <>{formatNumber(display)}{suffix}</>;
}

/* ─── Usage Trend Sparkline (inline SVG) ─── */
function Sparkline({ data, color = "#8b5cf6", height = 28 }: { data: number[]; color?: string; height?: number }) {
  if (data.length < 2) return null;
  const max = Math.max(...data, 1);
  const width = data.length * 6;
  const points = data.map((v, i) => `${i * 6 + 2},${height - (v / max) * (height - 4) - 2}`).join(" ");
  return (
    <svg width={width} height={height} className="w-full">
      <polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={points} />
    </svg>
  );
}

export default function AdminOverviewPage() {
  const router = useRouter();
  const { token } = useChatStore();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<string | null>(null);
  const autoRefInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchDashboard = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const result = await apiGet<DashboardData>("/admin/dashboard");
      setData(result);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load dashboard";
      setError(msg);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Auto-refresh interval
  useEffect(() => {
    if (autoRefresh) {
      autoRefInterval.current = setInterval(() => fetchDashboard(true), 30000);
    } else {
      if (autoRefInterval.current) clearInterval(autoRefInterval.current);
      autoRefInterval.current = null;
    }
    return () => { if (autoRefInterval.current) clearInterval(autoRefInterval.current); };
  }, [autoRefresh, fetchDashboard]);

  useEffect(() => {
    const init = async () => {
      const store = useChatStore.getState();
      if (!store.token) await store.initAuth();
      if (useChatStore.getState().token) fetchDashboard();
      else setLoading(false);
    };
    init();
  }, [fetchDashboard]);

  // Compute trend: compare today vs yesterday
  const trends = useMemo(() => {
    if (!data?.usage_over_time || data.usage_over_time.length < 2) return null;
    const days = data.usage_over_time;
    const today = days[days.length - 1];
    const yesterday = days[days.length - 2];
    if (!today || !yesterday) return null;
    const tokenChange = yesterday.tokens > 0 ? ((today.tokens - yesterday.tokens) / yesterday.tokens) * 100 : 0;
    const reqChange = yesterday.requests > 0 ? ((today.requests - yesterday.requests) / yesterday.requests) * 100 : 0;
    return { tokenChange, reqChange };
  }, [data]);

  if (loading && !data) {
    return <LoadingSpinner fullScreen />;
  }
  if (!token) {
    return (
      <div className="flex-1 flex flex-col justify-center items-center px-6 py-20 text-center">
        <div className="max-w-sm space-y-3">
          <div className="p-3 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 shadow-xl shadow-[var(--primary)]/20 mx-auto w-fit">
            <Shield className="size-6 text-white" />
          </div>
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">Authentication Required</h1>
          <p className="text-xs text-[var(--text-secondary)]">Please sign in to access the admin dashboard.</p>
        </div>
      </div>
    );
  }

  const ov = data?.overview;
  const td = data?.today;

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-8 animate-in fade-in">
      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-2.5 p-3 rounded-xl bg-rose-950/20 border border-rose-900/30 text-rose-300 text-xs animate-in fade-in-down">
          <AlertTriangle className="size-4 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
          <button onClick={() => fetchDashboard(true)} className="ml-auto text-rose-400 hover:text-rose-300 underline">Retry</button>
        </div>
      )}

      {data && ov && (
        <>
          {/* ─── Header Row ─── */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-[var(--text-primary)]">Platform Overview</h2>
              <p className="text-xs text-[var(--text-tertiary)] font-mono mt-0.5">
                Real-time system-wide analytics & monitoring
                {lastRefreshed && <span className="ml-2 text-[10px] text-slate-600">· last refresh {lastRefreshed}</span>}
              </p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {/* Auto-refresh toggle */}
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  autoRefresh
                    ? "text-emerald-400 border-emerald-900/30 bg-emerald-950/20"
                    : "text-slate-400 border-slate-800 hover:border-slate-700"
                }`}
                title={autoRefresh ? "Auto-refresh every 30s" : "Enable auto-refresh"}
              >
                {autoRefresh ? <Pause className="size-3.5" /> : <Play className="size-3.5" />}
                {autoRefresh ? "Auto" : "Manual"}
              </button>
              <button
                onClick={() => fetchDashboard(true)}
                disabled={refreshing}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700 transition-all disabled:opacity-50"
              >
                <RefreshCw className={`size-3.5 ${refreshing ? "animate-spin" : ""}`} />
                {refreshing ? "Refreshing..." : "Refresh"}
              </button>
              <button
                onClick={() => router.push("/admin/users")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-violet-400 hover:text-violet-300 border border-violet-900/30 hover:border-violet-700/50 transition-all"
              >
                <Users className="size-3.5" />
                Users <ChevronRight className="size-3" />
              </button>
            </div>
          </div>

          {/* ═══════════ TOP STATS with animated counters ═══════════ */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6 gap-3 md:gap-4 animate-in fade-in-up">
            <StatCard
              icon={Users} label="Total Users" value={<AnimatedCounter value={ov.total_users} />}
              subtext={`${ov.active_users} active`} color="bg-violet-600/20"
              onClick={() => router.push("/admin/users")}
            />
            <StatCard
              icon={MessageSquare} label="Conversations" value={<AnimatedCounter value={ov.total_conversations} />}
              subtext={td ? `+${td.conversations} today` : undefined} color="bg-indigo-600/20"
              onClick={() => router.push("/admin/conversations")}
            />
            <StatCard
              icon={FileText} label="Messages" value={<AnimatedCounter value={ov.total_messages} />}
              subtext={td ? `+${td.messages} today` : undefined} color="bg-blue-600/20"
            />
            <StatCard
              icon={TrendingUp} label="Tokens Used" value={<AnimatedCounter value={ov.total_tokens} />}
              subtext={td ? `+${formatNumber(td.tokens)} today` : undefined} color="bg-emerald-600/20"
            />
            <StatCard
              icon={DollarSign} label="Total Cost" value={`$${ov.total_cost.toFixed(2)}`} color="bg-amber-600/20"
            />
            <StatCard
              icon={BarChart3} label="Total Requests" value={<AnimatedCounter value={ov.total_requests} />}
              subtext={`${ov.failed_requests} failed`} color="bg-sky-600/20"
            />
          </div>

          {/* ═══════════ TODAY + HEALTH + AUTH + DLP ═══════════ */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 animate-in fade-in-up">
            {/* Today's Activity */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]/50 backdrop-blur-sm p-5 hover:border-slate-700/60 transition-all duration-300">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="size-4 text-violet-400" />
                <h3 className="text-xs font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono">Today&apos;s Activity</h3>
              </div>
              <div className="space-y-3">
                {[
                  { label: "New Conversations", value: td?.conversations ?? 0, icon: MessageSquare },
                  { label: "Messages Sent", value: td?.messages ?? 0, icon: FileText },
                  { label: "Tokens Consumed", value: formatNumber(td?.tokens ?? 0), icon: TrendingUp },
                  { label: "New Users", value: td?.new_users ?? 0, icon: UserCheck },
                  { label: "Errors", value: td?.errors ?? 0, icon: AlertTriangle },
                ].map((item, i) => (
                  <div key={i} className="flex items-center justify-between py-0.5 group">
                    <div className="flex items-center gap-2">
                      <item.icon className="size-3.5 text-slate-600 group-hover:text-slate-500 transition-colors" />
                      <span className="text-xs text-slate-400 group-hover:text-slate-300 transition-colors">{item.label}</span>
                    </div>
                    <span className={`text-sm font-bold tabular-nums transition-colors ${item.label === "Errors" && (item.value as number) > 0 ? "text-rose-400" : "text-white"}`}>
                      {typeof item.value === "number" ? <AnimatedCounter value={item.value} /> : item.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* System Health */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]/50 backdrop-blur-sm p-5 hover:border-slate-700/60 transition-all duration-300">
              <div className="flex items-center gap-2 mb-4">
                <Database className="size-4 text-violet-400" />
                <h3 className="text-xs font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono">System Health</h3>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Database className="size-3.5 text-slate-600" />
                    <span className="text-xs text-slate-400">Database</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <StatusDot status={data.health.database} />
                    <span className="text-xs font-medium capitalize text-slate-300">{data.health.database}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Organizations</span>
                  <span className="text-sm font-bold text-white tabular-nums">{data.health.total_organizations}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Total Requests</span>
                  <span className="text-sm font-bold text-white tabular-nums">{formatNumber(data.health.total_requests)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Failed Requests</span>
                  <span className={`text-sm font-bold tabular-nums ${ov.failed_requests > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                    {formatNumber(ov.failed_requests)}
                  </span>
                </div>
                {/* Error rate progress bar */}
                <div className="pt-1 border-t border-slate-800">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">Error Rate</span>
                    <span className="text-sm font-bold text-white tabular-nums">
                      {ov.total_requests > 0 ? `${((ov.failed_requests / ov.total_requests) * 100).toFixed(2)}%` : "0%"}
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full bg-gradient-to-r transition-all duration-700 ${
                        ov.failed_requests > 0 ? "from-rose-600 to-orange-500" : "from-emerald-500 to-teal-500"
                      }`}
                      style={{ width: `${ov.total_requests > 0 ? Math.min((ov.failed_requests / ov.total_requests) * 100, 100) : 0}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Auth Events */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]/50 backdrop-blur-sm p-5 hover:border-slate-700/60 transition-all duration-300">
              <div className="flex items-center gap-2 mb-4">
                <Key className="size-4 text-violet-400" />
                <h3 className="text-xs font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono">Auth Events (7d)</h3>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <UserCheck className="size-3.5 text-slate-600" />
                    <span className="text-xs text-slate-400">New Signups</span>
                  </div>
                  <span className="text-sm font-bold text-emerald-400 tabular-nums"><AnimatedCounter value={data.auth.recent_signups_7d} /></span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="size-3.5 text-slate-600" />
                    <span className="text-xs text-slate-400">Failed Logins</span>
                  </div>
                  <span className={`text-sm font-bold tabular-nums ${data.auth.failed_logins_7d > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                    <AnimatedCounter value={data.auth.failed_logins_7d} />
                  </span>
                </div>
                <div className="flex items-center justify-between py-1">
                  <span className="text-xs text-slate-400">Active Users</span>
                  <span className="text-sm font-bold text-white tabular-nums">{data.auth.active_users}/{data.auth.total_users}</span>
                </div>
                <div className="pt-1 border-t border-slate-800">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-slate-400">Activation Rate</span>
                    <span className="text-sm font-bold text-white tabular-nums">
                      {data.auth.total_users > 0 ? `${Math.round((data.auth.active_users / data.auth.total_users) * 100)}%` : "0%"}
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-violet-600 to-indigo-500 transition-all duration-700"
                      style={{ width: `${data.auth.total_users > 0 ? (data.auth.active_users / data.auth.total_users) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* DLP Summary */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]/50 backdrop-blur-sm p-5 hover:border-slate-700/60 transition-all duration-300">
              <div className="flex items-center gap-2 mb-4">
                <Fingerprint className="size-4 text-violet-400" />
                <h3 className="text-xs font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono">DLP Summary</h3>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Total Events</span>
                  <span className="text-sm font-bold text-white tabular-nums"><AnimatedCounter value={data.dlp.total} /></span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Blocked</span>
                  <span className={`text-sm font-bold tabular-nums ${data.dlp.blocked > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                    <AnimatedCounter value={data.dlp.blocked} />
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Pass Rate</span>
                  <span className="text-sm font-bold text-white tabular-nums">
                    {data.dlp.total > 0 ? `${Math.round((1 - data.dlp.blocked / data.dlp.total) * 100)}%` : "100%"}
                  </span>
                </div>
                {/* DLP pass rate bar */}
                <div className="pt-1 border-t border-slate-800">
                  <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full bg-gradient-to-r transition-all duration-700 ${
                        data.dlp.blocked > 0 ? "from-amber-500 to-orange-500" : "from-emerald-500 to-teal-500"
                      }`}
                      style={{ width: `${data.dlp.total > 0 ? Math.max(5, (1 - data.dlp.blocked / data.dlp.total) * 100) : 100}%` }}
                    />
                  </div>
                </div>
                {data.dlp.events.length > 0 && (
                  <div className="pt-2 border-t border-slate-800">
                    <p className="text-[10px] text-slate-600 font-mono mb-2">Latest Events</p>
                    {data.dlp.events.slice(0, 2).map((e) => (
                      <div key={e.id} className="flex items-center justify-between py-1">
                        <span className="text-[10px] text-slate-400 capitalize">{e.action}</span>
                        <span className="text-[10px] text-slate-600 font-mono">{timeAgo(e.created_at)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ═══════════ GROWTH + USAGE + CHARTS ═══════════ */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 animate-in fade-in-up">
            {/* Signup Growth */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]/50 backdrop-blur-sm p-5 hover:border-slate-700/60 transition-all duration-300">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <TrendingUp className="size-4 text-emerald-400" />
                  <h3 className="text-xs font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono">Signup Growth (30d)</h3>
                </div>
                <span className="text-[10px] text-slate-600 font-mono">
                  {data.growth.signups_30d.reduce((a, b) => a + b.count, 0)} total
                </span>
              </div>
              <MiniBarChart data={data.growth.signups_30d.map(d => d.count)} height={40} color="bg-emerald-500/60" />
              <div className="flex justify-between mt-1.5 text-[10px] text-slate-600 font-mono">
                {data.growth.signups_30d.filter((_, i) => i % 7 === 0 || i === data.growth.signups_30d.length - 1).map((d, i) => (
                  <span key={i}>{formatDateShort(d.date)}</span>
                ))}
              </div>
            </div>

            {/* Conversation Growth */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]/50 backdrop-blur-sm p-5 hover:border-slate-700/60 transition-all duration-300">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <MessageSquare className="size-4 text-indigo-400" />
                  <h3 className="text-xs font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono">Conversation Growth (30d)</h3>
                </div>
                <span className="text-[10px] text-slate-600 font-mono">
                  {data.growth.conversations_30d.reduce((a, b) => a + b.count, 0)} total
                </span>
              </div>
              <MiniBarChart data={data.growth.conversations_30d.map(d => d.count)} height={40} color="bg-indigo-500/60" />
              <div className="flex justify-between mt-1.5 text-[10px] text-slate-600 font-mono">
                {data.growth.conversations_30d.filter((_, i) => i % 7 === 0 || i === data.growth.conversations_30d.length - 1).map((d, i) => (
                  <span key={i}>{formatDateShort(d.date)}</span>
                ))}
              </div>
            </div>

            {/* Usage Trend */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]/50 backdrop-blur-sm p-5 hover:border-slate-700/60 transition-all duration-300">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <BarChart3 className="size-4 text-violet-400" />
                  <h3 className="text-xs font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono">Usage Trend (7d)</h3>
                </div>
                <span className="text-[10px] text-slate-600 font-mono">{data.usage_over_time.length} days</span>
              </div>
              <MiniBarChart data={data.usage_over_time.map(d => d.tokens)} height={40} />
              <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                <div className="p-2 rounded-lg bg-slate-900/50 border border-slate-800/50 hover:border-slate-700/60 transition-colors">
                  <p className="text-lg font-bold text-white tabular-nums">
                    {formatNumber(data.usage_over_time.reduce((a, b) => a + b.tokens, 0))}
                  </p>
                  <p className="text-[10px] text-slate-600 font-mono">Tokens</p>
                </div>
                <div className="p-2 rounded-lg bg-slate-900/50 border border-slate-800/50 hover:border-slate-700/60 transition-colors">
                  <p className="text-lg font-bold text-white tabular-nums">
                    {formatCost(data.usage_over_time.reduce((a, b) => a + b.cost, 0))}
                  </p>
                  <p className="text-[10px] text-slate-600 font-mono">Cost</p>
                </div>
                <div className="p-2 rounded-lg bg-slate-900/50 border border-slate-800/50 hover:border-slate-700/60 transition-colors">
                  <p className="text-lg font-bold text-white tabular-nums">
                    {formatNumber(data.usage_over_time.reduce((a, b) => a + b.requests, 0))}
                  </p>
                  <p className="text-[10px] text-slate-600 font-mono">Requests</p>
                </div>
              </div>
              {/* Trend indicators */}
              {trends && (
                <div className="mt-3 flex items-center gap-3 text-[10px] font-mono pt-2 border-t border-slate-800">
                  <span className="text-slate-600">vs yesterday:</span>
                  <span className={trends.tokenChange >= 0 ? "text-emerald-400" : "text-rose-400"}>
                    {trends.tokenChange >= 0 ? "↑" : "↓"} Tokens {Math.abs(trends.tokenChange).toFixed(1)}%
                  </span>
                  <span className={trends.reqChange >= 0 ? "text-emerald-400" : "text-rose-400"}>
                    {trends.reqChange >= 0 ? "↑" : "↓"} Reqs {Math.abs(trends.reqChange).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* ═══════════ MODEL + PROVIDER BREAKDOWN ═══════════ */}
          {data.model_breakdown.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-in fade-in-up">
              {/* Model Breakdown */}
              <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]/50 backdrop-blur-sm p-5 hover:border-slate-700/60 transition-all duration-300">
                <div className="flex items-center gap-2 mb-4">
                  <Layers className="size-4 text-violet-400" />
                  <h3 className="text-xs font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono">Model Breakdown</h3>
                </div>
                <div className="overflow-x-auto max-h-64 overflow-y-auto custom-scrollbar">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-slate-950/95">
                      <tr className="border-b border-slate-800">
                        <th className="text-left px-2 py-2 text-[10px] text-slate-600 font-mono">Provider</th>
                        <th className="text-left px-2 py-2 text-[10px] text-slate-600 font-mono">Model</th>
                        <th className="text-right px-2 py-2 text-[10px] text-slate-600 font-mono">Tokens</th>
                        <th className="text-right px-2 py-2 text-[10px] text-slate-600 font-mono">Cost</th>
                        <th className="text-right px-2 py-2 text-[10px] text-slate-600 font-mono">Req</th>
                        <th className="text-right px-2 py-2 text-[10px] text-slate-600 font-mono">Latency</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {data.model_breakdown.map((m, i) => (
                        <tr key={i} className="hover:bg-slate-900/30 transition-colors">
                          <td className="px-2 py-2 text-slate-400 capitalize">{m.provider}</td>
                          <td className="px-2 py-2 text-slate-300 font-mono text-[10px] truncate max-w-[140px]">{m.model}</td>
                          <td className="px-2 py-2 text-right font-mono text-slate-400">{formatNumber(m.tokens)}</td>
                          <td className="px-2 py-2 text-right font-mono text-slate-400">{formatCost(m.cost)}</td>
                          <td className="px-2 py-2 text-right font-mono text-slate-400">{m.requests}</td>
                          <td className="px-2 py-2 text-right font-mono text-slate-500">{m.avg_latency_ms ? `${m.avg_latency_ms}ms` : "\u2014"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Provider Cost Breakdown */}
              <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]/50 backdrop-blur-sm p-5 hover:border-slate-700/60 transition-all duration-300">
                <div className="flex items-center gap-2 mb-4">
                  <PieChart className="size-4 text-violet-400" />
                  <h3 className="text-xs font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono">Provider Cost Breakdown</h3>
                </div>
                {data.provider_breakdown.length === 0 ? (
                  <p className="text-xs text-slate-600 text-center py-8">No provider data yet</p>
                ) : (
                  <div className="space-y-4">
                    {data.provider_breakdown.map((p, i) => {
                      const maxCost = Math.max(...data.provider_breakdown.map(x => x.cost), 0.001);
                      const pct = (p.cost / maxCost) * 100;
                      const colors = ["from-violet-600 to-indigo-500", "from-emerald-500 to-teal-500", "from-amber-500 to-orange-500", "from-rose-500 to-pink-500"];
                      return (
                        <div key={i}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-slate-300 capitalize">{p.provider}</span>
                            <span className="text-[10px] text-slate-500 font-mono">{formatCost(p.cost)}</span>
                          </div>
                          <div className="h-2.5 rounded-full bg-slate-800 overflow-hidden">
                            <div
                              className={`h-full rounded-full bg-gradient-to-r ${colors[i % colors.length]} transition-all duration-700`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <div className="flex justify-between text-[10px] text-slate-600 font-mono mt-0.5">
                            <span>{formatNumber(p.tokens)} tokens</span>
                            <span>{p.requests} requests</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ═══════════ DAILY USAGE DETAILS ═══════════ */}
          {data.usage_over_time.length > 0 && (
            <div className="animate-in fade-in-up">
              <div className="flex items-center gap-2 mb-4">
                <Calendar className="size-4 text-violet-400" />
                <h2 className="text-xs font-bold text-slate-400 tracking-wider uppercase font-mono">Daily Usage Details</h2>
              </div>
              <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]/40 backdrop-blur-sm overflow-hidden hover:border-slate-700/60 transition-all duration-300">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-[var(--border)] bg-[var(--bg-muted)]/50">
                        <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Date</th>
                        <th className="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Tokens</th>
                        <th className="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Cost</th>
                        <th className="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Requests</th>
                        <th className="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase font-mono">Avg Latency</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {data.usage_over_time.map((d, i) => (
                        <tr key={i} className="hover:bg-slate-900/30 transition-colors">
                          <td className="px-4 py-3 text-slate-300 font-medium">{formatDateShort(d.date)}</td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-300">{formatNumber(d.tokens)}</td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-400">{formatCost(d.cost)}</td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-400">{d.requests}</td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-500">{d.avg_latency_ms ? `${d.avg_latency_ms}ms` : "\u2014"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ═══════════ RECENT ACTIVITY ═══════════ */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 animate-in fade-in-up">
            {/* Recent Audit */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]/50 backdrop-blur-sm p-5 hover:border-slate-700/60 transition-all duration-300">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Activity className="size-4 text-violet-400" />
                  <h3 className="text-xs font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono">Recent Audit</h3>
                </div>
                <button
                  onClick={() => router.push("/admin/audit")}
                  className="text-[10px] text-violet-400 hover:text-violet-300 font-mono transition-colors"
                >
                  View all &rarr;
                </button>
              </div>
              {data.recent_audit.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-6 text-center">
                  <Activity className="size-6 text-slate-700" />
                  <p className="text-xs text-slate-600">No audit logs yet</p>
                </div>
              ) : (
                <div className="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar">
                  {data.recent_audit.slice(0, 8).map((log) => (
                    <div key={log.id} className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-slate-900/30 transition-colors">
                      <div className="flex items-center gap-2 min-w-0">
                        <Activity className="size-3 text-[var(--text-tertiary)] flex-shrink-0" />
                        <span className="text-[10px] text-[var(--text-primary)] capitalize truncate">{log.event_type.replace(/_/g, " ")}</span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <Badge label={log.status} color={statusColor(log.status)} />
                        <span className="text-[10px] text-slate-600 font-mono">{timeAgo(log.created_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recent Security */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]/50 backdrop-blur-sm p-5 hover:border-slate-700/60 transition-all duration-300">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Shield className="size-4 text-violet-400" />
                  <h3 className="text-xs font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono">Recent Security</h3>
                </div>
                <button
                  onClick={() => router.push("/admin/security")}
                  className="text-[10px] text-violet-400 hover:text-violet-300 font-mono transition-colors"
                >
                  View all &rarr;
                </button>
              </div>
              {data.recent_security.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-6 text-center">
                  <Shield className="size-6 text-slate-700" />
                  <p className="text-xs text-slate-600">No security events</p>
                </div>
              ) : (
                <div className="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar">
                  {data.recent_security.slice(0, 8).map((event) => (
                    <div key={event.id} className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-slate-900/30 transition-colors">
                      <div className="flex items-center gap-2 min-w-0">
                        <Shield className="size-3 text-[var(--text-tertiary)] flex-shrink-0" />
                        <span className="text-[10px] text-[var(--text-primary)] capitalize truncate">{event.event_type.replace(/_/g, " ")}</span>
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <Badge label={event.severity} color={severityColor(event.severity)} />
                        <span className="text-[10px] text-slate-600 font-mono">{timeAgo(event.created_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recent DLP */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]/50 backdrop-blur-sm p-5 hover:border-slate-700/60 transition-all duration-300">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Fingerprint className="size-4 text-violet-400" />
                  <h3 className="text-xs font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono">Recent DLP</h3>
                </div>
                <button
                  onClick={() => router.push("/admin/dlp")}
                  className="text-[10px] text-violet-400 hover:text-violet-300 font-mono transition-colors"
                >
                  View all &rarr;
                </button>
              </div>
              {data.dlp.events.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-6 text-center">
                  <Fingerprint className="size-6 text-slate-700" />
                  <p className="text-xs text-slate-600">No DLP events</p>
                </div>
              ) : (
                <div className="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar">
                  {data.dlp.events.slice(0, 8).map((event) => (
                    <div key={event.id} className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-slate-900/30 transition-colors">
                      <div className="flex items-center gap-2 min-w-0">
                        <Fingerprint className="size-3 text-[var(--text-tertiary)] flex-shrink-0" />
                        <span className="text-[10px] text-[var(--text-primary)] capitalize truncate">{event.action}</span>
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <Badge
                          label={`${event.match_count} ${event.match_count === 1 ? "match" : "matches"}`}
                          color={event.action === "block" ? "text-rose-400 bg-rose-950/30 border-rose-900/30" : "text-yellow-400 bg-yellow-950/30 border-yellow-900/30"}
                        />
                        <span className="text-[10px] text-slate-600 font-mono">{timeAgo(event.created_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Footer */}
      <footer className="border-t border-[var(--border)] pt-4 pb-8 text-center animate-in fade-in">
        <div className="flex items-center justify-center gap-4 text-[10px] text-[var(--text-tertiary)] font-mono flex-wrap">
          <span>ChatHub Admin Console</span>
          <span className="hidden sm:inline">&middot;</span>
          <span className="hidden sm:inline">Platform Orchestration Dashboard</span>
          {data && (
            <>
              <span className="hidden sm:inline">&middot;</span>
              <span>{data.users.length} users &middot; {data.overview.total_conversations} conversations &middot; {formatCost(data.overview.total_cost)} total cost</span>
            </>
          )}
        </div>
      </footer>
    </div>
  );
}
