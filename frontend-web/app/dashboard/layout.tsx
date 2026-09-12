'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X, ScanLine, LayoutList, Search, Settings } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { getMe } from '@/lib/api/auth';
import Sidebar from '@/components/dashboard/Sidebar';
import UserMenu from '@/components/dashboard/UserMenu';
import AIAssistant from '@/components/ai/AIAssistant';

// ── Page title map ───────────────────────────────────────────────────────────
const PAGE_META: Record<string, { title: string; icon: LucideIcon; description: string }> = {
  '/dashboard/scan':     { title: 'Single Scan',    icon: ScanLine,   description: 'Forensic analysis of one resume PDF' },
  '/dashboard/batch':    { title: 'Batch Scan',     icon: LayoutList, description: 'Scan and rank multiple resumes at once' },
  '/dashboard/inspect':  { title: 'Span Inspector', icon: Search,     description: 'Deep-dive into text spans and metadata' },
  '/dashboard/settings': { title: 'Org Settings',   icon: Settings,   description: 'Configure thresholds and organization' },
};


function getPageMeta(pathname: string) {
  // Exact match first
  if (PAGE_META[pathname]) return PAGE_META[pathname];
  // Prefix match (e.g. /dashboard/inspect/42)
  for (const [key, meta] of Object.entries(PAGE_META)) {
    if (pathname.startsWith(key + '/')) return meta;
  }
  return null;
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { token, user, setAuth, clearAuth, _hasHydrated } = useAuthStore();
  const [validating, setValidating] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const pageMeta = getPageMeta(pathname);

  useEffect(() => {
    if (!_hasHydrated) return;
    if (!token) {
      router.replace('/auth');
      return;
    }
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

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  if (!_hasHydrated || validating) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0B0D12]">
        <div className="flex flex-col items-center gap-5">
          {/* Animated logo mark */}
          <div className="w-12 h-12 rounded-2xl bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center">
            <div className="w-5 h-5 rounded-full border-2 border-[#3CB697] border-t-transparent animate-spin" />
          </div>
          <div className="text-center space-y-1">
            <p className="text-sm font-semibold text-[#E8E6DF]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
              ATS Fraud Detector
            </p>
            <p className="text-xs text-[#8A90A4]">Verifying credentials…</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-[#0B0D12]">
      {/* ── Desktop sidebar ───────────────────────────────────────────────── */}
      <div className="hidden lg:flex flex-shrink-0">
        <Sidebar />
      </div>

      {/* ── Mobile sidebar overlay ─────────────────────────────────────────── */}
      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/65 backdrop-blur-sm z-40 lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', damping: 28, stiffness: 220 }}
              className="fixed left-0 top-0 bottom-0 z-50 lg:hidden"
            >
              <Sidebar onClose={() => setSidebarOpen(false)} />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── Main content area ─────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top nav bar */}
        <header className="h-14 flex items-center justify-between px-4 lg:px-6 border-b border-[rgba(60,182,151,0.07)] bg-[#0B0D12]/90 backdrop-blur-md sticky top-0 z-30">
          {/* Mobile hamburger */}
          <button
            className="lg:hidden p-2 rounded-lg hover:bg-[#1E2230] text-[#8A90A4] hover:text-[#E8E6DF] transition-colors"
            onClick={() => setSidebarOpen((o) => !o)}
            aria-label="Toggle navigation"
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>

          {/* Desktop: page title breadcrumb */}
          {pageMeta ? (
            <div className="hidden lg:flex items-center gap-3">
              <div className="w-7 h-7 rounded-lg bg-[#3CB697]/10 border border-[#3CB697]/15 flex items-center justify-center">
                <pageMeta.icon size={13} className="text-[#3CB697]" />
              </div>
              <div>
                <p
                  className="text-sm font-semibold text-[#E8E6DF] leading-none"
                  style={{ fontFamily: 'var(--font-space-grotesk)' }}
                >
                  {pageMeta.title}
                </p>
                <p className="text-[10px] text-[#8A90A4] mt-0.5">{pageMeta.description}</p>
              </div>
            </div>
          ) : (
            <div className="hidden lg:flex items-center gap-2 text-xs text-[#8A90A4]">
              <span className="text-[#3CB697] font-mono font-semibold">ATS</span>
              <span className="text-[#8A90A4]/40">/</span>
              <span>{user?.organization}</span>
            </div>
          )}

          <UserMenu />
        </header>

        {/* Routed page content */}
        <main className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
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
