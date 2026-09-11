'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, ArrowUpDown } from 'lucide-react';
import { getTrustColor, getTrustBadgeClass, formatPercent, cn } from '@/lib/utils';
import ScanResultPanel from '@/components/scan/ScanResultPanel';
import type { ScanResult } from '@/lib/types';

interface Props {
  results: ScanResult[];
}

type SortKey = 'trust_score' | 'ai_content_score' | 'true_match_score';

export default function BatchLeaderboard({ results }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('trust_score');
  const [sortAsc, setSortAsc] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const sorted = [...results].sort((a, b) => {
    const av = (a[sortKey] ?? 0) as number;
    const bv = (b[sortKey] ?? 0) as number;
    return sortAsc ? av - bv : bv - av;
  });

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc((a) => !a);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const SortHeader = ({ label, k }: { label: string; k: SortKey }) => (
    <button
      onClick={() => toggleSort(k)}
      className={cn(
        'flex items-center gap-1 text-xs font-medium uppercase tracking-widest transition-colors',
        sortKey === k ? 'text-[#3CB697]' : 'text-[#7A8099] hover:text-[#E8E6DF]',
      )}
    >
      {label}
      <ArrowUpDown size={10} />
    </button>
  );

  return (
    <div className="space-y-2">
      {/* Sort row */}
      <div className="flex items-center gap-4 px-4 py-2 rounded-lg bg-[#171A22] border border-[rgba(60,182,151,0.08)]">
        <span className="text-xs text-[#7A8099] mr-auto">{results.length} candidates</span>
        <SortHeader label="Trust" k="trust_score" />
        <SortHeader label="AI" k="ai_content_score" />
        <SortHeader label="Match" k="true_match_score" />
      </div>

      {/* Rows */}
      {sorted.map((r, rank) => {
        const isExpanded = expandedId === r.scan_id;
        const color = getTrustColor(r.trust_label);

        return (
          <motion.div
            key={r.scan_id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: rank * 0.04 }}
            className="rounded-xl overflow-hidden border border-[rgba(60,182,151,0.10)] bg-[#171A22]"
          >
            {/* Row header */}
            <button
              onClick={() => setExpandedId(isExpanded ? null : r.scan_id)}
              className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-[#1E2230] transition-colors text-left"
              aria-expanded={isExpanded}
            >
              {/* Rank */}
              <span
                className="text-sm font-bold font-mono w-6 flex-shrink-0"
                style={{ color: rank === 0 ? '#FFD700' : rank === 1 ? '#C0C0C0' : rank === 2 ? '#CD7F32' : '#7A8099' }}
              >
                #{rank + 1}
              </span>

              {/* Trust score bar */}
              <div className="w-16 h-1.5 rounded-full bg-[#0D0F14] overflow-hidden flex-shrink-0">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.round(r.trust_score * 100)}%` }}
                  transition={{ duration: 0.8, delay: rank * 0.05 }}
                  className="h-full rounded-full"
                  style={{ backgroundColor: color }}
                />
              </div>

              {/* Score */}
              <span
                className="text-sm font-bold font-mono w-10 flex-shrink-0"
                style={{ color }}
              >
                {Math.round(r.trust_score * 100)}
              </span>

              {/* Trust label badge */}
              <span
                className={cn(
                  'text-[10px] font-bold px-2 py-0.5 rounded-full border flex-shrink-0',
                  getTrustBadgeClass(r.trust_label),
                )}
              >
                {r.trust_label}
              </span>

              {/* Filename */}
              <span className="flex-1 text-sm text-[#E8E6DF] truncate min-w-0">
                {r.filename}
              </span>

              {/* Secondary scores */}
              <div className="hidden sm:flex items-center gap-4 flex-shrink-0 text-xs text-[#7A8099]">
                <span title="AI Content">{formatPercent(r.ai_content_score)}</span>
                <span title="Job Match">{r.true_match_score != null ? formatPercent(r.true_match_score) : '—'}</span>
              </div>

              {/* Signals count */}
              {r.fraud_signals?.length > 0 && (
                <span className="text-[10px] bg-[#E05252]/10 text-[#E05252] border border-[#E05252]/20 px-1.5 py-0.5 rounded-full flex-shrink-0">
                  {r.fraud_signals.length} flags
                </span>
              )}

              {isExpanded ? (
                <ChevronUp size={14} className="text-[#7A8099] flex-shrink-0" />
              ) : (
                <ChevronDown size={14} className="text-[#7A8099] flex-shrink-0" />
              )}
            </button>

            {/* Expanded detail */}
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.25 }}
                  className="overflow-hidden border-t border-[rgba(60,182,151,0.08)]"
                >
                  <div className="px-4 py-5">
                    <ScanResultPanel result={r} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );
      })}
    </div>
  );
}
