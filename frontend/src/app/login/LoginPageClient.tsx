"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useChatStore } from "../../store/chatStore";
import { apiPost } from "../../utils/api";
import { Bot, Mail, Lock, AlertCircle, ArrowRight, Eye, EyeOff } from "lucide-react";
import Link from "next/link";

type TokenResponse = {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
  };
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
      replace("/chat");
    } catch (error: unknown) {
      setErr(getErrorMessage(error, "Invalid email or password"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col justify-center items-center bg-[#090d16] text-slate-100 min-h-screen px-4">
      {/* Background radial glowing effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 size-[500px] bg-violet-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 size-[300px] bg-indigo-600/10 rounded-full blur-[100px] pointer-events-none" />

      <div className="w-full max-w-md z-10">
        {/* Brand / Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="p-3.5 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 shadow-xl shadow-violet-600/20 mb-3 border border-violet-500/20">
            <Bot className="size-7 text-white animate-pulse" />
          </div>
          <h1 className="text-2xl font-semibold text-white text-center">
            Welcome back to Dushman AI
          </h1>
          <p className="text-xs text-slate-500 font-medium tracking-wide mt-1 uppercase">
            Platform Orchestration Access
          </p>
        </div>

        {/* Login Glassmorphic Card */}
        <div className="rounded-2xl border border-slate-800/80 bg-slate-950/60 backdrop-blur-xl shadow-2xl p-6 md:p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Error Banner */}
            {err && (
              <div className="flex gap-2.5 p-3 rounded-xl bg-rose-950/20 border border-rose-900/30 text-rose-300 text-xs">
                <AlertCircle className="size-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <span className="leading-relaxed">{err}</span>
              </div>
            )}

            {/* Email Field */}
            <div className="space-y-1.5">
              <label
                htmlFor="login-email"
                className="text-[10px] font-bold text-slate-400 tracking-wider uppercase font-mono"
              >
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
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
                  className="w-full bg-slate-900/40 border border-slate-800 focus:border-slate-700/80 focus:outline-none rounded-xl py-3 pl-11 pr-4 text-sm text-slate-200 placeholder-slate-600 transition-all duration-300"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <label
                htmlFor="login-password"
                className="text-[10px] font-bold text-slate-400 tracking-wider uppercase font-mono"
              >
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="size-4" />
                </div>
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-900/40 border border-slate-800 focus:border-slate-700/80 focus:outline-none rounded-xl py-3 pl-11 pr-11 text-sm text-slate-200 placeholder-slate-600 transition-all duration-300"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-400 transition-colors"
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
                className="w-4 h-4 rounded border-slate-700 bg-slate-900/40 cursor-pointer accent-violet-500"
              />
              <label htmlFor="remember-me" className="text-xs text-slate-400 cursor-pointer hover:text-slate-300 transition-colors">
                Remember me
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 transition-all duration-300 shadow-lg shadow-indigo-600/10 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed mt-3 group"
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
              className="text-xs text-slate-400 hover:text-violet-400 transition-colors"
            >
              Forgot your password?
            </button>
          </div>
        </div>

        {/* Footer info */}
        <p className="text-center text-xs text-slate-500 mt-6">
          Don&apos;t have an account?{" "}
          <Link
            href="/signup"
            className="font-semibold text-violet-400 hover:text-violet-300 transition-colors"
          >
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
