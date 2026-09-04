export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_KEY ?? "change-me-to-a-long-random-secret";

export type LoginUser = { id: string; email: string; full_name: string; role: string };
export type LoginResponse = { access_token: string; token_type: string; expires_at: string; user: LoginUser };

let _token: string | null = typeof window !== "undefined" ? window.localStorage.getItem("cx_token") : null;
let _user: LoginUser | null = null;

export function setToken(token: string): void {
  _token = token;
  if (typeof window !== "undefined") window.localStorage.setItem("cx_token", token);
}
export function getToken(): string | null { return _token; }
export function clearToken(): void {
  _token = null; _user = null;
  if (typeof window !== "undefined") window.localStorage.removeItem("cx_token");
}
export function setUser(u: LoginUser): void { _user = u; }
export function getUser(): LoginUser | null {
  if (_user) return _user;
  if (typeof window !== "undefined") {
    const raw = window.localStorage.getItem("cx_user");
    if (raw) { try { _user = JSON.parse(raw); } catch {} }
  }
  return _user;
}

export async function login(email: string, password: string): Promise<LoginUser> {
  const body = new URLSearchParams(); body.set("username", email); body.set("password", password);
  const res = await fetch(`${API_URL}/api/auth/login`, { method: "POST", body: body.toString() });
  if (!res.ok) throw new Error(`${res.status}: ${(await res.text()) || "login failed"}`);
  const data = (await res.json()) as LoginResponse;
  setToken(data.access_token);
  setUser(data.user);
  if (typeof window !== "undefined") window.localStorage.setItem("cx_user", JSON.stringify(data.user));
  return data.user;
}

export async function api<T = any>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string> | undefined),
  };
  if (path.startsWith("/api/admin")) headers["X-Admin-Key"] = ADMIN_KEY;
  if (getToken()) headers["Authorization"] = `Bearer ${getToken()}`;
  const res = await fetch(`${API_URL}${path}`, { ...opts, headers });
  if (res.status === 401) { clearToken(); if (typeof window !== "undefined") window.location.href = "/login"; }
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status}: ${detail || res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type Brand = {
  id: string;
  name: string;
  description: string;
  website_url: string;
  is_active: boolean;
};

export type ReplyLog = {
  id: string;
  brand_name: string;
  customer_message: string;
  draft_text: string;
  final_text: string;
  confidence: number;
  status: string;
  validation_code: string;
  citation?: string;
  created_at: string;
};