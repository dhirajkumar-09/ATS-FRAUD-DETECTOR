'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  ScanLine,
  LayoutList,
  Search,
  Settings,
  Shield,
  ChevronRight,
} from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';

type IconComponent = React.ComponentType<{ size?: number; className?: string; style?: React.CSSProperties }>;

const NAV_ITEMS = [
  { href: '/dashboard/scan', label: 'Single Scan', icon: ScanLine },
  { href: '/dashboard/batch', label: 'Batch Scan', icon: LayoutList },
];

const ADMIN_ITEMS = [
  { href: '/dashboard/settings', label: 'Org Settings', icon: Settings },
];

export default function Sidebar({ onClose }: { onClose?: () => void }) {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);

  const NavLink = ({
    href,
    label,
    icon: Icon,
  }: {
    href: string;
    label: string;
    icon: IconComponent;
  }) => {
    const isActive = pathname === href || pathname.startsWith(href + '/');
    return (
      <Link
        href={href}
        onClick={onClose}
        className={cn(
          'group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 relative',
          isActive
            ? 'bg-[#3CB697]/10 text-[#3CB697] border border-[#3CB697]/20'
            : 'text-[#7A8099] hover:text-[#E8E6DF] hover:bg-[#1E2230]',
        )}
        aria-current={isActive ? 'page' : undefined}
      >
        {isActive && (
          <motion.div
            layoutId="sidebar-active"
            className="absolute inset-0 rounded-lg bg-[#3CB697]/8 border border-[#3CB697]/20"
            transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
          />
        )}
        <Icon
          size={16}
          className={cn('relative z-10 transition-colors', isActive ? 'text-[#3CB697]' : 'group-hover:text-[#3CB697]/70')}
        />
        <span className="relative z-10 font-medium">{label}</span>
        {isActive && (
          <ChevronRight size={12} className="relative z-10 ml-auto text-[#3CB697]/50" />
        )}
      </Link>
    );
  };

  return (
    <aside className="flex flex-col h-full bg-[#0D0F14] border-r border-[rgba(60,182,151,0.10)] w-64">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-5 py-6 border-b border-[rgba(60,182,151,0.08)]">
        <div className="w-8 h-8 rounded-lg bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center">
          <Shield size={16} className="text-[#3CB697]" />
        </div>
        <div>
          <p
            className="text-sm font-bold text-[#E8E6DF] leading-none"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            ATS Fraud
          </p>
          <p className="text-[10px] text-[#3CB697] font-mono mt-0.5 tracking-widest uppercase">
            Detector
          </p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" aria-label="Main navigation">
        <p className="px-3 mb-2 text-[10px] font-semibold text-[#7A8099] uppercase tracking-widest">
          Forensics
        </p>
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.href} {...item} />
        ))}

        {/* Inspect link — only shows if we have a scan context */}
        <NavLink
          href="/dashboard/inspect"
          label="Span Inspector"
          icon={Search}
        />

        {user?.is_admin && (
          <>
            <div className="pt-4 pb-2">
              <p className="px-3 mb-2 text-[10px] font-semibold text-[#7A8099] uppercase tracking-widest">
                Admin
              </p>
              {ADMIN_ITEMS.map((item) => (
                <NavLink key={item.href} {...item} />
              ))}
            </div>
          </>
        )}
      </nav>

      {/* Footer org info */}
      <div className="px-4 py-4 border-t border-[rgba(60,182,151,0.08)]">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#3CB697] animate-pulse" />
          <p className="text-xs text-[#7A8099] truncate">
            {user?.organization ?? 'Unknown org'}
          </p>
        </div>
      </div>
    </aside>
  );
}
