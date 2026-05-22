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
      <div className="flex-1 flex flex-col justify-center items-center bg-[#090d16] text-slate-100 h-screen w-screen">
        <div className="flex flex-col items-center gap-4">
          <div className="p-3.5 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 shadow-xl shadow-violet-600/10 animate-pulse">
            <Bot className="size-6 text-white" />
          </div>
          <div className="text-xs font-semibold tracking-wider text-slate-500 font-mono">
            ESTABLISHING ORCHESTRATION CONSOLE…
          </div>
        </div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="flex-1 flex flex-col justify-center items-center bg-[#090d16] text-slate-100 h-screen w-screen px-6 text-center">
        <div className="max-w-sm space-y-3">
          <h1 className="text-lg font-semibold text-white">Session expired</h1>
          <p className="text-xs text-slate-400">
            Your session is no longer valid. Please sign in to continue.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-lg bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-500 transition-colors"
          >
            Go to login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-row h-screen w-screen overflow-hidden bg-[#090d16] text-slate-100 font-sans">
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
        className="fixed top-4 left-4 z-40 p-2 rounded-xl border border-slate-800 bg-slate-950/80 text-slate-400 hover:text-white hover:bg-slate-900 backdrop-blur transition-all duration-200 lg:hidden shadow-lg"
      >
        {sidebarOpen ? <X className="size-4" /> : <Menu className="size-4" />}
      </button>

      {/* Main chat window container */}
      <main className="flex-1 h-full min-w-0 flex flex-col relative bg-[#0d1220]/50 border-l border-slate-900">
        <ChatWindow onToggleSidebar={toggleSidebar} />
      </main>
    </div>
  );
}
