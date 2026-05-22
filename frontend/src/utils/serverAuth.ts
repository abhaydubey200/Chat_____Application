import "server-only";
import { cookies } from "next/headers";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const AUTH_COOKIE = "dushman_auth_token";

export const getServerAuthState = async () => {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value ?? null;

  if (!token) {
    return { token: null, isAuthenticated: false };
  }

  const response = await fetch(`${API_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  if (response.status === 401) {
    return { token, isAuthenticated: false };
  }

  if (!response.ok) {
    throw new Error(`Auth check failed with status ${response.status}`);
  }

  return { token, isAuthenticated: true };
};
