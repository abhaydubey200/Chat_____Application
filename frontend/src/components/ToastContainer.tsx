"use client";

import React from "react";
import { useToastStore } from "../store/toastStore";
import { CheckCircle, AlertCircle, Info, AlertTriangle, X } from "lucide-react";

const iconMap = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
  warning: AlertTriangle,
};

const colorMap = {
  success:
    "border-emerald-800/40 bg-emerald-950/40 text-emerald-300 shadow-emerald-900/10",
  error:
    "border-rose-800/40 bg-rose-950/40 text-rose-300 shadow-rose-900/10",
  info:
    "border-indigo-800/40 bg-indigo-950/40 text-indigo-300 shadow-indigo-900/10",
  warning:
    "border-amber-800/40 bg-amber-950/40 text-amber-300 shadow-amber-900/10",
};

export default function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[200] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => {
        const Icon = iconMap[toast.type];
        return (
          <div
            key={toast.id}
            className={`toast-in pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl border backdrop-blur-xl shadow-xl ${colorMap[toast.type]}`}
            role="alert"
          >
            <Icon className="size-4 mt-0.5 flex-shrink-0" />
            <p className="text-xs font-medium leading-relaxed flex-1">
              {toast.message}
            </p>
            <button
              onClick={() => removeToast(toast.id)}
              className="p-0.5 rounded hover:bg-white/10 transition-colors flex-shrink-0 opacity-60 hover:opacity-100"
              aria-label="Dismiss notification"
            >
              <X className="size-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
