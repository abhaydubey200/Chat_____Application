"use client";

import React, { ReactNode } from "react";
import { AlertTriangle, RotateCw, LogOut } from "lucide-react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorCount: number;
}

/**
 * Error Boundary component to catch React component errors.
 *
 * Prevents entire app crash from a single component failure.
 * Shows user-friendly error message with recovery options.
 *
 * Usage:
 * <ErrorBoundary>
 *   <ChatWindow />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorCount: 0
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error to console in development
    if (process.env.NODE_ENV === "development") {
      console.error("Error Boundary caught an error:", error, errorInfo);
    }

    // Track error count to detect rapid failures
    this.setState((prevState) => ({
      errorCount: prevState.errorCount + 1
    }));

    // In production, you would send this to error tracking service
    // e.g., Sentry, LogRocket, Rollbar
    if (typeof window !== "undefined" && window.location.hostname !== "localhost") {
      // TODO: Send to error tracking service
      // captureException(error);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorCount: 0
    });
  };

  handleLogout = () => {
    // Clear auth and redirect to login
    if (typeof window !== "undefined") {
      localStorage.removeItem("dushman_auth_token");
      window.location.href = "/login";
    }
  };

  render() {
    if (this.state.hasError) {
      // If error count exceeds threshold, suggest logout
      const shouldSuggestLogout = this.state.errorCount > 3;
      const errorMessage = this.state.error?.message || "An unexpected error occurred";

      return (
        <div className="size-full flex items-center justify-center bg-gradient-to-br from-slate-950 to-slate-900 p-4">
          <div className="max-w-md w-full">
            {/* Error Icon */}
            <div className="flex justify-center mb-6">
              <div className="p-3 rounded-2xl bg-rose-950/30 border border-rose-900/50">
                <AlertTriangle className="size-8 text-rose-500" />
              </div>
            </div>

            {/* Error Message */}
            <h1 className="text-2xl font-semibold text-white text-center mb-2">Something went wrong</h1>
            <p className="text-sm text-slate-400 text-center mb-4">
              We encountered an unexpected error. Please try the actions below:
            </p>

            {/* Error Details (Development Only) */}
            {process.env.NODE_ENV === "development" && (
              <div className="mb-6 p-3 rounded-lg bg-slate-800/50 border border-slate-700 max-h-24 overflow-y-auto">
                <p className="text-xs text-slate-300 font-mono break-words">{errorMessage}</p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="space-y-3">
              {/* Refresh/Retry Button */}
              <button
                onClick={this.handleReset}
                className="w-full px-4 py-2.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-medium flex items-center justify-center gap-2 transition-all duration-200 shadow-lg shadow-violet-600/20"
              >
                <RotateCw className="size-4" />
                Try Again
              </button>

              {/* Logout Button (if too many errors) */}
              {shouldSuggestLogout && (
                <button
                  onClick={this.handleLogout}
                  className="w-full px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium flex items-center justify-center gap-2 transition-all duration-200 border border-slate-700"
                >
                  <LogOut className="size-4" />
                  Back to Login
                </button>
              )}

              {/* Go Home Link */}
              <button
                onClick={() => {
                  if (typeof window !== "undefined") {
                    window.location.href = "/";
                  }
                }}
                className="w-full px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition-all duration-200 border border-slate-700"
              >
                Go to Home
              </button>
            </div>

            {/* Help Text */}
            <p className="text-xs text-slate-500 text-center mt-6">
              Error persists? Contact support or check the browser console for details.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
