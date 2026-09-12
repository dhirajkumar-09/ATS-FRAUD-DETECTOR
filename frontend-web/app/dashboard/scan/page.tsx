'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ScanLine, Loader2, FileText, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import FileDropZone from '@/components/scan/FileDropZone';
import ScanResultPanel from '@/components/scan/ScanResultPanel';
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
      toast.success('Forensic scan complete!');
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

      {/* Upload card */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card rounded-2xl p-5 sm:p-6 space-y-5"
      >
        <FileDropZone
          file={file}
          onFile={setFile}
          onClear={() => { setFile(null); setResult(null); }}
        />

        {/* Job description */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-xs font-semibold text-[#8A90A4] uppercase tracking-[0.1em]" htmlFor="job-desc">
            <Sparkles size={10} className="text-[#3CB697]" />
            Job Description
            <span className="text-[#8A90A4]/50 normal-case font-normal tracking-normal">
              (optional — enables job match scoring)
            </span>
          </label>
          <textarea
            id="job-desc"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the job description here to get a match score…"
            rows={4}
            className="w-full px-4 py-3 rounded-xl text-sm bg-[#0B0D12] border border-[rgba(60,182,151,0.12)] text-[#E8E6DF] placeholder:text-[#8A90A4]/60 outline-none resize-none transition-all focus:border-[#3CB697]/50 focus:ring-2 focus:ring-[#3CB697]/12"
          />
        </div>

        {/* Scan button */}
        <motion.button
          onClick={handleScan}
          disabled={!file || loading}
          whileHover={{ scale: (!file || loading) ? 1 : 1.005 }}
          whileTap={{ scale: (!file || loading) ? 1 : 0.98 }}
          className="w-full flex items-center justify-center gap-2.5 py-3.5 rounded-xl text-sm font-bold bg-[#3CB697] text-[#0B0D12] hover:bg-[#3CB697]/92 hover:shadow-[0_0_28px_rgba(60,182,151,0.32)] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
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
      </motion.div>

      {/* Loading skeleton */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="glass-card rounded-2xl p-6 space-y-5"
          >
            <div className="flex items-center gap-3">
              <div className="relative w-8 h-8">
                <div className="absolute inset-0 rounded-full border-2 border-[#3CB697]/20" />
                <div className="absolute inset-0 rounded-full border-2 border-[#3CB697] border-t-transparent animate-spin" />
              </div>
              <div>
                <p className="text-sm font-semibold text-[#E8E6DF]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
                  Running forensic analysis
                </p>
                <p className="text-xs text-[#8A90A4] mt-0.5">Extracting text, scanning for fraud signals…</p>
              </div>
            </div>
            {/* Animated progress bars */}
            <div className="space-y-3">
              {['Extracting text layers', 'Detecting fraud signals', 'Scoring trust and AI content'].map((step, i) => (
                <div key={step} className="space-y-1.5">
                  <p className="text-xs text-[#8A90A4] font-mono">{step}</p>
                  <div className="h-1.5 bg-[#1E2230] rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-[#3CB697]/60 rounded-full"
                      initial={{ width: '0%' }}
                      animate={{ width: ['0%', '80%', '95%'] }}
                      transition={{
                        duration: 3 + i * 0.8,
                        ease: 'easeOut',
                        repeat: Infinity,
                        repeatType: 'reverse',
                        delay: i * 0.4,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results */}
      <AnimatePresence>
        {result && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
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
          transition={{ delay: 0.2 }}
          className="flex flex-col items-center gap-4 py-10 text-center"
        >
          <div className="w-14 h-14 rounded-2xl bg-[#131620] border border-[rgba(60,182,151,0.10)] flex items-center justify-center">
            <FileText size={22} className="text-[#8A90A4]" />
          </div>
          <div>
            <p className="text-sm font-medium text-[#8A90A4]">Upload a resume PDF to get started</p>
            <p className="text-xs text-[#8A90A4]/60 mt-1">Forensic analysis takes 5–15 seconds</p>
          </div>
        </motion.div>
      )}
    </div>
  );
}
