"use client";

import React from "react";
import { Bot, Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  message?: string;
  fullScreen?: boolean;
}

export default function LoadingSpinner({ message = "LOADING ADMIN ORCHESTRATION CONSOLE…", fullScreen = false }: LoadingSpinnerProps) {
  const content = (
    <div className="flex flex-col items-center gap-4">
      <div className="p-3.5 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 shadow-xl shadow-violet-600/10 animate-pulse">
        <Bot className="size-6 text-white" />
      </div>
      <Loader2 className="size-5 text-violet-400 animate-spin" />
      <div className="text-xs font-semibold tracking-wider text-slate-500 font-mono">{message}</div>
    </div>
  );

  if (fullScreen) {
    return (
      <div className="flex-1 flex flex-col justify-center items-center bg-[#090d16] text-slate-100 h-screen w-screen">
        {content}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center py-16">
      {content}
    </div>
  );
}
