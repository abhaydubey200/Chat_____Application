"use client";

import React from "react";

interface StatCardProps {
  icon: React.ElementType;
  label: string;
  value: string | number | React.ReactNode;
  subtext?: string;
  color: string;
  trend?: { direction: "up" | "down"; text: string };
  onClick?: () => void;
}

export default function StatCard({ icon: Icon, label, value, subtext, color, trend, onClick }: StatCardProps) {
  const Comp = onClick ? "button" : "div";
  return (
    <Comp
      onClick={onClick}
      className={`rounded-xl border border-slate-800 bg-slate-950/60 backdrop-blur-sm p-4 md:p-5 hover:border-slate-700/60 transition-all duration-300 group ${onClick ? "cursor-pointer text-left w-full" : ""}`}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1.5 flex-1 min-w-0">
          <p className="text-[10px] font-bold text-slate-500 tracking-wider uppercase font-mono">{label}</p>
          <p className="text-2xl md:text-3xl font-bold text-white tracking-tight tabular-nums truncate">{value}</p>
          <div className="flex items-center gap-2">
            {subtext && <p className="text-[10px] text-slate-600 font-mono truncate">{subtext}</p>}
            {trend && (
              <span className={`text-[10px] font-mono ${trend.direction === "up" ? "text-emerald-500" : "text-rose-500"}`}>
                {trend.direction === "up" ? "↑" : "↓"} {trend.text}
              </span>
            )}
          </div>
        </div>
        <div className={`p-2.5 rounded-xl ${color} transition-transform group-hover:scale-110 duration-300 flex-shrink-0`}>
          <Icon className="size-5 text-white" />
        </div>
      </div>
    </Comp>
  );
}
