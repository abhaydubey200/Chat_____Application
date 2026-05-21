"use client";

import React from "react";
import { useChatStore } from "../store/chatStore";
import { Sparkles, Zap, Cpu } from "lucide-react";

export default function ModelSelector() {
  const { modelType, setModelType, isGenerating } = useChatStore();

  const models = [
    {
      id: "fast",
      name: "Fast Model",
      desc: "Speed-optimized responses",
      icon: Zap,
      color: "from-amber-500 to-orange-600",
      activeBorder: "border-orange-500/50 shadow-orange-500/10",
      bg: "bg-orange-500/10"
    },
    {
      id: "default",
      name: "Standard Model",
      desc: "Balanced speed & quality",
      icon: Sparkles,
      color: "from-indigo-500 to-purple-600",
      activeBorder: "border-indigo-500/50 shadow-indigo-500/10",
      bg: "bg-indigo-500/10"
    },
    {
      id: "reasoning",
      name: "Reasoning Model",
      desc: "Advanced logic & reasoning",
      icon: Cpu,
      color: "from-cyan-500 to-blue-600",
      activeBorder: "border-cyan-500/50 shadow-cyan-500/10",
      bg: "bg-cyan-500/10"
    }
  ];

  return (
    <div className="flex flex-col sm:flex-row gap-3 w-full max-w-2xl mx-auto p-1">
      {models.map((model) => {
        const Icon = model.icon;
        const isActive = modelType === model.id;
        
        return (
          <button
            key={model.id}
            disabled={isGenerating}
            onClick={() => setModelType(model.id)}
            className={`flex-1 flex items-start gap-3 p-3.5 rounded-xl border transition-all duration-300 text-left cursor-pointer
              ${isActive 
                ? `border-slate-700 bg-slate-800/80 text-white ${model.activeBorder} shadow-lg scale-[1.02]` 
                : "border-slate-800/60 bg-slate-900/40 text-slate-400 hover:border-slate-700 hover:text-slate-200"
              }
              ${isGenerating ? "opacity-50 cursor-not-allowed" : ""}
            `}
          >
            <div className={`p-2 rounded-lg bg-gradient-to-br ${model.color} text-white`}>
              <Icon className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-sm leading-tight flex items-center gap-1.5">
                {model.name}
                {isActive && (
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                )}
              </div>
              <span className="text-[11px] text-slate-500 truncate block mt-0.5">
                {model.desc}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
