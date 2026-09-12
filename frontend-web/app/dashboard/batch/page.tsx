'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutList, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import BatchDropZone from '@/components/batch/BatchDropZone';
import BatchLeaderboard from '@/components/batch/BatchLeaderboard';
import { Skeleton } from '@/components/ui/skeleton';
import { scanBatch } from '@/lib/api/scan';
import type { ScanResult, DuplicateMatch } from '@/lib/types';

export default function BatchPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ScanResult[] | null>(null);
  const [duplicates, setDuplicates] = useState<DuplicateMatch[]>([]);

  const addFiles = (incoming: File[]) => {
    setFiles((prev) => [...prev, ...incoming]);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleBatchScan = async () => {
    if (files.length === 0) return;
    setLoading(true);
    setResults(null);
    setDuplicates([]);
    try {
      const res = await scanBatch(files, jobDescription);
      setResults(res.results);
      setDuplicates(res.duplicates);
      toast.success(`Batch complete — ${res.results.length} candidates ranked`);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Batch scan failed. Please try again.';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center">
          <LayoutList size={18} className="text-[#3CB697]" />
        </div>
        <div>
          <h1
            className="text-xl font-bold text-[#E8E6DF]"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            Batch Resume Scan
          </h1>
          <p className="text-xs text-[#7A8099] mt-0.5">
            Upload multiple PDFs — results ranked by trust score
          </p>
        </div>
      </div>

      {/* Upload card */}
      <div className="glass-card rounded-xl p-5 space-y-4">
        <BatchDropZone files={files} onAdd={addFiles} onRemove={removeFile} />

        {/* Job description */}
        <div className="space-y-1.5">
          <label className="text-xs text-[#7A8099] font-medium" htmlFor="batch-jd">
            Job description{' '}
            <span className="text-[#7A8099]/60">(optional — enables match scoring across all candidates)</span>
          </label>
          <textarea
            id="batch-jd"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the job description here…"
            rows={3}
            className="w-full px-4 py-3 rounded-lg text-sm bg-[#0D0F14] border border-[rgba(60,182,151,0.15)] text-[#E8E6DF] placeholder:text-[#7A8099] outline-none resize-none transition-all focus:border-[#3CB697] focus:ring-2 focus:ring-[#3CB697]/15"
          />
        </div>

        {/* Scan button */}
        <motion.button
          onClick={handleBatchScan}
          disabled={files.length === 0 || loading}
          whileHover={{ scale: files.length === 0 || loading ? 1 : 1.01 }}
          whileTap={{ scale: files.length === 0 || loading ? 1 : 0.98 }}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold bg-[#3CB697] text-[#0D0F14] hover:bg-[#3CB697]/90 hover:shadow-[0_0_24px_rgba(60,182,151,0.3)] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
          style={{ fontFamily: 'var(--font-space-grotesk)' }}
        >
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Scanning {files.length} resume{files.length > 1 ? 's' : ''}…
            </>
          ) : (
            <>
              <LayoutList size={16} />
              Scan {files.length > 0 ? `${files.length} Resume${files.length > 1 ? 's' : ''}` : 'Resumes'}
            </>
          )}
        </motion.button>
      </div>

      {/* Loading skeleton */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="glass-card rounded-xl p-5 space-y-3"
          >
            <div className="flex items-center gap-3 mb-2">
              <Loader2 size={14} className="text-[#3CB697] animate-spin" />
              <span className="text-sm text-[#7A8099] font-mono">
                Running batch analysis… this may take a moment
              </span>
            </div>
            {Array.from({ length: files.length }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full bg-[#1E2230] rounded-lg" />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results */}
      <AnimatePresence>
        {results && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            <div className="flex items-center justify-between mb-4">
              <h2
                className="text-sm font-bold text-[#E8E6DF]"
                style={{ fontFamily: 'var(--font-space-grotesk)' }}
              >
                Candidate Leaderboard
              </h2>
              <button
                onClick={() => { setResults(null); setFiles([]); }}
                className="text-xs text-[#7A8099] hover:text-[#E8E6DF] transition-colors"
              >
                Clear results
              </button>
            </div>
            <BatchLeaderboard results={results} duplicates={duplicates} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
