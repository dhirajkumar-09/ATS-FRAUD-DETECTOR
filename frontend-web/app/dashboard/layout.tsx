'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X, ScanLine, LayoutList, Search, Settings, Rocket, History, LayoutDashboard, Shield, User } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { getMe } from '@/lib/api/auth';
import Sidebar from '@/components/dashboard/Sidebar';
import UserMenu from '@/components/dashboard/UserMenu';
import AIAssistant from '@/components/ai/AIAssistant';

// ── Page title map ───────────────────────────────────────────────────────────
const PAGE_META: Record<string, { title: string; icon: LucideIcon; description: string }> = {
  '/dashboard':          { title: 'Overview',       icon: LayoutDashboard, description: 'Recruiter hub, recent scans, and audit metrics' },
  '/dashboard/scan':     { title: 'Single Scan',    icon: ScanLine,   description: 'Forensic analysis of one resume PDF' },
  '/dashboard/batch':    { title: 'Batch Scan',     icon: LayoutList, description: 'Scan and rank multiple resumes at once' },
  '/dashboard/inspect':  { title: 'Span Inspector', icon: Search,     description: 'Deep-dive into text spans and metadata' },
  '/dashboard/history':  { title: 'Scan History',   icon: History,    description: 'Past forensic audits and scan logs' },
  '/dashboard/settings': { title: 'Org Settings',   icon: Settings,   description: 'Configure thresholds and organization' },
  '/dashboard/roadmap':  { title: 'Future Roadmap', icon: Rocket,     description: 'Planned upcoming features on the forensic horizon' },
  '/dashboard/profile':  { title: 'Profile',        icon: User,       description: 'Your account details and password' },
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

  // Close sidebar on route change
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
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
      {/* ── Slide-in Navigation Drawer (Toggled by 3-line hamburger button) ───── */}
      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-[#0B0D12]/60 backdrop-blur-md z-40"
              onClick={() => setSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 28, stiffness: 240 }}
              className="fixed left-0 top-0 bottom-0 z-50 w-[85vw] max-w-[280px] shadow-[16px_0_48px_rgba(0,0,0,0.9),4px_0_24px_rgba(60,182,151,0.18)] border-r border-[#3CB697]/30 bg-[#131620]"
            >
              <Sidebar onClose={() => setSidebarOpen(false)} className="w-full border-r-0 bg-[#131620]" />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── Main content area ─────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top nav bar */}
        <header className="h-14 flex items-center justify-between px-4 lg:px-6 border-b border-[rgba(60,182,151,0.07)] bg-[#0B0D12]/90 backdrop-blur-md sticky top-0 z-30">
          <div className="flex items-center gap-3">
            {/* 3-line hamburger toggle button */}
            <button
              className="p-2 rounded-xl hover:bg-[#1E2230] text-[#8A90A4] hover:text-[#3CB697] transition-all border border-[rgba(60,182,151,0.15)] hover:border-[#3CB697]/40 flex items-center justify-center cursor-pointer shadow-[0_0_12px_rgba(60,182,151,0.06)]"
              onClick={() => setSidebarOpen((o) => !o)}
              aria-label="Toggle navigation"
              title="Navigation Menu"
            >
              {sidebarOpen ? <X size={18} className="text-[#3CB697]" /> : <Menu size={18} className="text-[#3CB697]" />}
            </button>

            {/* Brand logo in top header */}
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-[#3CB697]/12 border border-[#3CB697]/25 flex items-center justify-center flex-shrink-0">
                <Shield size={16} className="text-[#3CB697]" />
              </div>
              <span
                className="text-sm font-bold text-[#E8E6DF] tracking-tight hidden sm:inline-block"
                style={{ fontFamily: 'var(--font-space-grotesk)' }}
              >
                ATS Fraud Detector
              </span>
            </div>

            {/* Page title breadcrumb */}
            {pageMeta && (
              <div className="hidden md:flex items-center gap-2 pl-3 border-l border-[rgba(60,182,151,0.12)]">
                <pageMeta.icon size={13} className="text-[#3CB697]" />
                <span className="text-xs font-semibold text-[#8A90A4]">{pageMeta.title}</span>
              </div>
            )}
          </div>

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
