"use client";

import React from "react";

interface MiniBarChartProps {
  data: number[];
  height?: number;
  color?: string;
}

export default function MiniBarChart({ data, height = 32, color = "bg-violet-500/60" }: MiniBarChartProps) {
  if (data.length === 0) return null;
  const max = Math.max(...data, 1);
  return (
    <div className="flex items-end gap-[2px]" style={{ height }}>
      {data.map((v, i) => (
        <div
          key={i}
          className={`w-full rounded-[1px] ${color} hover:opacity-80 transition-opacity`}
          style={{ height: `${(v / max) * 100}%`, minHeight: v > 0 ? 2 : 0 }}
        />
      ))}
    </div>
  );
}
