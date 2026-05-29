"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  Activity,
  Shield,
  Fingerprint,
  Bot,
  LogOut,
  ChevronRight,
  Menu,
  X,
  Moon,
  Sun,
} from "lucide-react";
import { useChatStore } from "../../store/chatStore";
import { useThemeStore } from "../../store/useThemeStore";

const ADMIN_ROLES = ["super_admin", "admin", "security_admin"];

const NAV_ITEMS = [
  { href: "/admin", icon: LayoutDashboard, label: "Overview" },
  { href: "/admin/users", icon: Users, label: "Users" },
  { href: "/admin/conversations", icon: MessageSquare, label: "Conversations" },
  { href: "/admin/audit", icon: Activity, label: "Audit Logs" },
  { href: "/admin/security", icon: Shield, label: "Security" },
  { href: "/admin/dlp", icon: Fingerprint, label: "DLP Events" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useChatStore();
  const { theme, toggleTheme } = useThemeStore();
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  // Protect admin routes — redirect non-admin users to /chat
  useEffect(() => {
    if (user && !ADMIN_ROLES.includes(user.role ?? "")) {
      router.replace("/chat");
    }
  }, [user, router]);

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  // Show nothing while checking auth — prevents flash of admin content
  if (!user || !ADMIN_ROLES.includes(user.role ?? "")) {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="size-8 rounded-full border-2 border-[var(--primary)]/30 border-t-[var(--primary)] animate-spin" />
          <p className="text-xs text-[var(--text-tertiary)] font-mono">Verifying access...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] font-sans flex transition-colors duration-300">
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:sticky top-0 left-0 z-50 lg:z-30 h-screen w-60 flex-shrink-0 bg-[var(--bg-sidebar)] border-r border-[var(--border)] backdrop-blur-xl transition-transform duration-300 ease-in-out ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-4 border-b border-[var(--border)]">
            <div className="flex items-center gap-3">
              <div className="p-1.5 rounded-lg bg-gradient-to-tr from-violet-600 to-indigo-600 shadow-md flex-shrink-0">
                <Bot className="size-5 text-white" />
              </div>
              <div className="min-w-0">
                <h1 className="font-semibold text-sm text-[var(--text-primary)] truncate">Admin Console</h1>
                <p className="text-[10px] text-[var(--text-tertiary)] font-medium tracking-wide uppercase font-mono">Platform Control</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-3 space-y-1 overflow-y-auto custom-scrollbar">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href || (item.href !== "/admin" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all group ${
                    isActive
                      ? "bg-[var(--primary-light)] text-[var(--primary)] border border-[var(--primary)]/30"
                      : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] border border-transparent"
                  }`}
                  aria-current={isActive ? "page" : undefined}
                >
                  <item.icon className={`size-4 flex-shrink-0 ${isActive ? "text-[var(--primary)]" : "text-[var(--text-tertiary)] group-hover:text-[var(--text-secondary)]"}`} />
                  <span className="truncate">{item.label}</span>
                  {isActive && <ChevronRight className="size-3 ml-auto flex-shrink-0 text-[var(--primary)]" />}
                </Link>
              );
            })}
          </nav>

          {/* User section */}
          <div className="p-3 border-t border-[var(--border)]">
            <div className="flex items-center gap-2 px-2 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border)]">
              <div className="size-7 rounded-full bg-[var(--bg-hover)] border border-[var(--border)] flex items-center justify-center text-[var(--text-secondary)] flex-shrink-0">
                <Users className="size-3.5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[10px] font-medium text-[var(--text-primary)] truncate">{user?.email || "Admin"}</p>
                <p className="text-[8px] text-[var(--text-tertiary)] font-mono uppercase tracking-wider">Administrator</p>
              </div>
              <button
                onClick={handleLogout}
                className="p-1.5 rounded text-[var(--accent-rose)]/60 hover:text-[var(--accent-rose)] hover:bg-[var(--accent-rose)]/10 transition-all flex-shrink-0"
                title="Logout"
              >
                <LogOut className="size-3.5" />
              </button>
            </div>
          </div>

          {/* Theme Toggle */}
          <div className="px-3 pb-3">
            <button
              onClick={toggleTheme}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] border border-transparent transition-all group"
              title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {theme === "dark" ? (
                <Sun className="size-4 text-[var(--accent-amber)]" />
              ) : (
                <Moon className="size-4 text-[var(--primary)]" />
              )}
              <span className="truncate">{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Top bar (mobile) */}
        <div className="lg:hidden flex items-center gap-3 px-4 py-3 border-b border-[var(--border)] bg-[var(--bg-sidebar)]/80 backdrop-blur-md sticky top-0 z-30">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-[var(--bg-hover)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            <Menu className="size-5" />
          </button>
          <div className="flex items-center gap-2">
            <div className="p-1 rounded bg-gradient-to-tr from-violet-600 to-indigo-600">
              <Bot className="size-4 text-white" />
            </div>
            <span className="text-sm font-semibold text-[var(--text-primary)]">Admin Console</span>
          </div>
        </div>

        {/* Content - scrollable independently */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {children}
        </div>
      </div>
    </div>
  );
}
