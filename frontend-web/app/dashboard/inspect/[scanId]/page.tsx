'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Search, Loader2, AlertCircle } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { inspectScan } from '@/lib/api/scan';
import SpanInspector from '@/components/inspect/SpanInspector';
import type { InspectResult } from '@/lib/types';

export default function InspectPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const [data, setData] = useState<InspectResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId) return;
    setLoading(true);
    inspectScan(scanId)
      .then(setData)
      .catch((e) => {
        setError(
          e?.response?.data?.detail ?? 'Failed to load inspection data',
        );
      })
      .finally(() => setLoading(false));
  }, [scanId]);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center">
          <Search size={18} className="text-[#3CB697]" />
        </div>
        <div>
          <h1
            className="text-xl font-bold text-[#E8E6DF]"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            Span Inspector
          </h1>
          <p className="text-xs text-[#7A8099] mt-0.5 font-mono">
            scan/{scanId}
          </p>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="glass-card rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-3 mb-2">
            <Loader2 size={14} className="text-[#3CB697] animate-spin" />
            <span className="text-sm text-[#7A8099] font-mono">Loading inspection data…</span>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Skeleton className="h-96 bg-[#1E2230] rounded-xl" />
            <Skeleton className="h-96 bg-[#1E2230] rounded-xl" />
          </div>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-3 p-5 rounded-xl bg-[#E05252]/5 border border-[#E05252]/20"
        >
          <AlertCircle size={16} className="text-[#E05252] flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-[#E05252]">Failed to load</p>
            <p className="text-xs text-[#7A8099] mt-0.5">{error}</p>
          </div>
        </motion.div>
      )}

      {/* Inspector */}
      {data && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          <SpanInspector data={data} />
        </motion.div>
      )}
    </div>
  );
}
