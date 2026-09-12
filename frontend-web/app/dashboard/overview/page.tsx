'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion, type Variants } from 'framer-motion';
import {
  ScanLine,
  ShieldCheck,
  AlertTriangle,
  ShieldAlert,
  Gauge,
  ArrowRight,
  ExternalLink,
  History,
  FileText,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { getScanHistory } from '@/lib/api/scan';
import { formatDate, getTrustBadgeClass } from '@/lib/utils';
import type { ScanHistoryResponse, ScanHistoryItem } from '@/lib/types';

const containerVariants: Variants = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.08,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: 'easeOut' },
  },
};

export default function DashboardOverviewPage() {
  const [data, setData] = useState<ScanHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    getScanHistory({ limit: 5, offset: 0 })
      .then((res) => {
        if (mounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const summary = data?.summary;
  const recentScans: ScanHistoryItem[] = data?.items || [];
  const totalScans = summary?.total_scans ?? 0;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* ── Top Header Banner ────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1
            className="text-2xl font-bold text-[#E8E6DF] tracking-tight"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            Forensic Overview
          </h1>
          <p className="text-xs text-[#8A90A4] mt-1">
            Real-time telemetry and audit breakdown for your candidate pipeline
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/history"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-[#8A90A4] hover:text-[#E8E6DF] hover:bg-[#1E2230] border border-[rgba(60,182,151,0.12)] transition-colors"
          >
            <History size={13} />
            All History
          </Link>
          <Link
            href="/dashboard/scan"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#3CB697] text-[#0B0D12] text-xs font-bold hover:bg-[#3CB697]/90 hover:shadow-[0_0_20px_rgba(60,182,151,0.3)] transition-all duration-200"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            <ScanLine size={13} />
            New Scan
          </Link>
        </div>
      </div>

      {/* ── Metric Stat Cards ─────────────────────────────────────────────── */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-2xl bg-[#131620] border border-[rgba(60,182,151,0.08)]" />
          ))}
        </div>
      ) : (
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5"
        >
          {/* Total Resumes */}
          <motion.div variants={itemVariants}>
            <Card className="bg-[#131620]/80 border-[rgba(60,182,151,0.12)] rounded-2xl">
              <CardHeader className="p-4 pb-1">
                <CardTitle className="text-xs font-medium text-[#8A90A4] flex items-center justify-between">
                  <span>Total Scans</span>
                  <ScanLine size={14} className="text-[#8A90A4]" />
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-1">
                <div
                  className="text-2xl font-bold text-[#E8E6DF]"
                  style={{ fontFamily: 'var(--font-space-grotesk)' }}
                >
                  {totalScans}
                </div>
                <p className="text-[10px] text-[#8A90A4]/70 mt-1">Processed resumes</p>
              </CardContent>
            </Card>
          </motion.div>

          {/* Verified */}
          <motion.div variants={itemVariants}>
            <Card className="bg-[#131620]/80 border-[rgba(60,182,151,0.12)] rounded-2xl">
              <CardHeader className="p-4 pb-1">
                <CardTitle className="text-xs font-medium text-[#3CB697] flex items-center justify-between">
                  <span>Verified</span>
                  <ShieldCheck size={14} className="text-[#3CB697]" />
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-1">
                <div
                  className="text-2xl font-bold text-[#3CB697]"
                  style={{ fontFamily: 'var(--font-space-grotesk)' }}
                >
                  {summary?.counts_by_label?.Verified ?? 0}
                </div>
                <p className="text-[10px] text-[#8A90A4]/70 mt-1">Clean forensics</p>
              </CardContent>
            </Card>
          </motion.div>

          {/* Caution */}
          <motion.div variants={itemVariants}>
            <Card className="bg-[#131620]/80 border-[rgba(60,182,151,0.12)] rounded-2xl">
              <CardHeader className="p-4 pb-1">
                <CardTitle className="text-xs font-medium text-[#E09C52] flex items-center justify-between">
                  <span>Caution</span>
                  <AlertTriangle size={14} className="text-[#E09C52]" />
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-1">
                <div
                  className="text-2xl font-bold text-[#E09C52]"
                  style={{ fontFamily: 'var(--font-space-grotesk)' }}
                >
                  {summary?.counts_by_label?.Caution ?? 0}
                </div>
                <p className="text-[10px] text-[#8A90A4]/70 mt-1">Suspicious anomalies</p>
              </CardContent>
            </Card>
          </motion.div>

          {/* High Risk */}
          <motion.div variants={itemVariants}>
            <Card className="bg-[#131620]/80 border-[rgba(60,182,151,0.12)] rounded-2xl">
              <CardHeader className="p-4 pb-1">
                <CardTitle className="text-xs font-medium text-[#E05252] flex items-center justify-between">
                  <span>High Risk</span>
                  <ShieldAlert size={14} className="text-[#E05252]" />
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-1">
                <div
                  className="text-2xl font-bold text-[#E05252]"
                  style={{ fontFamily: 'var(--font-space-grotesk)' }}
                >
                  {summary?.counts_by_label?.['High Risk'] ?? 0}
                </div>
                <p className="text-[10px] text-[#8A90A4]/70 mt-1">Confirmed fraud</p>
              </CardContent>
            </Card>
          </motion.div>

          {/* Average Trust Score */}
          <motion.div variants={itemVariants} className="col-span-2 sm:col-span-1">
            <Card className="bg-[#131620]/80 border-[rgba(60,182,151,0.12)] rounded-2xl">
              <CardHeader className="p-4 pb-1">
                <CardTitle className="text-xs font-medium text-[#8A90A4] flex items-center justify-between">
                  <span>Avg Trust Score</span>
                  <Gauge size={14} className="text-[#3CB697]" />
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-1">
                <div
                  className="text-2xl font-bold text-[#E8E6DF]"
                  style={{ fontFamily: 'var(--font-space-grotesk)' }}
                >
                  {summary?.average_trust_score ?? 0}
                  <span className="text-xs font-normal text-[#8A90A4] ml-1">/ 100</span>
                </div>
                <p className="text-[10px] text-[#8A90A4]/70 mt-1">Across all scans</p>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      )}

      {/* ── Recent Scans Section ──────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2
            className="text-base font-bold text-[#E8E6DF] flex items-center gap-2"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            Recent Forensic Audits
          </h2>
          {totalScans > 5 && (
            <Link
              href="/dashboard/history"
              className="text-xs text-[#3CB697] hover:underline flex items-center gap-1"
            >
              View all {totalScans} scans <ArrowRight size={11} />
            </Link>
          )}
        </div>

        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-xl bg-[#131620] border border-[rgba(60,182,151,0.08)]" />
            ))}
          </div>
        ) : totalScans === 0 ? (
          /* ── Empty State ── */
          <div className="glass-card rounded-2xl p-10 text-center flex flex-col items-center justify-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-[#1E2230] border border-[rgba(60,182,151,0.2)] flex items-center justify-center shadow-[0_0_20px_rgba(60,182,151,0.1)]">
              <FileText size={24} className="text-[#3CB697]" />
            </div>
            <div>
              <h3
                className="text-base font-semibold text-[#E8E6DF]"
                style={{ fontFamily: 'var(--font-space-grotesk)' }}
              >
                No resumes scanned yet
              </h3>
              <p className="text-xs text-[#8A90A4] max-w-sm mt-1 mx-auto leading-relaxed">
                Run your first forensic scan to detect hidden white text, homoglyphs, and AI-generated content.
              </p>
            </div>
            <Link
              href="/dashboard/scan"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#3CB697] text-[#0B0D12] text-xs font-bold hover:bg-[#3CB697]/90 hover:shadow-[0_0_24px_rgba(60,182,151,0.3)] transition-all duration-200"
              style={{ fontFamily: 'var(--font-space-grotesk)' }}
            >
              <ScanLine size={14} />
              Run Your First Scan
            </Link>
          </div>
        ) : (
          /* ── Compact Recent Rows ── */
          <div className="space-y-2.5">
            {recentScans.map((scan) => (
              <div
                key={scan.scan_id}
                className="glass-card rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-[#3CB697]/30 transition-all duration-200 group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-[#1E2230] border border-[rgba(60,182,151,0.15)] flex items-center justify-center flex-shrink-0">
                    <FileText size={16} className="text-[#3CB697]" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-[#E8E6DF] truncate group-hover:text-[#3CB697] transition-colors">
                      {scan.filename}
                    </p>
                    <p className="text-[11px] text-[#8A90A4] font-mono mt-0.5">
                      {scan.scanned_at ? formatDate(scan.scanned_at) : 'Just now'} · {scan.total_signals} anomalies
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4 shrink-0 self-end sm:self-center">
                  {/* Trust Badge */}
                  <Badge
                    variant="outline"
                    className={`text-[11px] font-semibold tracking-wide capitalize px-2.5 py-0.5 ${getTrustBadgeClass(
                      scan.trust_label || 'Unknown'
                    )}`}
                  >
                    {scan.trust_label || 'Pending'} · {scan.trust_score != null ? Math.round(scan.trust_score) : 0}%
                  </Badge>

                  {/* Direct Inspect Action */}
                  <Link
                    href={`/dashboard/inspect/${scan.scan_id}`}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold text-[#8A90A4] hover:text-[#E8E6DF] hover:bg-[#1E2230] transition-colors"
                  >
                    <span>Inspect</span>
                    <ExternalLink size={12} />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
