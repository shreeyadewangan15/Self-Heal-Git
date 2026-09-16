import {
  AuthResponse,
  DecodedToken,
  PRRecordDetail,
  PRRecordSummary,
  PRStats,
  UserProfile,
  UserRole,
  SandboxSimulateResult,
  AdminRepository,
  AdminTelemetry,
  LLMConfig,
  KnownAccount,
  VisualDiagnosticTrace,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const TOKEN_KEY = 'self_heal_jwt_token';
const USER_KEY = 'self_heal_user_profile';

/**
 * Safe client-side token retrieval
 */
export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Store JWT token and optional profile
 */
export function setToken(token: string, user?: Partial<UserProfile>): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
}

/**
 * Clear authentication state
 */
export function removeToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/**
 * Simple client-side JWT decoder without third-party heavy dependencies
 */
export function decodeJWT(token: string): DecodedToken | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payloadBase64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(payloadBase64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload) as DecodedToken;
  } catch (error) {
    console.error('Failed to decode JWT:', error);
    return null;
  }
}

/**
 * Extract active user role from stored token
 */
export function getUserRole(): UserRole | null {
  const token = getToken();
  if (!token) return null;
  const decoded = decodeJWT(token);
  return decoded ? decoded.role : null;
}

/**
 * Get cached profile or derive from token
 */
export function getStoredUser(): Partial<UserProfile> | null {
  if (typeof window === 'undefined') return null;
  const cached = localStorage.getItem(USER_KEY);
  if (cached) {
    try {
      return JSON.parse(cached);
    } catch {
      // fallback to token
    }
  }
  const token = getToken();
  if (!token) return null;
  const decoded = decodeJWT(token);
  if (!decoded) return null;
  return {
    email: decoded.sub,
    role: decoded.role,
    id: decoded.id,
  };
}

/**
 * Fetch wrapper with automatic Bearer token injection
 */
export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // If unauthorized, clear invalid token
    if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
      removeToken();
      window.location.href = '/login';
    }
    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
    throw new Error(errorBody.detail || 'Unauthorized: Session expired or invalid');
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorBody.detail || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Authentication APIs
// ---------------------------------------------------------------------------

export async function login(email: string, password: string): Promise<AuthResponse> {
  const data = await apiFetch<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setToken(data.access_token, {
    email: data.email,
    full_name: data.full_name,
    role: data.role,
    picture_url: data.picture_url,
  });
  return data;
}

export async function register(
  email: string,
  password: string,
  fullName: string
): Promise<UserProfile> {
  return apiFetch<UserProfile>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
    }),
  });
}

export async function getMe(): Promise<UserProfile> {
  return apiFetch<UserProfile>('/api/auth/me');
}

export async function loginWithGoogle(
  idToken?: string,
  code?: string,
  requestedRole?: UserRole
): Promise<AuthResponse> {
  const data = await apiFetch<AuthResponse>('/api/auth/google', {
    method: 'POST',
    body: JSON.stringify({
      id_token: idToken,
      code: code,
      requested_role: requestedRole,
    }),
  });
  setToken(data.access_token, {
    email: data.email,
    full_name: data.full_name,
    role: data.role,
    picture_url: data.picture_url,
  });
  return data;
}

export async function getGoogleAuthUrl(): Promise<{
  auth_url: string;
  client_id: string;
  redirect_uri: string;
}> {
  return apiFetch<{
    auth_url: string;
    client_id: string;
    redirect_uri: string;
  }>('/api/auth/google/url');
}

export async function getAccounts(): Promise<KnownAccount[]> {
  try {
    return await apiFetch<KnownAccount[]>('/api/auth/accounts');
  } catch (err) {
    console.warn('Failed to fetch accounts list:', err);
    return [];
  }
}

// ---------------------------------------------------------------------------
// Developer & PR APIs
// ---------------------------------------------------------------------------

