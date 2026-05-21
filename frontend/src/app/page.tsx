"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useChatStore } from "../store/chatStore";
import { Bot } from "lucide-react";

export default function RootPage() {
  const router = useRouter();
  const { initAuth } = useChatStore();

  useEffect(() => {
    const checkAuth = async () => {
      await initAuth();
      // If we finished auth check
      const currentToken = useChatStore.getState().token;
      if (currentToken) {
        router.replace("/chat");
      } else {
        router.replace("/login");
      }
    };

    checkAuth();
  }, [router, initAuth]);

  return (
    <div className="flex-1 flex flex-col justify-center items-center bg-[#090d16] text-slate-100">
      <div className="flex flex-col items-center gap-4">
        <div className="p-4 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 shadow-xl shadow-violet-600/10 animate-pulse">
          <Bot className="w-8 h-8 text-white" />
        </div>
        <div className="text-sm font-semibold tracking-wider text-slate-400 font-mono">
          LOADING SESSION...
        </div>
      </div>
    </div>
  );
}
