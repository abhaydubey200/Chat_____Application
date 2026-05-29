const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const AUTH_COOKIE = "dushman_auth_token";

// Helper to get auth token from HTTP-only cookie (preferred, set by server)
export const getAuthToken = (): string | null => {
  if (typeof window === "undefined") {
    return null;
  }

  // Attempt to read from secure HTTP-only cookie
  const match = document.cookie.match(new RegExp(`(?:^|; )${AUTH_COOKIE}=([^;]*)`));
  if (match) {
    return decodeURIComponent(match[1]);
  }

  // Fallback to session storage if cookie isn't available
  if (typeof sessionStorage !== "undefined") {
    return sessionStorage.getItem(AUTH_COOKIE);
  }

  return null;
};

// Helper to set auth token in both cookie and memory
// Note: In production, backend should set HTTP-only cookie during login
export const setAuthToken = (token: string) => {
  if (typeof window !== "undefined") {
    // Set secure cookie (HTTP-only should be set by backend)
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `${AUTH_COOKIE}=${encodeURIComponent(token)}; Path=/; SameSite=Strict${secure}`;
    
    // Store in sessionStorage instead of localStorage for better security
    // Session storage is cleared when tab closes
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.setItem(AUTH_COOKIE, token);
    }
  }
};

// Helper to clear auth token
export const clearAuthToken = () => {
  if (typeof window !== "undefined") {
    // Clear from storage
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.removeItem(AUTH_COOKIE);
    }
    // Clear cookie
    document.cookie = `${AUTH_COOKIE}=; Path=/; Max-Age=0; SameSite=Strict`;
  }
};

// Generate CSRF token for secure requests (though using SameSite cookie helps)
const generateCSRFToken = (): string => {
  return Math.random().toString(36).substring(2);
};

// Store CSRF token in memory for the session
let csrfToken: string | null = null;

const getCSRFToken = (): string => {
  if (!csrfToken) {
    csrfToken = generateCSRFToken();
  }
  return csrfToken;
};

// Sanitize error messages to prevent XSS in error displays
const sanitizeErrorMessage = (message: string): string => {
  if (typeof message !== "string") return "An error occurred";
  return message
    .replace(/&/g, "&amp;")  // Must be first to prevent double-escaping
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;")
    .replace(/\//g, "&#x2F;")
    .substring(0, 500); // Limit length
};

// General fetch wrapper for JSON requests with timeout and error handling
async function request<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs: number = 30000
): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  // Add CSRF token for state-changing requests
  if (["POST", "PATCH", "DELETE", "PUT"].includes(options.method?.toUpperCase() || "GET")) {
    headers.set("X-CSRF-Token", getCSRFToken());
  }

  // Add timeout with AbortController
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (response.status === 401) {
      clearAuthToken();
      if (typeof window !== "undefined" && window.location.pathname !== "/login" && window.location.pathname !== "/signup") {
        window.location.href = "/login";
      }
      throw new Error("Session expired. Please log in again.");
    }

    if (!response.ok) {
      let errorMessage = `Request failed with status ${response.status}`;
      try {
        const errorBody = await response.json();
        errorMessage = errorBody.detail || errorMessage;
      } catch {
        // Response is not JSON, use status message
      }
      throw new Error(sanitizeErrorMessage(errorMessage));
    }

    return response.json() as Promise<T>;
  } catch (error) {
    clearTimeout(timeoutId);
    
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      throw new Error("Network error. Please check your connection.");
    }
    
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error(`Request timeout after ${timeoutMs}ms`);
    }
    
    throw error;
  }
}

export const apiGet = <T>(path: string) => request<T>(path, { method: "GET" }, 30000);
export const apiPost = <TResponse, TBody = unknown>(path: string, body: TBody) =>
  request<TResponse>(path, { method: "POST", body: JSON.stringify(body) }, 30000);
export const apiPatch = <TResponse, TBody = unknown>(path: string, body: TBody) =>
  request<TResponse>(path, { method: "PATCH", body: JSON.stringify(body) }, 30000);
export const apiDelete = <TResponse>(path: string) => request<TResponse>(path, { method: "DELETE" }, 30000);

// SSE chat streaming reader with automatic reconnection on transient failures.
//
// Uses exponential backoff (1s → 2s → 4s → 8s) with a jitter of ±500ms to
// gracefully recover from network blips without overwhelming the server.
// Does NOT retry on user-initiated abort (AbortController) or on fatal errors
// such as invalid credentials or bad requests.
//
// NOTE: On reconnection, the entire request is re-sent to the backend, so
// the LLM response is generated from scratch. This means the user may see
// duplicated content briefly in the UI as the new stream fills in. For a
// production-grade solution, consider a stateful resume token or cursor.
//
// Configuration constants
const MAX_RECONNECT_ATTEMPTS = 4;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 8000;
const RECONNECT_JITTER_MS = 500;

