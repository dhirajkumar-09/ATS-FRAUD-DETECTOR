'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserOut } from '@/lib/types';

interface AuthState {
  token: string | null;
  user: UserOut | null;
  _hasHydrated: boolean;
  setAuth: (token: string, user: UserOut) => void;
  clearAuth: () => void;
  setHasHydrated: (v: boolean) => void;
}

function setCookie(name: string, value: string, days = 7) {
  if (typeof document === 'undefined') return;
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function deleteCookie(name: string) {
  if (typeof document === 'undefined') return;
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; SameSite=Lax`;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      _hasHydrated: false,
      setAuth: (token, user) => {
        setCookie('ats-token', token);
        set({ token, user });
      },
      clearAuth: () => {
        deleteCookie('ats-token');
        set({ token: null, user: null });
      },
      setHasHydrated: (v) => set({ _hasHydrated: v }),
    }),
    {
      name: 'ats-auth',
      // Called once localStorage has been read back into the store
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
        // Re-sync the cookie in case it expired but localStorage still has the token
        if (state?.token) {
          setCookie('ats-token', state.token);
        }
      },
    },
  ),
);