export async function getMyPRFeed(): Promise<{
  stats: PRStats;
  user_email: string;
  user_role: string;
  prs: PRRecordSummary[];
}> {
  return apiFetch<{
    stats: PRStats;
    user_email: string;
    user_role: string;
    prs: PRRecordSummary[];
  }>('/api/prs/my-feed');
}

export async function getPRs(): Promise<{ stats: PRStats; prs: PRRecordSummary[] }> {
  return apiFetch<{ stats: PRStats; prs: PRRecordSummary[] }>('/api/prs');
}

export async function getPRDetail(id: number): Promise<PRRecordDetail> {
  return apiFetch<PRRecordDetail>(`/api/prs/${id}`);
}

export async function getPRDiff(id: number): Promise<PRRecordDetail> {
  return apiFetch<PRRecordDetail>(`/api/prs/${id}/diff`);
}

export async function approvePRPatch(id: number): Promise<{
  message: string;
  id: number;
  status: string;
  commit_sha: string;
  approved_by: string;
}> {
  return apiFetch<{
    message: string;
    id: number;
    status: string;
    commit_sha: string;
    approved_by: string;
  }>(`/api/prs/${id}/approve`, {
    method: 'POST',
  });
}

export async function simulatePR(): Promise<{ message: string; pr_number: number; id: number }> {
  return apiFetch<{ message: string; pr_number: number; id: number }>('/api/prs/simulate', {
    method: 'POST',
  });
}

export async function simulateSandboxPatch(payload: {
  code_snippet: string;
  file_path?: string;
}): Promise<SandboxSimulateResult> {
  return apiFetch<SandboxSimulateResult>('/api/prs/simulate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function deletePR(prId: number): Promise<{ message: string; id: number; repo: string }> {
  return apiFetch<{ message: string; id: number; repo: string }>(`/api/prs/${prId}`, {
    method: 'DELETE',
  });
}

// ---------------------------------------------------------------------------
// Administrator Control Center APIs
// ---------------------------------------------------------------------------

export async function getAdminRepositories(): Promise<AdminRepository[]> {
  return apiFetch<AdminRepository[]>('/api/admin/repositories');
}

export async function addAdminRepository(data: {
  full_name: string;
  webhook_secret?: string;
  auto_commit_enabled?: boolean;
}): Promise<AdminRepository & { message: string }> {
  return apiFetch<AdminRepository & { message: string }>('/api/admin/repositories', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function deleteAdminRepository(repoId: number): Promise<{ message: string; id: number }> {
  return apiFetch<{ message: string; id: number }>(`/api/admin/repositories/${repoId}`, {
    method: 'DELETE',
  });
}

export async function updateAdminRepository(
  repoId: number,
  data: { auto_commit_enabled?: boolean; webhook_secret?: string; is_active?: boolean }
): Promise<AdminRepository & { message: string }> {
  return apiFetch<AdminRepository & { message: string }>(`/api/admin/repositories/${repoId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function getAdminUsers(): Promise<UserProfile[]> {
  return apiFetch<UserProfile[]>('/api/admin/users');
}

export async function updateAdminUser(
  userId: number,
  data: { role?: UserRole; is_active?: boolean }
): Promise<UserProfile> {
  return apiFetch<UserProfile>(`/api/admin/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function getAdminTelemetry(): Promise<AdminTelemetry> {
  return apiFetch<AdminTelemetry>('/api/admin/telemetry');
}

export async function updateAdminLLMConfig(data: Partial<LLMConfig>): Promise<{
  message: string;
  config: LLMConfig;
}> {
  return apiFetch<{ message: string; config: LLMConfig }>('/api/admin/llm-config', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// 3-Agent Event-Driven Pipeline APIs
// ---------------------------------------------------------------------------

export async function triggerPipelineBenchmark(): Promise<VisualDiagnosticTrace> {
  return apiFetch<VisualDiagnosticTrace>('/api/pipeline/benchmark', {
    method: 'POST',
  });
}

export async function getLatestPipelineTrace(): Promise<VisualDiagnosticTrace> {
  return apiFetch<VisualDiagnosticTrace>('/api/pipeline/latest-trace');
}

