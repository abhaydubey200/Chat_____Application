// ═══════════════════════════════════════════════════════════════
// ADMIN DASHBOARD — Shared Helpers & UI Utilities
// ═══════════════════════════════════════════════════════════════

export const formatNumber = (n: number): string => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
};

export const formatCost = (n: number): string => {
  if (n < 0.001) return `$${n.toFixed(6)}`;
  if (n < 0.01) return `$${n.toFixed(5)}`;
  return `$${n.toFixed(4)}`;
};

export const formatDate = (iso: string): string => {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
};

export const formatDateShort = (iso: string): string => {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
};

export const formatDateFull = (iso: string): string => {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
};

export const timeAgo = (iso: string): string => {
  try {
    const now = Date.now();
    const then = new Date(iso).getTime();
    const diffMs = now - then;
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}d ago`;
    return formatDateShort(iso);
  } catch {
    return iso;
  }
};

// ═══════════════════════════════════════════════════════════════
// BADGE & COLOR HELPERS
// ═══════════════════════════════════════════════════════════════

export const severityColor = (s: string): string => {
  switch (s) {
    case "critical": return "text-rose-400 bg-rose-950/30 border-rose-900/30";
    case "high": return "text-orange-400 bg-orange-950/30 border-orange-900/30";
    case "medium": return "text-yellow-400 bg-yellow-950/30 border-yellow-900/30";
    case "low": return "text-slate-400 bg-slate-900 border-slate-800";
    default: return "text-slate-400 bg-slate-900 border-slate-800";
  }
};

export const statusColor = (s: string): string => {
  switch (s) {
    case "success": return "text-emerald-400 bg-emerald-950/30 border-emerald-900/30";
    case "failure": case "error": return "text-rose-400 bg-rose-950/30 border-rose-900/30";
    case "open": return "text-yellow-400 bg-yellow-950/30 border-yellow-900/30";
    case "resolved": case "closed": return "text-slate-400 bg-slate-900 border-slate-800";
    default: return "text-slate-400 bg-slate-900 border-slate-800";
  }
};

export const roleBadge = (role: string | null): { label: string; color: string } => {
  switch (role) {
    case "super_admin": return { label: "Super Admin", color: "text-purple-400 bg-purple-950/30 border-purple-900/30" };
    case "admin": return { label: "Admin", color: "text-violet-400 bg-violet-950/30 border-violet-900/30" };
    case "security_admin": return { label: "Security", color: "text-cyan-400 bg-cyan-950/30 border-cyan-900/30" };
    case "manager": return { label: "Manager", color: "text-blue-400 bg-blue-950/30 border-blue-900/30" };
    case "employee": return { label: "Employee", color: "text-slate-400 bg-slate-900 border-slate-800" };
    default: return { label: role || "N/A", color: "text-slate-500 bg-slate-900 border-slate-800" };
  }
};

export const statusDot = (status: string): string => {
  const colors: Record<string, string> = {
    healthy: "bg-emerald-500",
    degraded: "bg-amber-500",
    error: "bg-rose-500",
    success: "bg-emerald-500",
    failure: "bg-rose-500",
    open: "bg-yellow-500",
    resolved: "bg-slate-500",
    running: "bg-blue-500",
  };
  return colors[status] || "bg-slate-600";
};
