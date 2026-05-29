import "server-only";
import { cookies } from "next/headers";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const AUTH_COOKIE = "dushman_auth_token";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  userRole: string | null;
}

export const getServerAuthState = async (): Promise<AuthState> => {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value ?? null;

  if (!token) {
    return { token: null, isAuthenticated: false, userRole: null };
  }

  const response = await fetch(`${API_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  if (response.status === 401) {
    return { token, isAuthenticated: false, userRole: null };
  }

  if (!response.ok) {
    throw new Error(`Auth check failed with status ${response.status}`);
  }

  // Try to extract role from response body
  let userRole: string | null = null;
  try {
    const body = await response.clone().json();
    userRole = body.role ?? null;
  } catch {
    // Response body not needed for auth check alone
  }

  return { token, isAuthenticated: true, userRole };
};
