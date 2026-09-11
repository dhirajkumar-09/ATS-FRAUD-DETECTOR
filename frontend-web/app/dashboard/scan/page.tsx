'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ScanLine, Loader2, FileText } from 'lucide-react';
import { toast } from 'sonner';
import FileDropZone from '@/components/scan/FileDropZone';
import ScanResultPanel from '@/components/scan/ScanResultPanel';
import { Skeleton } from '@/components/ui/skeleton';
import { scanSingle } from '@/lib/api/scan';
import type { ScanResult } from '@/lib/types';

export default function ScanPage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);

  const handleScan = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await scanSingle(file, jobDescription);
      setResult(res);
      toast.success('Scan complete!');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Scan failed. Please try again.';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center">
          <ScanLine size={18} className="text-[#3CB697]" />
        </div>
        <div>
          <h1
            className="text-xl font-bold text-[#E8E6DF]"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            Single Resume Scan
          </h1>
          <p className="text-xs text-[#7A8099] mt-0.5">
            Upload one PDF to run a full forensic analysis
          </p>
        </div>
      </div>

      {/* Upload card */}
      <div className="glass-card rounded-xl p-5 space-y-4">
        <FileDropZone
          file={file}
          onFile={setFile}
          onClear={() => { setFile(null); setResult(null); }}
        />

        {/* Job description */}
        <div className="space-y-1.5">
          <label className="text-xs text-[#7A8099] font-medium" htmlFor="job-desc">
            Job description{' '}
            <span className="text-[#7A8099]/60">(optional — enables job match scoring)</span>
          </label>
          <textarea
            id="job-desc"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the job description here…"
            rows={4}
            className="w-full px-4 py-3 rounded-lg text-sm bg-[#0D0F14] border border-[rgba(60,182,151,0.15)] text-[#E8E6DF] placeholder:text-[#7A8099] outline-none resize-none transition-all focus:border-[#3CB697] focus:ring-2 focus:ring-[#3CB697]/15"
          />
        </div>

        {/* Scan button */}
        <motion.button
          onClick={handleScan}
          disabled={!file || loading}
          whileHover={{ scale: (!file || loading) ? 1 : 1.01 }}
          whileTap={{ scale: (!file || loading) ? 1 : 0.98 }}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold bg-[#3CB697] text-[#0D0F14] hover:bg-[#3CB697]/90 hover:shadow-[0_0_24px_rgba(60,182,151,0.3)] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
          style={{ fontFamily: 'var(--font-space-grotesk)' }}
        >
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Analyzing resume…
            </>
          ) : (
            <>
              <ScanLine size={16} />
              Run Forensic Scan
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
            className="glass-card rounded-xl p-5 space-y-4"
          >
            <div className="flex items-center gap-3 mb-4">
              <Loader2 size={16} className="text-[#3CB697] animate-spin" />
              <span className="text-sm text-[#7A8099] font-mono">
                Running forensic analysis…
              </span>
            </div>
            <div className="flex gap-6">
              <Skeleton className="w-40 h-40 rounded-full bg-[#1E2230]" />
              <div className="flex-1 space-y-3">
                <Skeleton className="h-4 w-3/4 bg-[#1E2230]" />
                <Skeleton className="h-4 w-1/2 bg-[#1E2230]" />
                <Skeleton className="h-12 w-full bg-[#1E2230] rounded-lg" />
                <Skeleton className="h-12 w-full bg-[#1E2230] rounded-lg" />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results */}
      <AnimatePresence>
        {result && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            <ScanResultPanel result={result} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Empty state */}
      {!file && !result && !loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center gap-3 py-10 text-center"
        >
          <div className="w-14 h-14 rounded-xl bg-[#171A22] border border-[rgba(60,182,151,0.1)] flex items-center justify-center">
            <FileText size={22} className="text-[#7A8099]" />
          </div>
          <p className="text-sm text-[#7A8099]">Upload a resume PDF to get started</p>
        </motion.div>
      )}
    </div>
  );
}
