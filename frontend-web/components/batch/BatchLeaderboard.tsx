'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';
import { getTrustColor, getTrustBadgeClass, formatPercent, cn } from '@/lib/utils';
import ScanResultPanel from '@/components/scan/ScanResultPanel';
import type { ScanResult, DuplicateMatch } from '@/lib/types';

interface Props {
  results: ScanResult[];
  duplicates?: DuplicateMatch[];
}

type SortKey = 'trust_score' | 'ai_content_score' | 'true_match_score';

export default function BatchLeaderboard({ results, duplicates }: Props) {
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

  const renderSortHeader = (label: string, k: SortKey) => (
    <button
      onClick={() => toggleSort(k)}
      className="flex items-center gap-1.5 min-w-[80px] text-xs font-semibold text-[#8A90A4] uppercase tracking-wider hover:text-[#E8E6DF] transition-colors"
    >
      {label}
      <div className="flex flex-col -space-y-[3px] opacity-40">
        <ChevronUp size={10} className={sortKey === k && sortAsc ? 'text-[#3CB697] opacity-100' : ''} />
        <ChevronDown size={10} className={sortKey === k && !sortAsc ? 'text-[#3CB697] opacity-100' : ''} />
      </div>
    </button>
  );

  return (
    <div className="space-y-2">
      {/* Sort row */}
      <div className="flex items-center gap-4 px-4 py-2 rounded-lg bg-[#171A22] border border-[rgba(60,182,151,0.08)]">
        <span className="text-xs text-[#7A8099] mr-auto">{results.length} candidates</span>
        {renderSortHeader('Trust', 'trust_score')}
        {renderSortHeader('AI', 'ai_content_score')}
        {renderSortHeader('Match', 'true_match_score')}
      </div>

      {/* Rows */}
      {sorted.map((r, rank) => {
        const isExpanded = expandedId === String(r.scan_id);
        const color = getTrustColor(r.trust_label);

        // Find if this candidate is part of a duplicate match
        const dupMatch = duplicates?.find(
          (d) => String(d.scan_id_a) === String(r.scan_id) || String(d.scan_id_b) === String(r.scan_id)
        );

        return (
          <motion.div
            key={r.scan_id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: rank * 0.04 }}
            className={cn(
              "rounded-xl overflow-hidden border bg-[#171A22] transition-colors",
              dupMatch ? "border-[#F59E0B]/30" : "border-[rgba(60,182,151,0.10)]"
            )}
          >
            {/* Row header */}
            <button
              onClick={() => setExpandedId(isExpanded ? null : String(r.scan_id))}
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

              {/* Filename and warning */}
              <div className="flex-1 min-w-0 flex flex-col justify-center">
                <span className="text-sm text-[#E8E6DF] truncate">
                  {r.filename}
                </span>
                {dupMatch && (
                  <div className="flex items-center gap-1 mt-0.5 text-[11px] text-[#F59E0B]">
                    <AlertTriangle size={10} />
                    <span>{dupMatch.similarity_score}% template reuse detected</span>
                  </div>
                )}
              </div>

              {/* Secondary scores */}
              <div className="hidden sm:flex items-center gap-4 flex-shrink-0 text-xs text-[#7A8099]">
                <span title="AI Content">{formatPercent(r.ai_content_score)}</span>
                <span title="Job Match">{r.true_match_score != null ? formatPercent(r.true_match_score) : '—'}</span>
              </div>

              {/* Signals count */}
              {(r.fraud_signals?.length > 0 || dupMatch) && (
                <span className="text-[10px] bg-[#E05252]/10 text-[#E05252] border border-[#E05252]/20 px-1.5 py-0.5 rounded-full flex-shrink-0">
                  {r.fraud_signals?.length ?? 1} flags
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
                  <div className="px-4 py-5 space-y-4">
                    {dupMatch && (
                      <div className="p-4 rounded-lg bg-[#F59E0B]/10 border border-[#F59E0B]/20">
                        <div className="flex items-center gap-2 text-[#F59E0B] font-semibold mb-2 text-sm">
                          <AlertTriangle size={16} />
                          Cross-Resume Plagiarism Detected ({dupMatch.similarity_score}% match)
                        </div>
                        <p className="text-xs text-[#E8E6DF] mb-3">
                          This candidate shares an unusually high amount of text with another applicant in this batch. Shared phrases include:
                        </p>
                        <ul className="list-disc pl-5 space-y-1 text-xs text-[#7A8099] font-mono">
                          {dupMatch.shared_phrases.map((p, i) => (
                            <li key={i}>{p}</li>
                          ))}
                        </ul>
                      </div>
                    )}
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
