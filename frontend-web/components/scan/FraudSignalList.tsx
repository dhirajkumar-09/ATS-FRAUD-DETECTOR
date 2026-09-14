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
            <div className="space-y-2">
              {items.map((sig) => {
                const idx = absoluteIdx++;
                const isOpen = expandedIdx === idx;
                const strength = sig.evidence_strength ?? 'MODERATE';
                const riskPts = sig.risk_points;

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
                      className="w-full flex items-center gap-3 px-4 py-3.5 text-left group cursor-pointer"
                      aria-expanded={isOpen}
                    >
                      {/* Severity dot */}
                      <div
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: color }}
                      />

                      {/* Signal info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-sm font-semibold text-[#E8E6DF] truncate">
                            {sig.signal_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                          </p>
                          {strength && (
                            <span className={cn(
                              'text-[9px] font-mono px-1.5 py-0.5 rounded border font-semibold uppercase',
                              strength === 'DEFINITIVE' ? 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30' :
                              strength === 'STRONG'     ? 'bg-red-500/15 text-red-300 border-red-500/30' :
                              strength === 'MODERATE'   ? 'bg-amber-500/15 text-amber-300 border-amber-500/30' :
                              strength === 'PROBABILISTIC' ? 'bg-purple-500/15 text-purple-300 border-purple-500/30' :
                              'bg-slate-500/15 text-slate-300 border-slate-500/30'
                            )}>
                              {strength}
                            </span>
                          )}
                          {riskPts != null && riskPts > 0 && (
                            <span className="text-[10px] font-mono font-bold text-[#E05252] bg-[#E05252]/10 px-1.5 py-0.5 rounded border border-[#E05252]/20">
                              +{riskPts} risk pts
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-[#8A90A4] mt-1 leading-relaxed line-clamp-2">
                          {sig.description}
                        </p>
                      </div>

                      {/* Page badge */}
                      {sig.page != null && (
                        <span className="text-[10px] text-[#8A90A4] font-mono bg-[#1E2230] px-2 py-1 rounded flex-shrink-0">
                          p.{sig.page}
                        </span>
                      )}

                      {/* Expand chevron */}
                      <motion.div
                        animate={{ rotate: isOpen ? 180 : 0 }}
                        transition={{ duration: 0.2 }}
                        className="flex-shrink-0 text-[#8A90A4] group-hover:text-[#E8E6DF] transition-colors"
                      >
                        <ChevronDown size={14} />
                      </motion.div>
                    </button>

                    {/* Expanded detail & structured evidence */}
                    <AnimatePresence initial={false}>
                      {isOpen && (
                        <motion.div
                          key="detail"
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.22, ease: 'easeInOut' }}
                          className="overflow-hidden"
                        >
                          <div className={cn('px-4 pb-4 pt-3 border-t space-y-3', cfg.border.replace('border-', 'border-t-'))}>
                            {/* Evidence Metadata Bar */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono bg-[#0F1118] p-2.5 rounded-lg border border-white/5">
                              <div>
                                <span className="text-[#8A90A4] block text-[9px] uppercase">Evidence Strength</span>
                                <span className="font-semibold text-[#E8E6DF]">{strength}</span>
                              </div>
                              <div>
                                <span className="text-[#8A90A4] block text-[9px] uppercase">Confidence</span>
                                <span className="font-semibold text-[#E8E6DF]">{sig.confidence?.toUpperCase() ?? 'HIGH'}</span>
                              </div>
                              <div>
                                <span className="text-[#8A90A4] block text-[9px] uppercase">Risk Points</span>
                                <span className="font-semibold text-[#E05252]">+{riskPts ?? 0}</span>
                              </div>
                              <div>
                                <span className="text-[#8A90A4] block text-[9px] uppercase">Location</span>
                                <span className="font-semibold text-[#E8E6DF]">Page {sig.page ?? 1}</span>
                              </div>
                            </div>

                            {/* Full technical description */}
                            <div>
                              <span className="text-[10px] text-[#8A90A4] uppercase font-mono block mb-1">Technical Finding</span>
                              <p className="text-xs text-[#E8E6DF] leading-relaxed bg-[#131620] p-2.5 rounded border border-white/5">
                                {sig.description}
                              </p>
                            </div>

                            {/* Extracted evidence text */}
                            {sig.detail && (
                              <div>
                                <span className="text-[10px] text-[#8A90A4] uppercase font-mono block mb-1">Extracted Text Sample</span>
                                <div className="p-2.5 bg-[#0F1118] border border-white/5 rounded text-xs text-[#E8E6DF] font-mono break-words leading-relaxed max-h-[140px] overflow-y-auto">
                                  {sig.detail}
                                </div>
                              </div>
                            )}

                            {/* Structured Evidence Key/Value view if present */}
                            {sig.evidence && typeof sig.evidence === 'object' && Object.keys(sig.evidence).length > 0 && (
                              <div>
                                <span className="text-[10px] text-[#8A90A4] uppercase font-mono block mb-1">PDF Object Forensic Evidence</span>
                                <div className="bg-[#0F1118] border border-white/5 rounded p-2.5 text-[11px] font-mono space-y-1">
                                  {Object.entries(sig.evidence).map(([key, val]) => {
                                    if (key === 'characters' && Array.isArray(val)) {
                                      return (
                                        <div key={key} className="pt-1">
                                          <span className="text-[#8A90A4]">{key}:</span>
                                          <div className="pl-2 space-y-0.5 mt-0.5">
                                            {val.map((item: any, i: number) => (
                                              <div key={i} className="text-[#3CB697]">
                                                • {item.character} ({item.codepoint}) — {item.name}
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      );
                                    }
                                    if (key === 'suspect_chars' && Array.isArray(val)) {
                                      return (
                                        <div key={key} className="pt-1">
                                          <span className="text-[#8A90A4]">{key}:</span>
                                          <div className="pl-2 space-y-0.5 mt-0.5">
                                            {val.map((item: any, i: number) => (
                                              <div key={i} className="text-[#E09C52]">
                                                • {item.character} ({item.codepoint}): detected script {item.detected_script}, expected {item.expected_script}
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      );
                                    }
                                    return (
                                      <div key={key} className="flex justify-between border-b border-white/[0.03] pb-0.5">
                                        <span className="text-[#8A90A4]">{key}:</span>
                                        <span className="text-[#E8E6DF] max-w-[65%] truncate text-right font-medium">
                                          {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                                        </span>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}

                            {/* Remediation / Why it matters */}
                            {sig.remediation && (
                              <div className="bg-[#3CB697]/5 border border-[#3CB697]/20 p-2.5 rounded-lg">
                                <span className="text-[10px] text-[#3CB697] uppercase font-mono font-bold block mb-1">
                                  Why This Matters / Remediation
                                </span>
                                <p className="text-xs text-[#E8E6DF]/90 leading-relaxed">
                                  {sig.remediation}
                                </p>
                              </div>
                            )}
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
