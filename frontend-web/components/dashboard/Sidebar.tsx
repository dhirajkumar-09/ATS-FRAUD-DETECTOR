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
  Rocket,
  History,
  X,
} from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';

type IconComponent = React.ComponentType<{ size?: number; className?: string; style?: React.CSSProperties }>;

const NAV_ITEMS = [
  { href: '/dashboard/scan',    label: 'Single Scan',    icon: ScanLine   },
  { href: '/dashboard/batch',   label: 'Batch Scan',     icon: LayoutList },
  { href: '/dashboard/inspect', label: 'Span Inspector', icon: Search     },
  { href: '/dashboard/history', label: 'Scan History',   icon: History    },
];

const PREVIEW_ITEMS = [
  { href: '/dashboard/roadmap', label: 'Future Roadmap', icon: Rocket },
];

const ADMIN_ITEMS = [
  { href: '/dashboard/settings', label: 'Org Settings', icon: Settings },
];

export default function Sidebar({
  onClose,
  className,
}: {
  onClose?: () => void;
  className?: string;
}) {
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
          'group relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200',
          isActive
            ? 'text-[#3CB697]'
            : 'text-[#8A90A4] hover:text-[#E8E6DF] hover:bg-[#1E2230]/70',
        )}
        aria-current={isActive ? 'page' : undefined}
      >
        {/* Active background */}
        {isActive && (
          <motion.div
            layoutId="sidebar-active"
            className="absolute inset-0 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/20"
            transition={{ type: 'spring', bounce: 0.15, duration: 0.35 }}
          />
        )}

        {/* Left accent line for active item */}
        {isActive && (
          <motion.div
            layoutId="sidebar-accent"
            className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-[#3CB697]"
            transition={{ type: 'spring', bounce: 0.15, duration: 0.35 }}
          />
        )}

        <Icon
          size={15}
          className={cn(
            'relative z-10 flex-shrink-0 transition-colors',
            isActive ? 'text-[#3CB697]' : 'group-hover:text-[#3CB697]/60',
          )}
        />
        <span className="relative z-10">{label}</span>
      </Link>
    );
  };

  return (
    <aside className={cn("flex flex-col h-full bg-[#0B0D12] border-r border-[rgba(60,182,151,0.08)] w-64", className)}>
      {/* Brand */}
      <div className="flex items-center justify-between px-5 py-5 border-b border-[rgba(60,182,151,0.08)]">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-[#3CB697]/12 border border-[#3CB697]/25 flex items-center justify-center flex-shrink-0">
            <Shield size={17} className="text-[#3CB697]" />
          </div>
          <div className="min-w-0">
            <p
              className="text-sm font-bold text-[#E8E6DF] leading-tight tracking-tight"
              style={{ fontFamily: 'var(--font-space-grotesk)' }}
            >
              ATS Fraud
            </p>
            <p className="text-[10px] text-[#3CB697] font-mono tracking-[0.18em] uppercase mt-0.5">
              Detector
            </p>
          </div>
        </div>

        {/* Mobile close (X) button */}
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#8A90A4] hover:text-[#E8E6DF] hover:bg-[#1E2230] transition-colors flex-shrink-0"
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto" aria-label="Main navigation">
        <p className="px-3 mb-1.5 text-[10px] font-semibold text-[#8A90A4]/70 uppercase tracking-[0.15em]">
          Forensics
        </p>
        <div className="space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.href} {...item} />
          ))}
        </div>

        <div className="mt-5 pt-4 border-t border-[rgba(60,182,151,0.07)]">
          <p className="px-3 mb-1.5 text-[10px] font-semibold text-[#8A90A4]/70 uppercase tracking-[0.15em]">
            Preview
          </p>
          <div className="space-y-0.5">
            {PREVIEW_ITEMS.map((item) => (
              <NavLink key={item.href} {...item} />
            ))}
          </div>
        </div>

        {user?.is_admin && (
          <div className="mt-5 pt-4 border-t border-[rgba(60,182,151,0.07)]">
            <p className="px-3 mb-1.5 text-[10px] font-semibold text-[#8A90A4]/70 uppercase tracking-[0.15em]">
              Admin
            </p>
            <div className="space-y-0.5">
              {ADMIN_ITEMS.map((item) => (
                <NavLink key={item.href} {...item} />
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* Footer org info */}
      <div className="px-4 py-4 border-t border-[rgba(60,182,151,0.07)]">
        <div className="flex items-center gap-2.5">
          <div className="w-1.5 h-1.5 rounded-full bg-[#3CB697] pulse-dot flex-shrink-0" />
          <p className="text-xs text-[#8A90A4] truncate font-medium">
            {user?.organization ?? 'Unknown org'}
          </p>
        </div>
      </div>
    </aside>
  );
}
