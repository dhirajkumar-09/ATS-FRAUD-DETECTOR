'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  History,
  Search,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  FileText,
  ScanLine,
} from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { getScanHistory } from '@/lib/api/scan';
import { formatDate, getTrustBadgeClass } from '@/lib/utils';
import type { ScanHistoryResponse, ScanHistoryItem } from '@/lib/types';

const PAGE_SIZE = 12;

type FilterTab = 'ALL' | 'Verified' | 'Caution' | 'High Risk';

export default function HistoryPage() {
  const [data, setData] = useState<ScanHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentTab, setCurrentTab] = useState<FilterTab>('ALL');
  const [offset, setOffset] = useState(0);

  const fetchHistory = (tab: FilterTab, currentOffset: number) => {
    setLoading(true);
    const filter = tab === 'ALL' ? undefined : tab;
    getScanHistory({ limit: PAGE_SIZE, offset: currentOffset, trust_label: filter })
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchHistory(currentTab, offset);
  }, [currentTab, offset]);

  const handleTabChange = (tab: FilterTab) => {
    setCurrentTab(tab);
    setOffset(0);
  };

  const total = data?.total ?? 0;
  const items: ScanHistoryItem[] = data?.items ?? [];
  const startIdx = total === 0 ? 0 : offset + 1;
  const endIdx = Math.min(offset + PAGE_SIZE, total);
  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* ── Page Header ──────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1
            className="text-2xl font-bold text-[#E8E6DF] tracking-tight flex items-center gap-2.5"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            <History size={22} className="text-[#3CB697]" />
            Scan History
          </h1>
          <p className="text-xs text-[#8A90A4] mt-1">
            Complete audit trail of all resumes submitted for ATS fraud analysis
          </p>
        </div>

        <Link
          href="/dashboard/scan"
          className="self-start sm:self-auto inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#3CB697] text-[#0B0D12] text-xs font-bold hover:bg-[#3CB697]/90 hover:shadow-[0_0_20px_rgba(60,182,151,0.3)] transition-all duration-200"
          style={{ fontFamily: 'var(--font-space-grotesk)' }}
        >
          <ScanLine size={13} />
          New Scan
        </Link>
      </div>

      {/* ── Filter Tabs ───────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2 border-b border-[rgba(60,182,151,0.08)] pb-3">
        {(['ALL', 'Verified', 'Caution', 'High Risk'] as FilterTab[]).map((tab) => {
          const isActive = currentTab === tab;
          return (
            <button
              key={tab}
              onClick={() => handleTabChange(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                isActive
                  ? 'bg-[#3CB697] text-[#0B0D12] shadow-[0_0_12px_rgba(60,182,151,0.25)]'
                  : 'text-[#8A90A4] hover:text-[#E8E6DF] hover:bg-[#1E2230]'
              }`}
            >
              {tab === 'ALL' ? 'All Scans' : tab}
              {data?.summary && tab !== 'ALL' && (
                <span
                  className={`ml-1.5 text-[10px] px-1.5 py-0.2 rounded-full ${
                    isActive ? 'bg-[#0B0D12]/20 text-[#0B0D12]' : 'bg-[#1E2230] text-[#8A90A4]'
                  }`}
                >
                  {data.summary.counts_by_label?.[tab] ?? 0}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ── History Table Card ────────────────────────────────────────────── */}
      <div className="glass-card rounded-2xl overflow-hidden border border-[rgba(60,182,151,0.12)]">
        <Table>
          <TableHeader className="bg-[#131620]/80">
            <TableRow className="border-b border-[rgba(60,182,151,0.08)] hover:bg-transparent">
              <TableHead className="text-xs text-[#8A90A4] font-medium py-3.5 px-4">Resume File</TableHead>
              <TableHead className="text-xs text-[#8A90A4] font-medium py-3.5 px-4">Date</TableHead>
              <TableHead className="text-xs text-[#8A90A4] font-medium py-3.5 px-4">Trust Verdict</TableHead>
              <TableHead className="text-xs text-[#8A90A4] font-medium py-3.5 px-4">AI Content</TableHead>
              <TableHead className="text-xs text-[#8A90A4] font-medium py-3.5 px-4">Match</TableHead>
              <TableHead className="text-xs text-[#8A90A4] font-medium py-3.5 px-4">Anomalies</TableHead>
              <TableHead className="text-xs text-[#8A90A4] font-medium py-3.5 px-4 text-right">Action</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i} className="border-b border-[rgba(60,182,151,0.06)]">
                  <TableCell className="py-3 px-4">
                    <Skeleton className="h-4 w-40 bg-[#1E2230]" />
                  </TableCell>
                  <TableCell className="py-3 px-4">
                    <Skeleton className="h-4 w-24 bg-[#1E2230]" />
                  </TableCell>
                  <TableCell className="py-3 px-4">
                    <Skeleton className="h-5 w-20 bg-[#1E2230] rounded-full" />
                  </TableCell>
                  <TableCell className="py-3 px-4">
                    <Skeleton className="h-4 w-12 bg-[#1E2230]" />
                  </TableCell>
                  <TableCell className="py-3 px-4">
                    <Skeleton className="h-4 w-12 bg-[#1E2230]" />
                  </TableCell>
                  <TableCell className="py-3 px-4">
                    <Skeleton className="h-4 w-16 bg-[#1E2230]" />
                  </TableCell>
                  <TableCell className="py-3 px-4 text-right">
                    <Skeleton className="h-6 w-16 bg-[#1E2230] ml-auto rounded-md" />
                  </TableCell>
                </TableRow>
              ))
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-12 text-center text-[#8A90A4]">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <FileText size={28} className="text-[#8A90A4]/40" />
                    <p className="text-sm font-medium">No scan results found</p>
                    <p className="text-xs text-[#8A90A4]/60">
                      {currentTab !== 'ALL'
                        ? `No scans matching the "${currentTab}" filter.`
                        : 'Submit a resume to generate your first audit record.'}
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => (
                <TableRow
                  key={item.scan_id}
                  className="border-b border-[rgba(60,182,151,0.06)] hover:bg-[#1E2230]/40 transition-colors group"
                >
                  <TableCell className="py-3.5 px-4 font-medium text-[#E8E6DF]">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <FileText size={15} className="text-[#3CB697] flex-shrink-0" />
                      <span className="truncate max-w-[220px] sm:max-w-xs">{item.filename}</span>
                    </div>
                  </TableCell>

                  <TableCell className="py-3.5 px-4 text-xs text-[#8A90A4] font-mono whitespace-nowrap">
                    {item.scanned_at ? formatDate(item.scanned_at) : '—'}
                  </TableCell>

                  <TableCell className="py-3.5 px-4 whitespace-nowrap">
                    <Badge
                      variant="outline"
                      className={`text-[11px] font-semibold tracking-wide capitalize px-2 py-0.5 ${getTrustBadgeClass(
                        item.trust_label || 'Unknown'
                      )}`}
                    >
                      {item.trust_label || 'Pending'} · {item.trust_score != null ? Math.round(item.trust_score) : 0}/100
                    </Badge>
                  </TableCell>

                  <TableCell className="py-3.5 px-4 text-xs font-mono text-[#8A90A4] whitespace-nowrap">
                    {item.ai_content_score != null ? `${Math.round(item.ai_content_score)}%` : '—'}
                  </TableCell>

                  <TableCell className="py-3.5 px-4 text-xs font-mono text-[#8A90A4] whitespace-nowrap">
                    {item.true_match_score != null ? `${Math.round(item.true_match_score)}%` : '—'}
                  </TableCell>

                  <TableCell className="py-3.5 px-4 text-xs whitespace-nowrap">
                    {item.high_count > 0 ? (
                      <span className="text-[#E05252] font-semibold">
                        {item.high_count} high / {item.total_signals} total
                      </span>
                    ) : (
                      <span className="text-[#8A90A4]">
                        {item.total_signals} total
                      </span>
                    )}
                  </TableCell>

                  <TableCell className="py-3.5 px-4 text-right whitespace-nowrap">
                    <Link
                      href={`/dashboard/inspect/${item.scan_id}`}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold text-[#8A90A4] hover:text-[#3CB697] hover:bg-[#1E2230] transition-colors"
                    >
                      <span>Inspect</span>
                      <ExternalLink size={12} />
                    </Link>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {/* ── Pagination Bar ──────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-[rgba(60,182,151,0.08)] bg-[#131620]/60 text-xs text-[#8A90A4]">
          <div>
            Showing <span className="text-[#E8E6DF] font-medium">{startIdx}</span> to{' '}
            <span className="text-[#E8E6DF] font-medium">{endIdx}</span> of{' '}
            <span className="text-[#E8E6DF] font-medium">{total}</span> scans
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={!hasPrev || loading}
              className="p-1.5 rounded-lg border border-[rgba(60,182,151,0.12)] disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#1E2230] text-[#E8E6DF] transition-colors"
              aria-label="Previous page"
            >
              <ChevronLeft size={15} />
            </button>
            <button
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={!hasNext || loading}
              className="p-1.5 rounded-lg border border-[rgba(60,182,151,0.12)] disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#1E2230] text-[#E8E6DF] transition-colors"
              aria-label="Next page"
            >
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