function isRetryableHttpStatus(status: number): boolean {
  // 5xx errors are potentially transient; 4xx are client errors and not retryable
  return status >= 500 && status < 600;
}

function isNetworkError(error: unknown): boolean {
  return (
    error instanceof TypeError &&
    error.message === "Failed to fetch"
  );
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function calculateBackoff(attempt: number): number {
  const delay = Math.min(RECONNECT_BASE_MS * 2 ** attempt, RECONNECT_MAX_MS);
  const jitter = Math.random() * RECONNECT_JITTER_MS * 2 - RECONNECT_JITTER_MS;
  return Math.max(0, delay + jitter);
}

// On-reconnect callback type — lets the caller show a "reconnecting…" UI
// eslint-disable-next-line @typescript-eslint/no-unused-vars

export async function streamChat(
  conversationId: string,
  message: string,
  modelType: string,
  abortController: AbortController,
  onChunk: (text: string) => void,
  onDone: (fullText: string) => void,
  onError: (error: string) => void,
  onReconnecting?: (attempt: number) => void  // optional: called before each retry
) {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  headers["X-CSRF-Token"] = getCSRFToken();

  const body = JSON.stringify({
    conversation_id: conversationId,
    message,
    model_type: modelType,
  });

  let reconnectionAttempt = 0;
  let accumulatedPartialContent = "";

  while (reconnectionAttempt <= MAX_RECONNECT_ATTEMPTS) {
    // If the user has aborted, stop immediately
    if (abortController.signal.aborted) {
      console.log("Stream generation aborted by user.");
      return;
    }

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers,
        body,
        signal: abortController.signal,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        const status = response.status;

        // Only retry on server errors (5xx)
        if (isRetryableHttpStatus(status) && reconnectionAttempt < MAX_RECONNECT_ATTEMPTS) {
          reconnectionAttempt++;
          onReconnecting?.(reconnectionAttempt);
          const delay = calculateBackoff(reconnectionAttempt);
          console.warn(
            `SSE reconnecting in ${Math.round(delay)}ms (attempt ${reconnectionAttempt}/${MAX_RECONNECT_ATTEMPTS})`
          );
          await sleep(delay);
          continue;
        }

        // Non-retryable status — surface the error immediately
        throw new Error(err.detail || `Request failed with status ${status}`);
      }

      if (!response.body) {
        throw new Error("No response body received from server");
      }

      // Reset reconnection counter on successful connection
      reconnectionAttempt = 0;

      // ── Read the SSE stream ──────────────────────────────────────
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let currentEvent = "";
      let streamComplete = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          streamComplete = true;
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() || ""; // Keep the last incomplete line in the buffer

        for (const line of lines) {
          if (!line.trim()) continue;

          if (line.startsWith("event:")) {
            currentEvent = line.substring(6).trim();
          } else if (line.startsWith("data:")) {
            const dataStr = line.substring(5).trim();
            try {
              const data = JSON.parse(dataStr);
              if (currentEvent === "delta") {
                accumulatedPartialContent += data.content;
                onChunk(data.content);
              } else if (currentEvent === "done") {
                streamComplete = true;
                onDone(data.content);
              } else if (currentEvent === "error") {
                onError(data.content);
                return;  // Fatal error from server — do not retry
              }
            } catch (e) {
              console.error("Failed to parse SSE data chunk", e);
            }
          }
        }
      }

      if (streamComplete) {
        return;  // Stream finished normally
      }
    } catch (err: unknown) {
      const error = err instanceof Error ? err : null;

      // User-initiated abort — stop immediately
      if (error?.name === "AbortError") {
        console.log("Stream generation aborted by user.");
        return;
      }

      // Network error or transient failure — retry if we haven't exhausted attempts
      const isTransient = isNetworkError(error) || error?.message?.includes("Failed to start stream");

      if (isTransient && reconnectionAttempt < MAX_RECONNECT_ATTEMPTS) {
        reconnectionAttempt++;
        onReconnecting?.(reconnectionAttempt);
        const delay = calculateBackoff(reconnectionAttempt);
        console.warn(
          `SSE reconnecting after error in ${Math.round(delay)}ms (attempt ${reconnectionAttempt}/${MAX_RECONNECT_ATTEMPTS})`
        );
        await sleep(delay);
        continue;  // Retry the outer loop
      }

      // Non-retryable or exhausted — report error
      onError(error?.message || "An error occurred during streaming.");
      return;
    }
  }
}
