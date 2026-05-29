"use client";

import React from "react";

interface SkeletonTableProps {
  rows?: number;
  columns?: number;
  className?: string;
}

export default function SkeletonTable({ rows = 6, columns = 5, className = "" }: SkeletonTableProps) {
  const columnWidths = ["w-1/2", "w-3/4", "w-2/3", "w-1/3", "w-1/2"];
  const rowWidths = ["w-2/3", "w-1/2", "w-3/4", "w-1/3", "w-1/2", "w-2/3"];

  return (
    <div className={`rounded-xl border border-slate-800 bg-slate-950/40 backdrop-blur-sm overflow-hidden ${className}`} role="status" aria-label="Loading content">
      {/* Table header */}
      <div className="flex items-center gap-4 px-4 py-3 border-b border-slate-800 bg-slate-900/50">
        {Array.from({ length: columns }).map((_, i) => (
          <div
            key={`h-${i}`}
            className={`skeleton h-3 rounded ${columnWidths[i % columnWidths.length]}`}
            style={{ maxWidth: i === 0 ? "200px" : "120px" }}
          />
        ))}
      </div>

      {/* Table rows */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div
          key={`r-${rowIdx}`}
          className="flex items-center gap-4 px-4 py-3.5 border-b border-slate-800/50"
        >
          {Array.from({ length: columns }).map((_, colIdx) => {
            const isFirst = colIdx === 0;
            const widthClass = rowWidths[(rowIdx + colIdx) % rowWidths.length];
            return (
              <div key={`c-${rowIdx}-${colIdx}`} className="flex items-center gap-2" style={{ flex: isFirst ? 2 : 1 }}>
                {isFirst && (
                  <div className="skeleton size-8 rounded-full flex-shrink-0" />
                )}
                <div className={`skeleton h-3 rounded ${widthClass}`} style={{ maxWidth: isFirst ? "180px" : "80px" }} />
              </div>
            );
          })}
        </div>
      ))}

      <span className="sr-only">Loading, please wait...</span>
    </div>
  );
}
