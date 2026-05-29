"use client";

import React from "react";

interface BadgeProps {
  label: string | React.ReactNode;
  color?: string;
  size?: "sm" | "md";
}

export default function Badge({ label, color = "text-slate-400 bg-slate-900 border-slate-800", size = "sm" }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border ${color} ${size === "md" ? "px-2.5 py-1 text-xs" : ""}`}>
      {label}
    </span>
  );
}
