"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useChatStore } from "../../store/chatStore";
import ChatSidebar from "../../components/ChatSidebar";
import ChatWindow from "../../components/ChatWindow";
import { Bot, Menu, X } from "lucide-react";

export default function ChatDashboardClient() {
  const { initAuth, token } = useChatStore();
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const authorize = async () => {
      await initAuth();
      if (isMounted) {
        setLoading(false);
      }
    };

    authorize();

    return () => {
      isMounted = false;
    };
  }, [initAuth]);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, []);

  const closeSidebar = useCallback(() => {
    setSidebarOpen(false);
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex flex-col justify-center items-center bg-[var(--bg-primary)] text-[var(--text-primary)] h-screen w-screen">
        <div className="flex flex-col items-center gap-4">
          <div className="p-3.5 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 shadow-xl shadow-[var(--primary)]/10 animate-pulse">
            <Bot className="size-6 text-white" />
          </div>
          <div className="text-xs font-semibold tracking-wider text-[var(--text-tertiary)] font-mono">
            ESTABLISHING ORCHESTRATION CONSOLE…
          </div>
        </div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="flex-1 flex flex-col justify-center items-center bg-[var(--bg-primary)] text-[var(--text-primary)] h-screen w-screen px-6 text-center">
        <div className="max-w-sm space-y-3">
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">Session expired</h1>
          <p className="text-xs text-[var(--text-secondary)]">
            Your session is no longer valid. Please sign in to continue.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-lg bg-[var(--primary)] px-4 py-2 text-xs font-semibold text-white hover:bg-[var(--primary-hover)] transition-colors"
          >
            Go to login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-row h-screen w-screen overflow-hidden bg-[var(--bg-primary)] text-[var(--text-primary)] font-sans">
      {/* Mobile overlay backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={closeSidebar}
        />
      )}

      {/* Sidebar - responsive: overlay on mobile, persistent on desktop */}
      <div
        className={`
          fixed lg:relative z-30 lg:z-auto h-full transition-transform duration-300 ease-in-out
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
      >
        <ChatSidebar onClose={closeSidebar} />
      </div>

      {/* Mobile sidebar toggle */}
      <button
        onClick={toggleSidebar}
        className="fixed top-4 left-4 z-40 p-2 rounded-xl border border-[var(--border)] bg-[var(--bg-sidebar)]/80 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] backdrop-blur transition-all duration-200 lg:hidden shadow-lg"
      >
        {sidebarOpen ? <X className="size-4" /> : <Menu className="size-4" />}
      </button>

      {/* Main chat window container */}
      <main className="flex-1 h-full min-w-0 flex flex-col relative bg-[var(--bg-secondary)]/50 border-l border-[var(--border)]">
        <ChatWindow onToggleSidebar={toggleSidebar} />
      </main>
    </div>
  );
}
