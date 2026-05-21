"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useChatStore } from "../../store/chatStore";
import { apiPost } from "../../utils/api";
import { Bot, Mail, Lock, AlertCircle, ArrowRight } from "lucide-react";
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

export default function SignupPage() {
  const router = useRouter();
  const { signup: setStoreSignup, token } = useChatStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  // Redirect to chat if already logged in
  useEffect(() => {
    if (token) {
      router.replace("/chat");
    }
  }, [token, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || !confirmPassword) return;

    if (password.length < 6) {
      setErr("Password must be at least 6 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setErr("Passwords do not match.");
      return;
    }

    setLoading(true);
    setErr("");

    try {
      // 1. Post to signup
      await apiPost("/auth/signup", { email, password });
      
      // 2. Automatically log them in to fetch JWT token
      const loginData = await apiPost<TokenResponse, { email: string; password: string }>(
        "/auth/login",
        { email, password }
      );
      
      setStoreSignup(loginData.access_token, loginData.user);
      router.replace("/chat");
    } catch (err: unknown) {
      setErr(getErrorMessage(err, "Failed to create account. Email may already be in use."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col justify-center items-center bg-[#090d16] text-slate-100 min-h-screen px-4">
      {/* Background radial glowing effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-violet-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 w-[300px] h-[300px] bg-indigo-600/10 rounded-full blur-[100px] pointer-events-none" />

      <div className="w-full max-w-md z-10">
        {/* Brand / Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="p-3.5 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 shadow-xl shadow-violet-600/20 mb-3 border border-violet-500/20">
            <Bot className="w-7 h-7 text-white animate-pulse" />
          </div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            Create your account
          </h1>
          <p className="text-xs text-slate-500 font-medium tracking-wide mt-1 uppercase">
            Start Orchestrating LLMs
          </p>
        </div>

        {/* Signup Glassmorphic Card */}
        <div className="rounded-2xl border border-slate-800/80 bg-slate-950/60 backdrop-blur-xl shadow-2xl p-6 md:p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Error Banner */}
            {err && (
              <div className="flex gap-2.5 p-3 rounded-xl bg-rose-950/20 border border-rose-900/30 text-rose-300 text-xs">
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <span className="leading-relaxed">{err}</span>
              </div>
            )}

            {/* Email Field */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 tracking-wider uppercase font-mono">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@domain.com"
                  className="w-full bg-slate-900/40 border border-slate-800 focus:border-slate-700/80 focus:outline-none rounded-xl py-2.5 pl-11 pr-4 text-sm text-slate-200 placeholder-slate-600 transition-all duration-300"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 tracking-wider uppercase font-mono">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 6 characters"
                  className="w-full bg-slate-900/40 border border-slate-800 focus:border-slate-700/80 focus:outline-none rounded-xl py-2.5 pl-11 pr-4 text-sm text-slate-200 placeholder-slate-600 transition-all duration-300"
                />
              </div>
            </div>

            {/* Confirm Password Field */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 tracking-wider uppercase font-mono">
                Confirm Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-900/40 border border-slate-800 focus:border-slate-700/80 focus:outline-none rounded-xl py-2.5 pl-11 pr-4 text-sm text-slate-200 placeholder-slate-600 transition-all duration-300"
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !email || !password || !confirmPassword}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 transition-all duration-300 shadow-lg shadow-indigo-600/10 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed mt-4 group"
            >
              {loading ? (
                <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              ) : (
                <>
                  Register Account
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Footer info */}
        <p className="text-center text-xs text-slate-500 mt-6">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-semibold text-violet-400 hover:text-violet-300 transition-colors"
          >
            Sign in instead
          </Link>
        </p>
      </div>
    </div>
  );
}
