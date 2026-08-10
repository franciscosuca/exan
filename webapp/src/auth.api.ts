import { throwResponseError } from "./lib/response-error";

const API_BASE = "/api";

export interface AuthResponse {
  token: string;
  username: string;
}

export interface AuthError {
  error: string;
}

export async function login(
  username: string,
  password: string
): Promise<AuthResponse> {
  const requestUrl = `${API_BASE}/auth/login`;
  const res = await fetch(requestUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    await throwResponseError(res, {
      fallbackMessage: "Login failed",
      method: "POST",
      requestUrl,
    });
  }

  return res.json();
}

export async function register(
  username: string,
  password: string,
  repeatPassword: string
): Promise<AuthResponse> {
  const requestUrl = `${API_BASE}/auth/register`;
  const res = await fetch(requestUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, repeatPassword }),
  });

  if (!res.ok) {
    await throwResponseError(res, {
      fallbackMessage: "Registration failed",
      method: "POST",
      requestUrl,
    });
  }

  return res.json();
}

export function saveToken(token: string): void {
  localStorage.setItem("auth_token", token);
}

export function getToken(): string | null {
  return localStorage.getItem("auth_token");
}

export function clearToken(): void {
  localStorage.removeItem("auth_token");
}

export function saveUsername(username: string): void {
  localStorage.setItem("auth_username", username);
}

export function getUsername(): string | null {
  return localStorage.getItem("auth_username");
}

export function clearUsername(): void {
  localStorage.removeItem("auth_username");
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}

export function logout(): void {
  clearToken();
  clearUsername();
}
