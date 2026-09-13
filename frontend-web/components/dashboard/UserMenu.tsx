'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { LogOut, User, ChevronDown, Shield } from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { toast } from 'sonner';

export default function UserMenu() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleLogout = () => {
    clearAuth();
    toast.success('Signed out successfully');
    router.push('/auth');
  };

  const initials = user?.full_name
    ? user.full_name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()
    : user?.email?.[0]?.toUpperCase() ?? '?';

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-[#1E2230] transition-colors group"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        {/* Avatar */}
        <div className="w-7 h-7 rounded-full bg-[#3CB697]/15 border border-[#3CB697]/25 flex items-center justify-center text-xs font-bold text-[#3CB697]">
          {initials}
        </div>
        <div className="hidden sm:block text-left">
          <p className="text-xs font-medium text-[#E8E6DF] leading-none truncate max-w-[120px]">
            {user?.full_name ?? user?.email}
          </p>
          {user?.is_admin && (
            <p className="text-[10px] text-[#3CB697] font-mono mt-0.5">Admin</p>
          )}
        </div>
        <ChevronDown
          size={14}
          className={`text-[#7A8099] transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.96 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 w-56 rounded-xl bg-[#171A22] border border-[rgba(60,182,151,0.15)] shadow-xl z-50 overflow-hidden"
            role="menu"
          >
            {/* User info */}
            <div className="px-4 py-3 border-b border-[rgba(60,182,151,0.08)]">
              <p className="text-xs font-semibold text-[#E8E6DF] truncate">
                {user?.full_name || user?.email || 'Account'}
              </p>
              {user?.full_name && (
                <p className="text-[11px] text-[#7A8099] truncate mt-0.5">{user.email}</p>
              )}
              <div className="flex items-center gap-1.5 mt-1.5">
                <span className="text-[10px] font-mono text-[#3CB697] bg-[#3CB697]/10 border border-[#3CB697]/20 px-1.5 py-0.5 rounded">
                  {user?.organization || 'ATS Org'}
                </span>
                {user?.is_admin && (
                  <span className="text-[10px] font-mono text-[#8A90A4] bg-[#1E2230] px-1.5 py-0.5 rounded">
                    Admin
                  </span>
                )}
              </div>
            </div>

            {/* Profile link */}
            <button
              role="menuitem"
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#E8E6DF]/80 hover:text-[#3CB697] hover:bg-[#1E2230] transition-colors text-left"
              onClick={() => { setOpen(false); router.push('/dashboard/profile'); }}
            >
              <User size={14} />
              Profile & Account
            </button>

            {user?.is_admin && (
              <button
                role="menuitem"
                className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#E8E6DF]/80 hover:text-[#3CB697] hover:bg-[#1E2230] transition-colors text-left"
                onClick={() => { setOpen(false); router.push('/dashboard/settings'); }}
              >
                <Shield size={14} className="text-[#3CB697]" />
                Org Settings
              </button>
            )}

            {/* Logout */}
            <div className="border-t border-[rgba(60,182,151,0.08)]">
              <button
                role="menuitem"
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#E05252]/80 hover:text-[#E05252] hover:bg-[#E05252]/5 transition-colors text-left"
              >
                <LogOut size={14} />
                Sign out
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
