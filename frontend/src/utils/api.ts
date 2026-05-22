const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const AUTH_COOKIE = "dushman_auth_token";

const getAuthCookie = (): string | null => {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${AUTH_COOKIE}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
};

const setAuthCookie = (token: string) => {
  if (typeof document === "undefined") return;
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${AUTH_COOKIE}=${encodeURIComponent(token)}; Path=/; SameSite=Lax${secure}`;
};

const clearAuthCookie = () => {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
};

// Helper to get auth token from localStorage
export const getAuthToken = (): string | null => {
  if (typeof window === "undefined") {
    return null;
  }

  const storedToken = localStorage.getItem(AUTH_COOKIE);
  if (storedToken) {
    return storedToken;
  }

  const cookieToken = getAuthCookie();
  if (cookieToken) {
    localStorage.setItem(AUTH_COOKIE, cookieToken);
  }

  return cookieToken;
};

// Helper to set auth token
export const setAuthToken = (token: string) => {
  if (typeof window !== "undefined") {
    localStorage.setItem(AUTH_COOKIE, token);
    setAuthCookie(token);
  }
};

// Helper to clear auth token
export const clearAuthToken = () => {
  if (typeof window !== "undefined") {
    localStorage.removeItem(AUTH_COOKIE);
    clearAuthCookie();
  }
};

// General fetch wrapper for JSON requests
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearAuthToken();
    if (typeof window !== "undefined" && window.location.pathname !== "/login" && window.location.pathname !== "/signup") {
      window.location.href = "/login";
    }
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const apiGet = <T>(path: string) => request<T>(path, { method: "GET" });
export const apiPost = <TResponse, TBody = unknown>(path: string, body: TBody) =>
  request<TResponse>(path, { method: "POST", body: JSON.stringify(body) });
export const apiPatch = <TResponse, TBody = unknown>(path: string, body: TBody) =>
  request<TResponse>(path, { method: "PATCH", body: JSON.stringify(body) });
export const apiDelete = <TResponse>(path: string) => request<TResponse>(path, { method: "DELETE" });

// SSE chat streaming reader
export async function streamChat(
  conversationId: string,
  message: string,
  modelType: string,
  abortController: AbortController,
  onChunk: (text: string) => void,
  onDone: (fullText: string) => void,
  onError: (error: string) => void
) {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        conversation_id: conversationId,
        message,
        model_type: modelType,
      }),
      signal: abortController.signal,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to start stream");
    }

    if (!response.body) {
      throw new Error("No response body received from server");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let currentEvent = "";

    // Iterative read loop to avoid potential stack buildup from recursion
    // in long-lived streaming sessions
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

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
              onChunk(data.content);
            } else if (currentEvent === "done") {
              onDone(data.content);
            } else if (currentEvent === "error") {
              onError(data.content);
            }
          } catch (e) {
            console.error("Failed to parse SSE data chunk", e);
          }
        }
      }
    }
  } catch (err: unknown) {
    const error = err instanceof Error ? err : null;
    if (error?.name === "AbortError") {
      console.log("Stream generation aborted by user.");
    } else {
      onError(error?.message || "An error occurred during streaming.");
    }
  }
}
