"use client";

import { useEffect, useRef } from "react";
import { useThemeStore } from "../store/useThemeStore";

export default function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useThemeStore((s) => s.theme);
  const initialized = useRef(false);

  useEffect(() => {
    const root = document.documentElement;

    // Apply theme class
    root.classList.toggle("dark", theme === "dark");

    // Trigger smooth transition on subsequent theme changes (skip initial paint)
    if (initialized.current) {
      root.classList.add("theme-transition");
      const timer = setTimeout(() => root.classList.remove("theme-transition"), 400);
      return () => clearTimeout(timer);
    }

    initialized.current = true;
  }, [theme]);

  return <>{children}</>;
}
