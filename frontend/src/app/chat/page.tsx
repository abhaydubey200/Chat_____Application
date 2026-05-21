"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useChatStore } from "../../store/chatStore";
import ChatSidebar from "../../components/ChatSidebar";
import ChatWindow from "../../components/ChatWindow";
import { Bot } from "lucide-react";

export default function ChatDashboardPage() {
  const router = useRouter();
  const { initAuth } = useChatStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const authorize = async () => {
      await initAuth();
      const currentToken = useChatStore.getState().token;
      
      if (!currentToken) {
        router.replace("/login");
      } else {
        setLoading(false);
      }
    };

    authorize();
  }, [router, initAuth]);

  if (loading) {
    return (
      <div className="flex-1 flex flex-col justify-center items-center bg-[#090d16] text-slate-100 h-screen w-screen">
        <div className="flex flex-col items-center gap-4">
          <div className="p-3.5 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 shadow-xl shadow-violet-600/10 animate-pulse">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div className="text-xs font-semibold tracking-wider text-slate-500 font-mono">
            ESTABLISHING ORCHESTRATION CONSOLE...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-row h-screen w-screen overflow-hidden bg-[#090d16] text-slate-100 font-sans">
      {/* Sidebar navigation */}
      <ChatSidebar />

      {/* Main chat window container */}
      <main className="flex-1 h-full min-w-0 flex flex-col relative bg-[#0d1220]/50 border-l border-slate-900">
        <ChatWindow />
      </main>
    </div>
  );
}
