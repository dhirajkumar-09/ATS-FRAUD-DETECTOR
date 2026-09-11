import apiClient from './client';
import type { TokenResponse, UserOut, OrgSettingsOut, OrgSettingsIn } from '../types';

export async function register(payload: {
  email: string;
  password: string;
  full_name: string;
  organization: string;
}): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/register', payload);
  return data;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const formData = new URLSearchParams();
  formData.set('username', email);
  formData.set('password', password);
  const { data } = await apiClient.post<TokenResponse>('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data;
}

export async function getMe(): Promise<UserOut> {
  const { data } = await apiClient.get<UserOut>('/auth/me');
  return data;
}

// Explicitly pass token — use this right after login/register before
// the token is persisted to localStorage (avoids 401 race condition)
export async function getMeWithToken(token: string): Promise<UserOut> {
  const { data } = await apiClient.get<UserOut>('/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

export async function getOrgSettings(): Promise<OrgSettingsOut> {
  const { data } = await apiClient.get<OrgSettingsOut>('/auth/org-settings');
  return data;
}

export async function updateOrgSettings(payload: OrgSettingsIn): Promise<OrgSettingsOut> {
  const { data } = await apiClient.put<OrgSettingsOut>('/auth/org-settings', payload);
  return data;
}
