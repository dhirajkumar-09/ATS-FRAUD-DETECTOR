'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X } from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { getMe } from '@/lib/api/auth';
import Sidebar from '@/components/dashboard/Sidebar';
import UserMenu from '@/components/dashboard/UserMenu';
import AIAssistant from '@/components/ai/AIAssistant';
import { Skeleton } from '@/components/ui/skeleton';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { token, user, setAuth, clearAuth, _hasHydrated } = useAuthStore();
  const [validating, setValidating] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    // Wait until Zustand has finished reading from localStorage
    if (!_hasHydrated) return;

    if (!token) {
      // Definitely no token — go to auth
      router.replace('/auth');
      return;
    }

    // Token exists — validate it against the backend
    getMe()
      .then((freshUser) => {
        setAuth(token, freshUser);
        setValidating(false);
      })
      .catch(() => {
        clearAuth();
        router.replace('/auth');
      });
  }, [_hasHydrated]); // eslint-disable-line react-hooks/exhaustive-deps

  // Show skeleton while:
  // (a) store hasn't hydrated from localStorage yet, OR
  // (b) we're in the middle of validating the token with the server
  if (!_hasHydrated || validating) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0D0F14]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center">
            <div className="w-4 h-4 rounded-full border-2 border-[#3CB697] border-t-transparent animate-spin" />
          </div>
          <div className="space-y-2 w-48">
            <Skeleton className="h-3 w-full bg-[#171A22]" />
            <Skeleton className="h-3 w-3/4 bg-[#171A22]" />
            <Skeleton className="h-3 w-1/2 bg-[#171A22]" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-[#0D0F14]">
      {/* ── Desktop sidebar ─────────────────────────────────────────────── */}
      <div className="hidden lg:flex flex-shrink-0">
        <Sidebar />
      </div>

      {/* ── Mobile sidebar overlay ───────────────────────────────────────── */}
      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 z-40 lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed left-0 top-0 bottom-0 z-50 lg:hidden"
            >
              <Sidebar onClose={() => setSidebarOpen(false)} />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── Main content area ────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top nav bar */}
        <header className="h-14 flex items-center justify-between px-4 lg:px-6 border-b border-[rgba(60,182,151,0.08)] bg-[#0D0F14]/80 backdrop-blur-md sticky top-0 z-30">
          <button
            className="lg:hidden p-2 rounded-lg hover:bg-[#1E2230] text-[#7A8099] hover:text-[#E8E6DF] transition-colors"
            onClick={() => setSidebarOpen((o) => !o)}
            aria-label="Toggle navigation"
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>

          <div className="hidden lg:flex items-center gap-2 text-xs text-[#7A8099]">
            <span className="text-[#3CB697] font-mono">ATS</span>
            <span>/</span>
            <span>{user?.organization}</span>
          </div>

          <UserMenu />
        </header>

        {/* Routed page content */}
        <main className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="h-full"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Floating AI Assistant — accessible on every dashboard page */}
      <AIAssistant />
    </div>
  );
}
