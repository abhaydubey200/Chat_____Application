"use client";

import { create } from "zustand";

type Theme = "dark" | "light";

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const getInitialTheme = (): Theme => {
  if (typeof window === "undefined") return "dark";
  const stored = localStorage.getItem("chathub-theme") as Theme | null;
  if (stored === "light" || stored === "dark") return stored;
  return "dark";
};

export const useThemeStore = create<ThemeState>((set) => ({
  theme: getInitialTheme(),

  toggleTheme: () =>
    set((state) => {
      const next = state.theme === "dark" ? "light" : "dark";
      localStorage.setItem("chathub-theme", next);
      return { theme: next };
    }),

  setTheme: (theme) => {
    localStorage.setItem("chathub-theme", theme);
    set({ theme });
  },
}));
