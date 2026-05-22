"use client";

import React, { useReducer, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useChatStore } from "../../store/chatStore";
import { apiPost } from "../../utils/api";
import { Bot, Mail, Lock, AlertCircle, ArrowRight, Eye, EyeOff, Check, X } from "lucide-react";
import Link from "next/link";

type TokenResponse = {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
  };
};

type SignupState = {
  email: string;
  password: string;
  confirmPassword: string;
  loading: boolean;
  err: string;
  showPassword: boolean;
  showConfirmPassword: boolean;
};

const initialState: SignupState = {
  email: "",
  password: "",
  confirmPassword: "",
  loading: false,
  err: "",
  showPassword: false,
  showConfirmPassword: false,
};

const getErrorMessage = (error: unknown, fallback: string) =>
  error instanceof Error && error.message ? error.message : fallback;

const getPasswordStrength = (password: string) => {
  if (!password) return { strength: 0, label: "", color: "", valid: false };
  let strength = 0;
  let valid = true;
  
  // Backend requirements: 8+ chars, uppercase, digit
  if (password.length >= 8) strength++;
  else valid = false;
  
  if (/[A-Z]/.test(password)) strength++;
  else valid = false;
  
  if (/\d/.test(password)) strength++;
  else valid = false;
  
  // Additional complexity
  if (password.length >= 12) strength++;
  if (/[a-z]/.test(password)) strength++;
  if (/[!@#$%^&*]/.test(password)) strength++;
  
  let label = "";
  let color = "";
  if (!valid) {
    label = "Needs uppercase & digit";
    color = "text-rose-400";
  } else if (strength <= 3) {
    label = "Fair";
    color = "text-yellow-400";
  } else if (strength <= 4) {
    label = "Good";
    color = "text-blue-400";
  } else {
    label = "Strong";
    color = "text-green-400";
  }
  
  return { strength, label, color, valid };
};

export default function SignupPageClient() {
  const { replace } = useRouter();
  const { signup: setStoreSignup } = useChatStore();
  const [state, setState] = useReducer(
    (prev: SignupState, next: Partial<SignupState>) => ({ ...prev, ...next }),
    initialState
  );
  const { email, password, confirmPassword, loading, err, showPassword, showConfirmPassword } = state;
  const passwordStrength = useMemo(() => getPasswordStrength(password), [password]);
  const passwordsMatch = password && confirmPassword && password === confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || !confirmPassword) return;

    if (!passwordStrength.valid) {
      setState({ err: "Password must be at least 8 characters with one uppercase letter and one number." });
      return;
    }

    if (password !== confirmPassword) {
      setState({ err: "Passwords do not match." });
      return;
    }

    setState({ loading: true, err: "" });

    try {
      // 1. Post to signup
      await apiPost("/auth/signup", { email, password });

      // 2. Automatically log them in to fetch JWT token
      const loginData = await apiPost<TokenResponse, { email: string; password: string }>(
        "/auth/login",
        { email, password }
      );

      setStoreSignup(loginData.access_token, loginData.user);
      replace("/chat");
    } catch (error: unknown) {
      setState({
        err: getErrorMessage(error, "Failed to create account. Email may already be in use."),
      });
    } finally {
      setState({ loading: false });
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
                <AlertCircle className="size-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <span className="leading-relaxed">{err}</span>
              </div>
            )}

            {/* Email Field */}
            <div className="space-y-1.5">
              <label
                htmlFor="signup-email"
                className="text-[10px] font-bold text-slate-400 tracking-wider uppercase font-mono"
              >
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Mail className="size-4" />
                </div>
                <input
                  id="signup-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setState({ email: e.target.value })}
                  placeholder="name@domain.com"
                  className="w-full bg-slate-900/40 border border-slate-800 focus:border-slate-700/80 focus:outline-none rounded-xl py-2.5 pl-11 pr-4 text-sm text-slate-200 placeholder-slate-600 transition-all duration-300"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <label
                htmlFor="signup-password"
                className="text-[10px] font-bold text-slate-400 tracking-wider uppercase font-mono"
              >
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="size-4" />
                </div>
                <input
                  id="signup-password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setState({ password: e.target.value })}
                  placeholder="At least 8 characters"
                  className="w-full bg-slate-900/40 border border-slate-800 focus:border-slate-700/80 focus:outline-none rounded-xl py-2.5 pl-11 pr-11 text-sm text-slate-200 placeholder-slate-600 transition-all duration-300"
                />
                <button
                  type="button"
                  onClick={() => setState({ showPassword: !showPassword })}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-400 transition-colors"
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              {password && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-xs">
                    <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          !passwordStrength.valid
                            ? "w-1/4 bg-rose-500"
                            : passwordStrength.strength <= 3
                          ? "w-1/2 bg-yellow-500"
                          : passwordStrength.strength <= 4
                          ? "w-3/4 bg-blue-500"
                          : "w-full bg-green-500"
                        }`}
                      />
                    </div>
                    <span className={`font-semibold ${passwordStrength.color}`}>
                      {passwordStrength.label}
                    </span>
                  </div>
                  {!passwordStrength.valid && (
                    <div className="text-xs text-slate-400 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={password.length >= 8 ? "text-green-400" : "text-slate-500"}>
                          ✓ At least 8 characters
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={/[A-Z]/.test(password) ? "text-green-400" : "text-slate-500"}>
                          ✓ One uppercase letter
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={/\d/.test(password) ? "text-green-400" : "text-slate-500"}>
                          ✓ One number
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Confirm Password Field */}
            <div className="space-y-1.5">
              <label
                htmlFor="signup-confirm-password"
                className="text-[10px] font-bold text-slate-400 tracking-wider uppercase font-mono"
              >
                Confirm Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="size-4" />
                </div>
                <input
                  id="signup-confirm-password"
                  type={showConfirmPassword ? "text" : "password"}
                  required
                  value={confirmPassword}
                  onChange={(e) => setState({ confirmPassword: e.target.value })}
                  placeholder="••••••••"
                  className="w-full bg-slate-900/40 border border-slate-800 focus:border-slate-700/80 focus:outline-none rounded-xl py-2.5 pl-11 pr-11 text-sm text-slate-200 placeholder-slate-600 transition-all duration-300"
                />
                <button
                  type="button"
                  onClick={() => setState({ showConfirmPassword: !showConfirmPassword })}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-400 transition-colors"
                >
                  {showConfirmPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              {confirmPassword && (
                <div className="flex items-center gap-2 text-xs">
                  {passwordsMatch ? (
                    <>
                      <Check className="size-4 text-green-400" />
                      <span className="text-green-400">Passwords match</span>
                    </>
                  ) : (
                    <>
                      <X className="size-4 text-rose-400" />
                      <span className="text-rose-400">Passwords don&apos;t match</span>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !email || !passwordStrength.valid || !confirmPassword || !passwordsMatch}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 transition-all duration-300 shadow-lg shadow-indigo-600/10 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed mt-4 group"
            >
              {loading ? (
                <span className="size-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              ) : (
                <>
                  Register Account
                  <ArrowRight className="size-4 group-hover:translate-x-0.5 transition-transform" />
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
