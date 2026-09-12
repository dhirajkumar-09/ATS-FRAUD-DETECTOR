'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, AlertTriangle, AlertCircle, Info, CheckCircle2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useState } from 'react';
import { getSeverityColor, cn } from '@/lib/utils';
import type { FraudSignal } from '@/lib/types';

const SEVERITY_ORDER: Record<string, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };

const SEVERITY_CONFIG: Record<string, {
  icon: LucideIcon;
  bg: string;
  border: string;
  badge: string;
}> = {
  HIGH: {
    icon: AlertTriangle,
    bg:     'bg-[#E05252]/8',
    border: 'border-[#E05252]/25',
    badge:  'bg-[#E05252]/12 text-[#E05252] border-[#E05252]/25',
  },
  MEDIUM: {
    icon: AlertCircle,
    bg:     'bg-[#E09C52]/6',
    border: 'border-[#E09C52]/22',
    badge:  'bg-[#E09C52]/10 text-[#E09C52] border-[#E09C52]/22',
  },
  LOW: {
    icon: Info,
    bg:     'bg-[#3CB697]/5',
    border: 'border-[#3CB697]/18',
    badge:  'bg-[#3CB697]/8 text-[#3CB697] border-[#3CB697]/20',
  },
};

interface Props {
  signals: FraudSignal[];
  fraudSummary: string;
}

export default function FraudSignalList({ signals, fraudSummary }: Props) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  if (!signals?.length) {
    return (
      <div className="flex flex-col items-center gap-3 py-10 text-center">
        <div className="w-12 h-12 rounded-2xl bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center">
          <CheckCircle2 size={20} className="text-[#3CB697]" />
        </div>
        <div>
          <p className="text-sm font-semibold text-[#3CB697]">No fraud signals detected</p>
          <p className="text-xs text-[#8A90A4] mt-1">This resume appears clean</p>
        </div>
      </div>
    );
  }

  // Sort and group by severity
  const sorted = signals
    .slice()
    .sort((a, b) => (SEVERITY_ORDER[a.severity?.toUpperCase()] ?? 99) - (SEVERITY_ORDER[b.severity?.toUpperCase()] ?? 99));

  const groups: Record<string, FraudSignal[]> = {};
  sorted.forEach((s) => {
    const k = s.severity?.toUpperCase() ?? 'LOW';
    if (!groups[k]) groups[k] = [];
    groups[k].push(s);
  });

  let absoluteIdx = 0;

  return (
    <div className="space-y-4">
      {/* Summary text */}
      {fraudSummary && (
        <p className="text-sm text-[#8A90A4] leading-relaxed">{fraudSummary}</p>
      )}

      {/* Signal groups */}
      {Object.entries(groups).map(([severity, items]) => {
        const cfg = SEVERITY_CONFIG[severity] ?? SEVERITY_CONFIG.LOW;
        const SevIcon = cfg.icon;
        const color = getSeverityColor(severity);

        return (
          <div key={severity} className="space-y-1.5">
            {/* Group header */}
            <div className="flex items-center gap-2 px-1 mb-2">
              <SevIcon size={13} style={{ color }} />
              <span className={cn('text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-[0.1em]', cfg.badge)}>
                {severity}
              </span>
              <span className="text-xs text-[#8A90A4]">
                {items.length} signal{items.length > 1 ? 's' : ''}
              </span>
            </div>

            {/* Signal cards */}
            <div className="space-y-1.5">
              {items.map((sig) => {
                const idx = absoluteIdx++;
                const isOpen = expandedIdx === idx;
                const hasDetail = !!(sig.detail);

                return (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.04, duration: 0.28 }}
                    className={cn(
                      'rounded-xl border overflow-hidden transition-colors',
                      isOpen
                        ? cn('bg-[#181B25]', cfg.border)
                        : 'bg-[#131620] border-[rgba(60,182,151,0.10)] hover:border-[rgba(60,182,151,0.20)]',
                    )}
                  >
                    <button
                      onClick={() => setExpandedIdx(isOpen ? null : idx)}
                      disabled={!hasDetail}
                      className="w-full flex items-center gap-3 px-4 py-3.5 text-left group"
                      aria-expanded={isOpen}
                    >
                      {/* Severity dot */}
                      <div
                        className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-0.5"
                        style={{ backgroundColor: color }}
                      />

                      {/* Signal info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-[#E8E6DF] truncate">
                          {sig.signal_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                        </p>
                        <p className="text-xs text-[#8A90A4] mt-0.5 leading-relaxed line-clamp-2">
                          {sig.description}
                        </p>
                      </div>

                      {/* Page badge */}
                      {sig.page != null && (
                        <span className="text-[10px] text-[#8A90A4] font-mono bg-[#1E2230] px-1.5 py-0.5 rounded flex-shrink-0">
                          p.{sig.page}
                        </span>
                      )}

                      {/* Expand chevron */}
                      {hasDetail && (
                        <motion.div
                          animate={{ rotate: isOpen ? 180 : 0 }}
                          transition={{ duration: 0.2 }}
                          className="flex-shrink-0 text-[#8A90A4] group-hover:text-[#E8E6DF] transition-colors"
                        >
                          <ChevronDown size={14} />
                        </motion.div>
                      )}
                    </button>

                    {/* Expanded detail */}
                    <AnimatePresence initial={false}>
                      {isOpen && hasDetail && (
                        <motion.div
                          key="detail"
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.22, ease: 'easeInOut' }}
                          className="overflow-hidden"
                        >
                          <div className={cn('px-4 pb-4 pt-3 border-t', cfg.border.replace('border-', 'border-t-'))}>
                            <p className="text-xs text-[#8A90A4] leading-relaxed font-mono">
                              {sig.detail}
                            </p>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
