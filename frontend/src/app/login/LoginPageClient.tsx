"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useChatStore } from "../../store/chatStore";
import { useToastStore } from "../../store/toastStore";
import { apiPost } from "../../utils/api";
import { Bot, Mail, Lock, AlertCircle, ArrowRight, Eye, EyeOff } from "lucide-react";
import Link from "next/link";

type TokenUser = {
  id: string;
  email: string;
  role?: string | null;
};

type TokenResponse = {
  access_token: string;
  token_type: string;
  user: TokenUser;
};

const getErrorMessage = (error: unknown, fallback: string) =>
  error instanceof Error && error.message ? error.message : fallback;

export default function LoginPageClient() {
  const { replace } = useRouter();
  const { login: setStoreLogin } = useChatStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [mounted, setMounted] = useState(false);
  const addToast = useToastStore((s) => s.addToast);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    setLoading(true);
    setErr("");

    try {
      const data = await apiPost<TokenResponse, { email: string; password: string }>(
        "/auth/login",
        { email, password }
      );
      setStoreLogin(data.access_token, data.user);

      addToast("Successfully signed in", "success");
      
      // Route admins to dashboard, regular users to chat
      const role = data.user?.role;
      if (role === "super_admin" || role === "admin" || role === "security_admin") {
        setTimeout(() => replace("/admin"), 300);
      } else {
        setTimeout(() => replace("/chat"), 300);
      }
    } catch (error: unknown) {
      setErr(getErrorMessage(error, "Invalid email or password"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col justify-center items-center bg-[var(--bg-primary)] text-[var(--text-primary)] min-h-screen px-4 transition-colors duration-300">
      {/* Background radial glowing effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 size-[500px] bg-[var(--primary)]/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 size-[300px] bg-[var(--primary)]/10 rounded-full blur-[100px] pointer-events-none" />

      <div className={`w-full max-w-md z-10 transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
        {/* Brand / Logo */}
        <div className="flex flex-col items-center mb-8 animate-in fade-in-up duration-500" style={{ animationFillMode: 'backwards' }}>
          <div className="p-3.5 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600            shadow-xl shadow-[var(--primary)]/20 mb-3 border border-[var(--primary)]/20">
            <Bot className="size-7 text-white animate-pulse" />
          </div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)] text-center">
            Welcome back to ChatHub
          </h1>
          <p className="text-xs text-[var(--text-tertiary)] font-medium tracking-wide mt-1 uppercase">
            Platform Orchestration Access
          </p>
        </div>

        {/* Login Glassmorphic Card */}
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)]/60 backdrop-blur-xl shadow-2xl p-6 md:p-8 animate-in fade-in-up duration-500" style={{ animationDelay: '100ms', animationFillMode: 'backwards' }}>
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Error Banner */}
            {err && (
              <div className="flex gap-2.5 p-3 rounded-xl bg-[var(--accent-rose)]/10 border border-[var(--accent-rose)]/20 text-[var(--accent-rose)] text-xs">
                <AlertCircle className="size-4 text-[var(--accent-rose)] flex-shrink-0 mt-0.5" />
                <span className="leading-relaxed">{err}</span>
              </div>
            )}

            {/* Email Field */}
            <div className="space-y-1.5">
              <label
                htmlFor="login-email"
                className="text-[10px] font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono"
              >
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[var(--text-tertiary)]">
                  <Mail className="size-4" />
                </div>
                <input
                  id="login-email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@domain.com"
                  className="w-full bg-[var(--bg-input)]/40 border border-[var(--border)] focus:border-[var(--border-light)] focus:outline-none rounded-xl py-3 pl-11 pr-4 text-sm text-[var(--text-primary)] placeholder-[var(--text-tertiary)] transition-all duration-300 focus-ring"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <label
                htmlFor="login-password"
                className="text-[10px] font-bold text-[var(--text-secondary)] tracking-wider uppercase font-mono"
              >
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[var(--text-tertiary)]">
                  <Lock className="size-4" />
                </div>
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-[var(--bg-input)]/40 border border-[var(--border)] focus:border-[var(--border-light)] focus:outline-none rounded-xl py-3 pl-11 pr-11 text-sm text-[var(--text-primary)] placeholder-[var(--text-tertiary)] transition-all duration-300 focus-ring"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors"
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </div>

            {/* Remember Me Checkbox */}
            <div className="flex items-center gap-2">
              <input
                id="remember-me"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded border-[var(--border)] bg-[var(--bg-input)] cursor-pointer accent-[var(--primary)]"
              />
              <label htmlFor="remember-me" className="text-xs text-[var(--text-secondary)] cursor-pointer hover:text-[var(--text-primary)] transition-colors">
                Remember me
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 transition-all duration-300 shadow-lg shadow-[var(--primary)]/10 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed mt-3 group"
            >
              {loading ? (
                <span className="size-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              ) : (
                <>
                  Access Platform
                  <ArrowRight className="size-4 group-hover:translate-x-0.5 transition-transform" />
                </>
              )}
            </button>
          </form>

          {/* Forgot Password Link */}
          <div className="mt-4 text-center">
            <button
              type="button"
              className="text-xs text-[var(--text-secondary)] hover:text-[var(--primary)] transition-colors"
            >
              Forgot your password?
            </button>
          </div>
        </div>

        {/* Footer info */}
        <p className="text-center text-xs text-[var(--text-tertiary)] mt-6 animate-in fade-in-up duration-500" style={{ animationDelay: '200ms', animationFillMode: 'backwards' }}>
          Don&apos;t have an account?{" "}
          <Link
            href="/signup"
            className="font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] transition-colors"
          >
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
