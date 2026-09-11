'use client';

import { motion } from 'framer-motion';
import { ChevronDown, ChevronUp, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { useState } from 'react';
import { getSeverityBadgeClass, getSeverityColor, cn } from '@/lib/utils';
import type { FraudSignal } from '@/lib/types';

const SEVERITY_ORDER = { HIGH: 0, MEDIUM: 1, LOW: 2 };

const SeverityIcon = ({ severity }: { severity: string }) => {
  const s = severity?.toUpperCase();
  const color = getSeverityColor(s);
  if (s === 'HIGH') return <AlertTriangle size={14} style={{ color }} />;
  if (s === 'MEDIUM') return <AlertCircle size={14} style={{ color }} />;
  return <Info size={14} style={{ color }} />;
};

interface Props {
  signals: FraudSignal[];
  fraudSummary: string;
}

export default function FraudSignalList({ signals, fraudSummary }: Props) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  if (!signals?.length) {
    return (
      <div className="rounded-xl border border-[#3CB697]/15 bg-[#3CB697]/5 px-5 py-4">
        <p className="text-sm text-[#3CB697]">✓ No fraud signals detected</p>
      </div>
    );
  }

  // Group by severity
  const grouped = signals
    .slice()
    .sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 99) - (SEVERITY_ORDER[b.severity] ?? 99));

  const severityGroups: Record<string, FraudSignal[]> = {};
  grouped.forEach((s) => {
    const k = s.severity?.toUpperCase() ?? 'LOW';
    if (!severityGroups[k]) severityGroups[k] = [];
    severityGroups[k].push(s);
  });

  let absoluteIdx = 0;

  return (
    <div className="space-y-3">
      {/* Summary */}
      {fraudSummary && (
        <p className="text-sm text-[#7A8099] leading-relaxed">{fraudSummary}</p>
      )}

      {/* Signal groups */}
      {Object.entries(severityGroups).map(([severity, items]) => (
        <div key={severity}>
          <div className="flex items-center gap-2 mb-2">
            <SeverityIcon severity={severity} />
            <span
              className={cn('text-xs font-bold px-2 py-0.5 rounded-full', getSeverityBadgeClass(severity))}
            >
              {severity}
            </span>
            <span className="text-xs text-[#7A8099]">{items.length} signal{items.length > 1 ? 's' : ''}</span>
          </div>

          <div className="space-y-2 ml-4">
            {items.map((sig) => {
              const idx = absoluteIdx++;
              const isOpen = expandedIdx === idx;
              return (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className={cn(
                    'rounded-lg border bg-[#171A22] overflow-hidden transition-all',
                    'border-[rgba(60,182,151,0.1)] hover:border-[rgba(60,182,151,0.2)]',
                  )}
                >
                  <button
                    onClick={() => setExpandedIdx(isOpen ? null : idx)}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left"
                    aria-expanded={isOpen}
                  >
                    <div
                      className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: getSeverityColor(severity) }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-[#E8E6DF] font-medium truncate">
                        {sig.signal_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                      </p>
                      <p className="text-xs text-[#7A8099] mt-0.5 truncate">{sig.description}</p>
                    </div>
                    {sig.page != null && (
                      <span className="text-[10px] text-[#7A8099] font-mono flex-shrink-0">
                        p.{sig.page}
                      </span>
                    )}
                    {isOpen ? (
                      <ChevronUp size={14} className="text-[#7A8099] flex-shrink-0" />
                    ) : (
                      <ChevronDown size={14} className="text-[#7A8099] flex-shrink-0" />
                    )}
                  </button>

                  <motion.div
                    initial={false}
                    animate={{ height: isOpen ? 'auto' : 0, opacity: isOpen ? 1 : 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    {sig.detail && (
                      <div className="px-4 pb-3 border-t border-[rgba(60,182,151,0.08)]">
                        <p className="text-xs text-[#7A8099] leading-relaxed pt-2 font-mono">
                          {sig.detail}
                        </p>
                      </div>
                    )}
                  </motion.div>
                </motion.div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
