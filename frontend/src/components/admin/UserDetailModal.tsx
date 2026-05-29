"use client";

import React, { useEffect, useState } from "react";
import {
  Users, MessageSquare, X, Loader2, AlertTriangle, Activity,
} from "lucide-react";
import { apiGet } from "../../utils/api";
import { UserDetailData } from "./types";
import { formatNumber, formatCost, formatDateShort, formatDateFull, timeAgo, roleBadge, statusColor } from "./helpers";
import MiniBarChart from "./MiniBarChart";

interface UserDetailModalProps {
  userId: string;
  onClose: () => void;
}

export default function UserDetailModal({ userId, onClose }: UserDetailModalProps) {
  const [data, setData] = useState<UserDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUserDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await apiGet<UserDetailData>(`/admin/users/${userId}`);
        setData(result);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load user detail");
      } finally {
        setLoading(false);
      }
    };
    fetchUserDetail();
  }, [userId]);

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-12 pb-8 px-4 overflow-y-auto">
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-4xl rounded-2xl border border-slate-800 bg-slate-950/95 backdrop-blur-xl shadow-2xl shadow-black/50 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="size-10 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center">
              <Users className="size-5 text-white" />
            </div>
            <div>
              {loading ? (
                <p className="text-sm font-semibold text-slate-300">Loading...</p>
              ) : (
                <>
                  <p className="text-sm font-semibold text-white">{data?.user.email || "User Detail"}</p>
                  <p className="text-[10px] text-slate-500 font-mono">ID: {userId.substring(0, 8)}...</p>
                </>
              )}
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-800 text-slate-500 hover:text-white transition-colors">
            <X className="size-5" />
          </button>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="size-8 text-violet-400 animate-spin" />
          </div>
        )}

        {error && (
          <div className="p-6">
            <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-950/20 border border-rose-900/30 text-rose-300 text-xs">
              <AlertTriangle className="size-4" />
              {error}
            </div>
          </div>
        )}

        {data && !loading && (
          <div className="p-5 space-y-6 max-h-[70vh] overflow-y-auto custom-scrollbar">
            {/* User Info */}
            <div className="flex items-center gap-3 pb-3 border-b border-slate-800">
              {data.user.role && (
                <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold border ${roleBadge(data.user.role).color}`}>
                  {roleBadge(data.user.role).label}
                </span>
              )}
              <span className="text-[10px] text-slate-600 font-mono">Joined {formatDateFull(data.user.created_at)}</span>
              <span className={`text-[10px] font-mono ${data.user.is_active ? "text-emerald-400" : "text-rose-400"}`}>
                {data.user.is_active ? "Active" : "Inactive"}
              </span>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "Conversations", value: data.stats.total_conversations },
                { label: "Requests", value: data.stats.total_requests },
                { label: "Tokens", value: formatNumber(data.stats.total_tokens) },
                { label: "Cost", value: formatCost(data.stats.total_cost) },
              ].map((stat, i) => (
                <div key={i} className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 text-center hover:border-slate-700/60 transition-colors">
                  <p className="text-lg font-bold text-white tabular-nums">{stat.value}</p>
                  <p className="text-[10px] text-slate-500 font-mono mt-0.5">{stat.label}</p>
                </div>
              ))}
            </div>

            {/* Usage History */}
            {data.usage_history.length > 0 && (
              <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-4">
                <h4 className="text-[10px] font-bold text-slate-500 tracking-wider uppercase font-mono mb-3">Usage History (7 Days)</h4>
                <MiniBarChart data={data.usage_history.map(d => d.tokens)} height={36} />
                <div className="flex justify-between mt-1.5 text-[10px] text-slate-600 font-mono">
                  {data.usage_history.map((d, i) => (
                    <span key={i}>{formatDateShort(d.date)}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Conversations */}
            {data.conversations.items.length > 0 && (
              <div>
                <h4 className="text-[10px] font-bold text-slate-500 tracking-wider uppercase font-mono mb-2">
                  Recent Conversations ({data.conversations.total} total)
                </h4>
                <div className="space-y-1 max-h-48 overflow-y-auto custom-scrollbar">
                  {data.conversations.items.slice(0, 8).map((conv) => (
                    <div key={conv.id} className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-900/30 hover:bg-slate-900/50 transition-colors">
                      <div className="flex items-center gap-2 min-w-0">
                        <MessageSquare className="size-3 text-slate-600 flex-shrink-0" />
                        <span className="text-xs text-slate-300 truncate">{conv.title}</span>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0">
                        <span className="text-[10px] text-slate-600 font-mono">{conv.message_count} msgs</span>
                        <span className="text-[10px] text-slate-600 font-mono">{timeAgo(conv.updated_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Model Usage */}
            {data.model_usage.length > 0 && (
              <div>
                <h4 className="text-[10px] font-bold text-slate-500 tracking-wider uppercase font-mono mb-2">Model Usage Breakdown</h4>
                <div className="overflow-x-auto rounded-lg border border-slate-800">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-900/50">
                        <th className="text-left px-3 py-2 text-[10px] text-slate-600 font-mono">Provider</th>
                        <th className="text-left px-3 py-2 text-[10px] text-slate-600 font-mono">Model</th>
                        <th className="text-right px-3 py-2 text-[10px] text-slate-600 font-mono">Tokens</th>
                        <th className="text-right px-3 py-2 text-[10px] text-slate-600 font-mono">Cost</th>
                        <th className="text-right px-3 py-2 text-[10px] text-slate-600 font-mono">Requests</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {data.model_usage.map((m, i) => (
                        <tr key={i} className="hover:bg-slate-900/30">
                          <td className="px-3 py-2 text-slate-400 capitalize">{m.provider}</td>
                          <td className="px-3 py-2 text-slate-300 font-mono text-[10px]">{m.model}</td>
                          <td className="px-3 py-2 text-right font-mono text-slate-400">{formatNumber(m.tokens)}</td>
                          <td className="px-3 py-2 text-right font-mono text-slate-400">{formatCost(m.cost)}</td>
                          <td className="px-3 py-2 text-right font-mono text-slate-400">{m.requests}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Recent Audit */}
            {data.recent_audit.length > 0 && (
              <div>
                <h4 className="text-[10px] font-bold text-slate-500 tracking-wider uppercase font-mono mb-2">Recent Activity</h4>
                <div className="space-y-1 max-h-40 overflow-y-auto custom-scrollbar">
                  {data.recent_audit.slice(0, 8).map((log) => (
                    <div key={log.id} className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-900/30">
                      <div className="flex items-center gap-2">
                        <Activity className="size-3 text-slate-600" />
                        <span className="text-xs text-slate-400 capitalize">{log.event_type.replace(/_/g, " ")}</span>
                        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] border ${statusColor(log.status)}`}>{log.status}</span>
                      </div>
                      <span className="text-[10px] text-slate-600 font-mono">{timeAgo(log.created_at)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="border-t border-slate-800 p-3 flex justify-end">
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700 transition-all">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
